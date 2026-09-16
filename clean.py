"""واجهة توافق قديمة لمنطق التنظيف وواجهة سطر الأوامر."""

from src.fileManager.io import load_config, read_table as read_rows, write_csv_rows as write_rows
from src.media.cli import clean_main, run_clean
from src.roles.logic import clean_data, drop_duplicates, fill_missing, normalize_columns


def clean(input_path, output_path, strategy="mean", dedupe=True):
    return run_clean(input_path, output_path, strategy, dedupe)


main = clean_main

__all__ = [
    "clean",
    "drop_duplicates",
    "fill_missing",
    "load_config",
    "main",
    "normalize_columns",
    "read_rows",
    "write_rows",
    "clean_data",
]


if __name__ == "__main__":
    main()
