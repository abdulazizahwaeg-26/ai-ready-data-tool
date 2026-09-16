"""اختبارات الوحدة للدوال العامة في src.roles.logic."""

import pytest

from src.roles.logic import (
    clean_data,
    drop_duplicates,
    enrich_data,
    fill_missing,
    normalize_columns,
)


def test_normalize_columns_normalizes_names_and_missing_text():
    """يثبت توحيد الأسماء والتعامل مع اسم عمود فارغ."""
    assert normalize_columns([" Order ID ", "Discount %", ""]) == [
        "order_id",
        "discount",
        "",
    ]


def test_normalize_columns_empty_header_returns_empty_header():
    """يثبت أن العنوان الفارغ يبقى فارغاً."""
    assert normalize_columns([]) == []


def test_normalize_columns_rejects_missing_header():
    """يثبت رفض العنوان المفقود بنوع خطأ واضح."""
    with pytest.raises(TypeError):
        normalize_columns(None)


def test_fill_missing_replaces_missing_numeric_values_with_mean():
    """يثبت استكمال القيمة الرقمية المفقودة بالمتوسط."""
    assert fill_missing(["units"], [["10"], [""], ["20"]]) == [["10"], ["15"], ["20"]]


def test_fill_missing_empty_rows_returns_empty_rows():
    """يثبت أن غياب الصفوف لا ينتج صفوفاً جديدة."""
    assert fill_missing(["units"], []) == []


def test_fill_missing_rejects_missing_rows():
    """يثبت رفض مجموعة الصفوف المفقودة بنوع خطأ واضح."""
    with pytest.raises(TypeError):
        fill_missing(["units"], None)


def test_drop_duplicates_keeps_first_duplicate_and_unique_rows():
    """يثبت حذف التكرار مع الحفاظ على أول ظهور."""
    assert drop_duplicates([["a"], ["a"], ["b"]]) == [["a"], ["b"]]


def test_drop_duplicates_empty_rows_returns_empty_rows():
    """يثبت أن قائمة الصفوف الفارغة تبقى فارغة."""
    assert drop_duplicates([]) == []


def test_drop_duplicates_rejects_missing_rows():
    """يثبت رفض الصفوف المفقودة بنوع خطأ واضح."""
    with pytest.raises(TypeError):
        drop_duplicates(None)


def test_clean_data_normalizes_fills_and_deduplicates():
    """يثبت تنفيذ التنظيف الكامل مع استكمال قيمة مفقودة."""
    header, rows, stats = clean_data(
        ["Order ID", "Units"],
        [["1", "10"], ["2", ""], ["2", "15"]],
    )
    assert header == ["order_id", "units"]
    assert rows == [["1", "10"], ["2", "12.5"], ["2", "15"]]
    assert stats == {"rows_in": 3, "rows_out": 3}


def test_clean_data_empty_header_returns_empty_result():
    """يثبت أن الجدول بلا عنوان يعيد نتيجة فارغة وملخصاً صفرياً."""
    assert clean_data([], []) == ([], [], {"rows_in": 0, "rows_out": 0})


def test_clean_data_rejects_missing_rows():
    """يثبت رفض الصفوف المفقودة بنوع خطأ واضح."""
    with pytest.raises(TypeError):
        clean_data(["units"], None)


def test_enrich_data_calculates_derived_columns():
    """يثبت حساب الإجمالي والخصم والضريبة والعلامات المشتقة."""
    header, rows, summary = enrich_data(
        ["region", "units_sold", "unit_price", "discount"],
        [["Sanaa", "2", "100", "10"]],
    )
    assert header[-7:] == [
        "gross",
        "discount_amount",
        "tax",
        "total",
        "region_code",
        "is_outlier",
        "is_high_value",
    ]
    assert rows[0][-7:] == ["200.00", "20.00", "27.00", "207.00", "1", "0", "0"]
    assert summary == {"n": 1, "th": 1000, "mu": 0.0, "sd": 0.0}


def test_enrich_data_empty_rows_returns_header_and_zero_summary():
    """يثبت أن إثراء جدول فارغ لا يضيف صفوفاً."""
    header, rows, summary = enrich_data(
        ["region", "units_sold", "unit_price", "discount"],
        [],
    )
    assert header[-7:] == [
        "gross",
        "discount_amount",
        "tax",
        "total",
        "region_code",
        "is_outlier",
        "is_high_value",
    ]
    assert rows == []
    assert summary == {"n": 0, "th": 1000, "mu": 0.0, "sd": 0.0}


def test_enrich_data_missing_numeric_value_defaults_to_zero():
    """يثبت أن القيمة الرقمية المفقودة تعامل كصفر دون إسقاط الصف."""
    _, rows, _ = enrich_data(
        ["region", "units_sold", "unit_price", "discount"],
        [["Unknown", "", "100", "0"]],
    )
    assert rows[0][-7:] == ["0.00", "0.00", "0.00", "0.00", "0", "0", "0"]


def test_enrich_data_rejects_missing_header():
    """يثبت رفض العنوان المفقود بنوع خطأ واضح."""
    with pytest.raises(TypeError):
        enrich_data(None, [])
