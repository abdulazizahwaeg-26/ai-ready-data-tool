"""
اختبارات تثبيت السلوك (Characterization Tests) لملف enrich.py.

هذه الاختبارات لا تقول إن الكود جميل — تقول إنه يُنتج هذه الأرقام بالضبط.
وظيفتها الوحيدة: أن تصرخ إن غيّرت إعادة الهيكلة النتيجة.

    pytest tests/ -q        ← يجب أن تنجح كلها قبل أن تلمس سطراً واحداً
                              وأن تنجح كلها بعد أن تنتهي.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clean import clean
from enrich import p

RAW = "data/raw/sales_sample.csv"

# الناتج المرجعي: أعمدة (gross, discount_amount, tax, total, region_code,
# is_outlier, is_high_value) لكل طلب، كما يُنتجها النظام اليوم.
GOLDEN = {
    "1001": ("546.00", "27.30", "77.81", "596.51", "1", "0", "0"),
    "1002": ("1761.50", "0.00", "264.23", "2025.73", "2", "0", "1"),
    "1003": ("628.89", "62.89", "84.90", "650.90", "3", "0", "0"),
    "1004": ("955.50", "47.77", "136.16", "1043.88", "1", "0", "1"),
    "1005": ("546.00", "27.30", "77.81", "596.51", "1", "0", "0"),
    "1006": ("360.00", "24.00", "50.40", "386.40", "4", "0", "0"),
    "1007": ("1800.00", "270.00", "229.50", "1759.50", "2", "0", "1"),
    "1008": ("4645.72", "0.00", "696.86", "5342.57", "3", "0", "1"),
    "1009": ("9100.00", "1820.00", "1092.00", "8372.00", "1", "1", "1"),
}

NEW_COLUMNS = ["gross", "discount_amount", "tax", "total",
               "region_code", "is_outlier", "is_high_value"]


def _pipeline(tmp_path, drop_outliers=False, with_tax=True):
    """يشغّل clean ثم enrich في مجلد مؤقّت ويعيد (العناوين، الصفوف، الملخّص)."""
    cleaned = str(tmp_path / "clean.csv")
    enriched = str(tmp_path / "enriched.csv")
    clean(RAW, cleaned, "mean")
    summary = p(cleaned, enriched, with_tax, drop_outliers)
    with open(enriched, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:], summary


def test_new_columns_are_appended_in_this_exact_order(tmp_path):
    header, _, _ = _pipeline(tmp_path)
    assert header[-7:] == NEW_COLUMNS


def test_every_order_keeps_its_current_numbers(tmp_path):
    """لو غيّر أي تعديل رقماً واحداً هنا، فقد غيّر سلوك النظام لا شكله."""
    _, rows, _ = _pipeline(tmp_path)
    actual = {row[0]: tuple(row[-7:]) for row in rows}
    assert actual == GOLDEN


def test_tax_is_charged_on_the_net_amount_not_on_gross(tmp_path):
    """546.00 - 27.30 = 518.70 ، والضريبة 15% منها = 77.81 لا 81.90."""
    _, rows, _ = _pipeline(tmp_path)
    first = next(r for r in rows if r[0] == "1001")
    gross, discount, tax, total = (float(x) for x in first[-7:-3])
    assert round(gross - discount, 2) == 518.70
    assert tax == 77.81
    assert round(total, 2) == round(gross - discount + tax, 2)


def test_high_value_flag_reads_total_not_gross(tmp_path):
    """الطلب 1004: الإجمالي الخام 955.50 تحت الحد، والإجمالي النهائي 1043.88 فوقه."""
    _, rows, _ = _pipeline(tmp_path)
    row = next(r for r in rows if r[0] == "1004")
    assert float(row[-7]) < 1000      # gross
    assert float(row[-4]) > 1000      # total
    assert row[-1] == "1"             # is_high_value


def test_exactly_one_order_is_flagged_as_an_outlier(tmp_path):
    _, rows, _ = _pipeline(tmp_path)
    flagged = [r[0] for r in rows if r[-2] == "1"]
    assert flagged == ["1009"]


def test_outlier_statistics_are_computed_before_any_row_is_dropped(tmp_path):
    """
    المِصْيدة: الحدّ الإحصائي يُحسب على كل الصفوف، ثم يُحذف الشاذّ.
    لو عُكس الترتيب — حُذف الشاذّ أولاً ثم حُسب المتوسط — لتغيّر الانحراف
    المعياري، ولصار الحدّ رقماً آخر، ولربما صار صفٌّ بريء شاذّاً.
    """
    _, kept, with_drop = _pipeline(tmp_path / "a", drop_outliers=True)
    _, all_rows, no_drop = _pipeline(tmp_path / "b", drop_outliers=False)

    assert with_drop["sd"] == no_drop["sd"]
    assert with_drop["mu"] == no_drop["mu"]
    assert with_drop["n"] == no_drop["n"] - 1
    assert "1009" not in [r[0] for r in kept]
    assert len(all_rows) == 9


def test_disabling_tax_zeroes_the_column_and_the_total_equals_net(tmp_path):
    _, rows, _ = _pipeline(tmp_path, with_tax=False)
    first = next(r for r in rows if r[0] == "1001")
    assert first[-5] == "0.00"                       # tax
    assert first[-4] == "518.70"                     # total == gross - discount


def test_unknown_region_becomes_zero_not_a_crash(tmp_path):
    src = tmp_path / "in.csv"
    src.write_text("Order ID,Region,Units Sold,Unit Price,Discount %\n"
                   "1,Mukalla,5,10,0\n", encoding="utf-8")
    cleaned = str(tmp_path / "c.csv")
    out = str(tmp_path / "e.csv")
    clean(str(src), cleaned, "mean")
    p(cleaned, out, True, False)
    with open(out, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[1][-3] == "0"


def test_missing_input_returns_none_instead_of_raising(tmp_path):
    assert p(str(tmp_path / "nope.csv"), str(tmp_path / "out.csv")) is None
