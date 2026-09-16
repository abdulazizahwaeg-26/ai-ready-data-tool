"""معالجة الوسائط والطباعة لواجهتي التنظيف والإثراء."""

import argparse

from src.fileManager.io import load_config, read_csv_rows, read_table, write_csv_rows
from src.roles.logic import clean_data, enrich_data, REGION_CODES


def _print_region_counts(rows, header):
    region_index = header.index("region") if "region" in header else -1
    for region in REGION_CODES:
        count = sum(
            1
            for row in rows
            if region_index >= 0
            and region_index < len(row)
            and row[region_index].strip().lower() == region
        )
        print(f"  {region}: {count}")


def run_clean(input_path, output_path, strategy="mean", dedupe=True):
    header, rows = read_table(input_path)
    header, rows, stats = clean_data(header, rows, strategy, dedupe)
    write_csv_rows(header, rows, output_path)
    return stats


def run_enrich(input_path, output_path, charge_tax=True, drop_outliers=False, verbose=0):
    table = read_csv_rows(input_path)
    if not table:
        return None
    header, rows = table[0], table[1:]
    output_header, enriched_rows, summary = enrich_data(
        header, rows, charge_tax, drop_outliers
    )
    if verbose:
        _print_region_counts(rows, header)
    write_csv_rows(output_header, enriched_rows, output_path)
    return summary


def clean_main():
    config = load_config()
    parser = argparse.ArgumentParser(description="AI-Ready Data Processing Tool")
    parser.add_argument("--input", default=config.get("input", "data/raw/sales_sample.csv"))
    parser.add_argument("--output", default=config.get("output", "output/clean.csv"))
    parser.add_argument(
        "--strategy",
        default=config.get("missing_strategy", "mean"),
        choices=["mean", "median", "drop"],
    )
    args = parser.parse_args()
    stats = run_clean(
        args.input,
        args.output,
        args.strategy,
        bool(config.get("drop_duplicates", True)),
    )
    print(f"[ok] {args.input} -> {args.output}")
    print(f"     strategy={args.strategy}  rows_in={stats['rows_in']}  rows_out={stats['rows_out']}")


def enrich_main():
    parser = argparse.ArgumentParser(description="enrich")
    parser.add_argument("--input", default="output/clean.csv")
    parser.add_argument("--output", default="output/enriched.csv")
    parser.add_argument("--no-tax", action="store_true")
    parser.add_argument("--drop-outliers", action="store_true")
    parser.add_argument("-v", action="count", default=0)
    args = parser.parse_args()
    result = run_enrich(args.input, args.output, not args.no_tax, args.drop_outliers, args.v)
    if result is None:
        print("[fail] no input")
        return
    print(f"[ok] {args.input} -> {args.output}")
    print(f"     rows={result['n']}  threshold={result['th']}")
