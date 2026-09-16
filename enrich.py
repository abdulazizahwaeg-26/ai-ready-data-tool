"""واجهة توافق قديمة لمنطق الإثراء وواجهة سطر الأوامر."""

from src.fileManager.io import read_csv_rows as getData
from src.media.cli import enrich_main, run_enrich
from src.roles.logic import enrich_data


def p(input_path, output_path, charge_tax=True, drop_outliers=False, mode="normal", verbose=0):
    if mode == "future":
        raise NotImplementedError("سيُدعم لاحقاً")
    return run_enrich(input_path, output_path, charge_tax, drop_outliers, verbose)


main = enrich_main

__all__ = ["enrich_data", "getData", "main", "p"]


if __name__ == "__main__":
    main()
