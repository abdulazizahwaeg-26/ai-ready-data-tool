"""قراءة ملفات CSV وكتابتها وقراءة الإعدادات."""

import csv
import os
import sys


def load_config(path="config.yaml"):
    """يقرأ إعدادات key: value البسيطة من ملف."""
    config = {}
    if not os.path.exists(path):
        return config
    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            value = value.strip()
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            config[key.strip()] = value
    return config


def read_csv_rows(path, warning="warning: not found: "):
    """يقرأ صفوف CSV غير الفارغة."""
    if not os.path.exists(path):
        print(warning + path, file=sys.stderr)
        return []
    with open(path, newline="", encoding="utf-8-sig") as file:
        return [row for row in csv.reader(file) if any(cell.strip() for cell in row)]


def read_table(path):
    """يقرأ ملف CSV ويعيد العناوين والصفوف."""
    rows = read_csv_rows(path, "warning: input file not found: ")
    if not rows:
        return [], []
    return rows[0], rows[1:]


def write_csv_rows(header, rows, path):
    """يكتب عناوين وصفوف CSV إلى المسار المحدد."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if header:
            writer.writerow(header)
        writer.writerows(rows)
