"""
enrich.py — بعد إعادة الهيكلة (النسخة المرجعية للمدرّب).

تضيف أعمدة مشتقّة إلى ملف CSV نظيف تمهيداً للنمذجة.
السلوك مطابق للنسخة القديمة حرفاً بحرف — الاختبارات هي الدليل، لا الانطباع.

    python enrich.py --input output/clean.csv --output output/enriched.csv
"""

import argparse
import csv
import os
import statistics
import sys
from collections import Counter

# ── الأرقام التي كانت سحرية، ولها الآن أسماء تُناقَش ───────────────
TAX_RATE = 0.15                 # ضريبة القيمة المضافة على المبلغ الصافي
HIGH_VALUE_THRESHOLD = 1000.0   # حدّ الطلب «عالي القيمة» بعملة الملف
OUTLIER_SIGMA = 2               # كم انحرافاً معيارياً فوق المتوسط يُعدّ شذوذاً
PERCENT = 100.0

REGION_CODES = {"sanaa": 1, "aden": 2, "taiz": 3, "hodeidah": 4}
UNKNOWN_REGION_CODE = 0

UNITS_COLUMN = "units_sold"
PRICE_COLUMN = "unit_price"
DISCOUNT_COLUMN = "discount"
REGION_COLUMN = "region"

DERIVED_COLUMNS = ["gross", "discount_amount", "tax", "total",
                   "region_code", "is_outlier", "is_high_value"]

MONEY = "%.2f"


# ── قراءة الملف ───────────────────────────────────────────────────
def read_table(path):
    """يعيد (العناوين، الصفوف). ملف مفقود يعطي جدولاً فارغاً لا استثناءً."""
    if not os.path.exists(path):
        print(f"warning: not found: {path}", file=sys.stderr)
        return [], []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = [row for row in csv.reader(handle) if any(c.strip() for c in row)]
    if not rows:
        return [], []
    return rows[0], rows[1:]


def column_index(header, name):
    """
    موضع العمود، أو -1 إن لم يوجد.

    سلوك موروث مقصود: عند تكرار الاسم يُؤخذ آخر عمود مطابق.
    إعادة الهيكلة لا تصحّح السلوك الغريب — تصحيحه تعديلٌ منفصل بـ commit منفصل.
    """
    found = -1
    for index, column in enumerate(header):
        if column == name:
            found = index
    return found


def cell_as_number(row, index, default=0.0):
    """يقرأ خلية كرقم. الخلية الفارغة أو غير الرقمية أو الغائبة تعطي القيمة الافتراضية."""
    try:
        return float(row[index])
    except (ValueError, IndexError, TypeError):
        return default


# ── الحسابات: كل دالة تجيب عن سؤال واحد ────────────────────────────
def gross_amount(units, unit_price):
    return units * unit_price


def discount_amount(gross, discount_percent):
    return gross * discount_percent / PERCENT


def tax_amount(net, charge_tax):
    return net * TAX_RATE if charge_tax else 0.0


def region_code(region_name):
    return REGION_CODES.get(region_name.strip().lower(), UNKNOWN_REGION_CODE)


def outlier_threshold(values):
    """
    الحدّ الأعلى المقبول: المتوسط + (OUTLIER_SIGMA × الانحراف المعياري).

    يُحسب على كل الصفوف قبل أي حذف — وإلا تغيّر الحدّ بتغيّر ما حُذف.
    """
    if len(values) < 2:
        return 0.0, 0.0
    return statistics.mean(values), statistics.pstdev(values)


def is_outlier(value, mean, deviation):
    return deviation > 0 and value > mean + OUTLIER_SIGMA * deviation


# ── بناء الصف المُثرى ──────────────────────────────────────────────
def derived_values(row, columns, charge_tax, outlier):
    units = cell_as_number(row, columns["units"])
    price = cell_as_number(row, columns["price"])
    discount_percent = cell_as_number(row, columns["discount"])
    region = row[columns["region"]] if columns["region"] >= 0 else ""

    gross = gross_amount(units, price)
    discount = discount_amount(gross, discount_percent)
    net = gross - discount
    tax = tax_amount(net, charge_tax)
    total = net + tax

    return [
        MONEY % gross,
        MONEY % discount,
        MONEY % tax,
        MONEY % total,
        str(region_code(region)),
        str(int(outlier)),
        str(int(total > HIGH_VALUE_THRESHOLD)),
    ]


def locate_columns(header):
    return {
        "units": column_index(header, UNITS_COLUMN),
        "price": column_index(header, PRICE_COLUMN),
        "discount": column_index(header, DISCOUNT_COLUMN),
        "region": column_index(header, REGION_COLUMN),
    }


def write_table(header, rows, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def region_report(header, rows):
    index = column_index(header, REGION_COLUMN)
    if index < 0:
        return Counter()
    return Counter(row[index].strip().lower() for row in rows if index < len(row))


# ── الواجهة الرئيسة ───────────────────────────────────────────────
def enrich(input_path, output_path, charge_tax=True, drop_outliers=False):
    """يُثري الملف ويعيد ملخّصاً. المعاملان المنطقيان بالاسم لا بالموضع."""
    header, rows = read_table(input_path)
    if not header:
        return None

    columns = locate_columns(header)
    unit_values = [cell_as_number(row, columns["units"]) for row in rows]
    mean, deviation = outlier_threshold(unit_values)

    enriched = [
        row + derived_values(row, columns, charge_tax,
                             is_outlier(units, mean, deviation))
        for row, units in zip(rows, unit_values)
    ]

    if drop_outliers:
        enriched = [row for row in enriched if row[-2] == "0"]

    write_table(header + DERIVED_COLUMNS, enriched, output_path)
    return {"n": len(enriched), "th": HIGH_VALUE_THRESHOLD,
            "mu": mean, "sd": deviation}


def main():
    parser = argparse.ArgumentParser(description="AI-Ready Data Processing Tool — enrich")
    parser.add_argument("--input", default="output/clean.csv")
    parser.add_argument("--output", default="output/enriched.csv")
    parser.add_argument("--no-tax", action="store_true")
    parser.add_argument("--drop-outliers", action="store_true")
    parser.add_argument("-v", action="count", default=0)
    args = parser.parse_args()

    if args.v:
        header, rows = read_table(args.input)
        for region, count in sorted(region_report(header, rows).items()):
            print(f"  {region}: {count}")

    summary = enrich(args.input, args.output,
                     charge_tax=not args.no_tax,
                     drop_outliers=args.drop_outliers)
    if summary is None:
        print("[fail] no input")
        return
    print(f"[ok] {args.input} -> {args.output}")
    print(f"     rows={summary['n']}  threshold={summary['th']:g}")


if __name__ == "__main__":
    main()
