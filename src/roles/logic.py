"""الحسابات وقواعد العمل دون قراءة ملفات أو طباعتها."""

import re
import statistics

TAX_RATE = 0.15
HIGH_VALUE_THRESHOLD = 1000
REGION_CODES = {"sanaa": 1, "aden": 2, "taiz": 3, "hodeidah": 4}
NEW_COLUMNS = [
    "gross",
    "discount_amount",
    "tax",
    "total",
    "region_code",
    "is_outlier",
    "is_high_value",
]


def normalize_columns(header):
    """يوحّد أسماء الأعمدة."""
    normalized = []
    for name in header:
        name = name.strip().lower()
        name = re.sub(r"[^\w\s]", "", name)
        name = re.sub(r"\s+", "_", name.strip())
        normalized.append(name.strip("_"))
    return normalized


def _numeric_column(rows, index):
    values = []
    for row in rows:
        if index >= len(row):
            continue
        cell = row[index].strip()
        if cell == "":
            continue
        try:
            values.append(float(cell))
        except ValueError:
            return None
    return values


def fill_missing(header, rows, strategy="mean"):
    """يعالج الخلايا الفارغة في الأعمدة الرقمية."""
    if strategy == "drop":
        return [row for row in rows if all(str(cell).strip() != "" for cell in row)]

    filled_rows = [list(row) for row in rows]
    for index in range(len(header)):
        values = _numeric_column(filled_rows, index)
        if not values:
            continue
        replacement = statistics.mean(values) if strategy == "mean" else statistics.median(values)
        for row in filled_rows:
            if index < len(row) and row[index].strip() == "":
                row[index] = f"{replacement:.4f}".rstrip("0").rstrip(".")
    return filled_rows


def drop_duplicates(rows):
    """يحذف الصفوف المكررة مع إبقاء أول ظهور."""
    seen, unique_rows = set(), []
    for row in rows:
        key = tuple(row)
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
    return unique_rows


def clean_data(header, rows, strategy="mean", dedupe=True):
    """ينظف جدولاً ويعيد الملخص دون أي تعامل مع الملفات."""
    if not header:
        return [], [], {"rows_in": 0, "rows_out": 0}
    rows_in = len(rows)
    normalized_header = normalize_columns(header)
    cleaned_rows = fill_missing(normalized_header, rows, strategy)
    if dedupe:
        cleaned_rows = drop_duplicates(cleaned_rows)
    return normalized_header, cleaned_rows, {
        "rows_in": rows_in,
        "rows_out": len(cleaned_rows),
    }


def _number(row, index):
    try:
        return float(row[index])
    except (IndexError, ValueError):
        return 0.0


def _column_index(header, name):
    return header.index(name) if name in header else -1


def _region_code(row, index):
    if index < 0 or index >= len(row):
        return 0
    return REGION_CODES.get(row[index].strip().lower(), 0)


def _outlier_flags(units):
    if len(units) > 1:
        mean = statistics.mean(units)
        standard_deviation = statistics.pstdev(units)
    else:
        mean = standard_deviation = 0.0
    flags = [
        int(standard_deviation > 0 and value > mean + 2 * standard_deviation)
        for value in units
    ]
    return flags, mean, standard_deviation


def enrich_data(header, rows, charge_tax=True, drop_outliers=False):
    """يضيف الأعمدة المشتقة إلى جدول دون قراءة أو كتابة."""
    units_index = _column_index(header, "units_sold")
    price_index = _column_index(header, "unit_price")
    discount_index = _column_index(header, "discount")
    region_index = _column_index(header, "region")
    units = [_number(row, units_index) for row in rows]
    prices = [_number(row, price_index) for row in rows]
    discounts = [_number(row, discount_index) for row in rows]
    gross = [units_sold * price for units_sold, price in zip(units, prices)]
    discount_amount = [
        amount * discount / 100 for amount, discount in zip(gross, discounts)
    ]
    tax = [
        (amount - discount) * TAX_RATE if charge_tax else 0.0
        for amount, discount in zip(gross, discount_amount)
    ]
    total = [
        amount - discount + tax_value
        for amount, discount, tax_value in zip(gross, discount_amount, tax)
    ]
    outlier_flags, mean, standard_deviation = _outlier_flags(units)
    enriched_rows = []
    for index, row in enumerate(rows):
        enriched_rows.append(
            row
            + [
                f"{gross[index]:.2f}",
                f"{discount_amount[index]:.2f}",
                f"{tax[index]:.2f}",
                f"{total[index]:.2f}",
                str(_region_code(row, region_index)),
                str(outlier_flags[index]),
                str(int(total[index] > HIGH_VALUE_THRESHOLD)),
            ]
        )
    if drop_outliers:
        enriched_rows = [row for row in enriched_rows if row[-2] == "0"]
    return header + NEW_COLUMNS, enriched_rows, {
        "n": len(enriched_rows),
        "th": HIGH_VALUE_THRESHOLD,
        "mu": mean,
        "sd": standard_deviation,
    }
