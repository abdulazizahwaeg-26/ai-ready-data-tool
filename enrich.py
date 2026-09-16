"""إضافة أعمدة مشتقة إلى ملف CSV نظيف تمهيداً للنمذجة."""

import argparse
import csv
import os
import statistics
import sys
from dataclasses import dataclass

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


@dataclass(frozen=True)
class ColumnIndexes:
    units: int
    price: int
    discount: int
    region: int


def table_read(path):
    """يقرأ الصفوف غير الفارغة من ملف CSV، أو يعيد قائمة فارغة إذا لم يوجد."""
    if not os.path.exists(path):
        print(f"warning: not found: {path}", file=sys.stderr)
        return []
    with open(path, newline="", encoding="utf-8-sig") as file:
        return [row for row in csv.reader(file) if any(cell.strip() for cell in row)]


def _column_index(header, name):
    return header.index(name) if name in header else -1


def _number(row, index):
    """يحوّل خلية إلى رقم، مع الحفاظ على قيمة الصفر عند الخلايا غير الصالحة."""
    try:
        return float(row[index])
    except (IndexError, ValueError):
        return 0.0


def _column_values(rows, index):
    return [_number(row, index) for row in rows]


def _region_code(row, region_index):
    if region_index < 0 or region_index >= len(row):
        return 0
    return REGION_CODES.get(row[region_index].strip().lower(), 0)


def _outlier_flags(units):
    if len(units) > 1:
        mean = statistics.mean(units)
        standard_deviation = statistics.pstdev(units)
    else:
        mean = 0.0
        standard_deviation = 0.0

    flags = [
        int(standard_deviation > 0 and units_sold > mean + 2 * standard_deviation)
        for units_sold in units
    ]
    return flags, mean, standard_deviation


def _print_region_counts(rows, region_index):
    for region, code in REGION_CODES.items():
        count = sum(
            1
            for row in rows
            if region_index >= 0
            and region_index < len(row)
            and row[region_index].strip().lower() == region
        )
        print(f"  {region}: {count}")


def _financial_values(rows, columns, charge_tax):
    units = _column_values(rows, columns.units)
    prices = _column_values(rows, columns.price)
    discounts = _column_values(rows, columns.discount)
    gross_values = [units_sold * price for units_sold, price in zip(units, prices)]
    discount_values = [
        gross * discount / 100 for gross, discount in zip(gross_values, discounts)
    ]
    tax_values = [
        (gross - discount) * TAX_RATE if charge_tax else 0.0
        for gross, discount in zip(gross_values, discount_values)
    ]
    totals = [
        gross - discount + tax
        for gross, discount, tax in zip(gross_values, discount_values, tax_values)
    ]
    outlier_flags, mean, standard_deviation = _outlier_flags(units)
    return gross_values, discount_values, tax_values, totals, outlier_flags, mean, standard_deviation


def _derived_rows(rows, columns, charge_tax):
    financials = _financial_values(rows, columns, charge_tax)
    gross_values, discount_values, tax_values, totals, outlier_flags, mean, standard_deviation = (
        financials
    )
    region_codes = [_region_code(row, columns.region) for row in rows]

    derived = []
    for index, row in enumerate(rows):
        derived.append(
            row
            + [
                f"{gross_values[index]:.2f}",
                f"{discount_values[index]:.2f}",
                f"{tax_values[index]:.2f}",
                f"{totals[index]:.2f}",
                str(region_codes[index]),
                str(outlier_flags[index]),
                str(int(totals[index] > HIGH_VALUE_THRESHOLD)),
            ]
        )
    return derived, mean, standard_deviation


def _write_table(header, rows, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header + NEW_COLUMNS)
        writer.writerows(rows)


def p(input_path, output_path, charge_tax=True, drop_outliers=False, verbose=0):
    """يثري ملفاً نظيفاً ويحافظ على عقد الإخراج القديم."""
    table = table_read(input_path)
    if not table:
        return None

    header, rows = table[0], table[1:]
    columns = ColumnIndexes(
        units=_column_index(header, "units_sold"),
        price=_column_index(header, "unit_price"),
        discount=_column_index(header, "discount"),
        region=_column_index(header, "region"),
    )
    data, mean, standard_deviation = _derived_rows(rows, columns, charge_tax)
    if drop_outliers:
        data = [row for row in data if row[-2] == "0"]
    if verbose:
        _print_region_counts(rows, columns.region)
    _write_table(header, data, output_path)
    return {"n": len(data), "th": HIGH_VALUE_THRESHOLD, "mu": mean, "sd": standard_deviation}


def main():
    parser = argparse.ArgumentParser(description="enrich")
    parser.add_argument("--input", default="output/clean.csv")
    parser.add_argument("--output", default="output/enriched.csv")
    parser.add_argument("--no-tax", action="store_true")
    parser.add_argument("--drop-outliers", action="store_true")
    parser.add_argument("-v", action="count", default=0)
    args = parser.parse_args()
    result = p(args.input, args.output, not args.no_tax, args.drop_outliers, args.v)
    if result is None:
        print("[fail] no input")
        return
    print(f"[ok] {args.input} -> {args.output}")
    print(f"     rows={result['n']}  threshold={result['th']}")


if __name__ == "__main__":
    main()
