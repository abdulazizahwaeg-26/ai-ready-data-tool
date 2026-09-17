"""اختبار توافق مخرجات واجهة الحزمة."""

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FIXTURE = Path(__file__).parent / "fixtures" / "sales_sample.csv"
EXPECTED_OUTPUT = Path(__file__).parent / "fixtures" / "enriched_baseline.csv"


def test_cli_output_matches_baseline(tmp_path):
    """يثبت أن تشغيل CLI ينتج نفس CSV المرجعي byte-for-byte."""
    output_path = tmp_path / "now.csv"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli",
            "--input",
            str(INPUT_FIXTURE),
            "--output",
            str(output_path),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.read_bytes() == EXPECTED_OUTPUT.read_bytes()
