"""نقطة التشغيل الموحدة لخط تجهيز البيانات."""

import argparse

from src.fileManager.io import load_config
from src.media.cli import run_clean, run_enrich


def main():
    """ينظف الملف الخام ثم يكتب الملف المُثرى إلى المسار المطلوب."""
    config = load_config()
    parser = argparse.ArgumentParser(description="AI-Ready Data Processing Tool")
    parser.add_argument("--input", default=config.get("input", "data/raw/sales_sample.csv"))
    parser.add_argument("--output", default="output/enriched.csv")
    parser.add_argument(
        "--strategy",
        default=config.get("missing_strategy", "mean"),
        choices=["mean", "median", "drop"],
    )
    parser.add_argument("--no-tax", action="store_true")
    parser.add_argument("--drop-outliers", action="store_true")
    args = parser.parse_args()

    clean_output = config.get("output", "output/clean.csv")
    run_clean(
        args.input,
        clean_output,
        args.strategy,
        bool(config.get("drop_duplicates", True)),
    )
    run_enrich(clean_output, args.output, not args.no_tax, args.drop_outliers)


if __name__ == "__main__":
    main()
