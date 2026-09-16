# enrich.py
# آخر تعديل: قبل أربعة عشر شهراً — كتبه زميل غادر الفريق.
# ملاحظة مكتوبة في أعلى الملف: "لا تلمس شيئاً، الملف يعمل."
#
# يقرأ ملف CSV نظيفاً (مخرَج clean.py) ويضيف أعمدة مشتقّة للنمذجة.

import argparse
import csv
import os
import statistics
import sys

NUM = 0.15        # الضريبة
NUM2 = 1000       # الحد
R = {"sanaa": 1, "aden": 2, "taiz": 3, "hodeidah": 4}


# ─────────────────────────────────────────────────────────────
class ThresholdStrategy:
    def get(self, rows):
        raise NotImplementedError


class FixedThresholdStrategy(ThresholdStrategy):
    def get(self, rows):
        return NUM2


class AdaptiveThresholdStrategy(ThresholdStrategy):
    def get(self, rows):
        return NUM2


class ThresholdStrategyFactory:
    @staticmethod
    def create(k):
        if k == "fixed":
            return FixedThresholdStrategy()
        elif k == "adaptive":
            return AdaptiveThresholdStrategy()
        else:
            return FixedThresholdStrategy()


# ─────────────────────────────────────────────────────────────
def getData(f):
    if not os.path.exists(f):
        print("warning: not found: " + f, file=sys.stderr)
        return []
    with open(f, newline="", encoding="utf-8-sig") as fh:
        return [r for r in csv.reader(fh) if any(c.strip() for c in r)]


def calc2(a, b):
    return a * b


# def export_xml(rows, path):
#     كان مطلوباً في اجتماع الربع الثاني. لم يُستخدم قط.
#     with open(path, "w") as f:
#         f.write("<rows>")


def p(f, o, t=True, d=False, m="normal", v=0):
    if m == "future":
        raise NotImplementedError("سيُدعم لاحقاً")

    l = getData(f)
    if not l:
        return None
    h = l[0]
    r = l[1:]

    # x = عمود الكمية ، y = عمود السعر ، z = عمود الخصم
    x = -1
    y = -1
    z = -1
    for i in range(len(h)):
        if h[i] == "units_sold":
            x = i
        if h[i] == "unit_price":
            y = i
        if h[i] == "discount":
            z = i

    n1 = []
    for row in r:
        try:
            a = float(row[x])
        except:
            a = 0.0
        try:
            b = float(row[y])
        except:
            b = 0.0
        n1.append(a * b)

    n2 = []
    for i in range(len(r)):
        try:
            c = float(r[i][z])
        except:
            c = 0.0
        n2.append(n1[i] * c / 100)

    n3 = []
    for i in range(len(r)):
        net = n1[i] - n2[i]
        if t:
            n3.append(net * NUM)
        else:
            n3.append(0.0)

    codes = []
    for row in r:
        got = 0
        for i in range(len(h)):
            if h[i] == "region":
                v2 = row[i].strip().lower()
                if v2 != "":
                    if v2 in R:
                        got = R[v2]
                    else:
                        got = 0
        codes.append(got)

    units = []
    for row in r:
        try:
            units.append(float(row[x]))
        except:
            units.append(0.0)
    if len(units) > 1:
        mu = statistics.mean(units)
        sd = statistics.pstdev(units)
    else:
        mu = 0.0
        sd = 0.0
    flag1 = []
    for u in units:
        if sd > 0 and u > mu + 2 * sd:
            flag1.append(1)
        else:
            flag1.append(0)

    st = ThresholdStrategyFactory.create("fixed")
    th = st.get(r)
    flag2 = []
    for i in range(len(r)):
        tot = n1[i] - n2[i] + n3[i]
        if tot > th:
            flag2.append(1)
        else:
            flag2.append(0)

    data2 = []
    for i in range(len(r)):
        tot = n1[i] - n2[i] + n3[i]
        data2.append(r[i] + [
            "%.2f" % n1[i], "%.2f" % n2[i], "%.2f" % n3[i], "%.2f" % tot,
            str(codes[i]), str(flag1[i]), str(flag2[i]),
        ])

    if d:
        tmp = []
        for row in data2:
            if row[-2] == "0":
                tmp.append(row)
        data2 = tmp

    if v > 0:
        rr = {"sanaa": 1, "aden": 2, "taiz": 3, "hodeidah": 4}
        for k in rr:
            cnt = 0
            for row in r:
                for i in range(len(h)):
                    if h[i] == "region" and row[i].strip().lower() == k:
                        cnt += 1
            print("  " + k + ": " + str(cnt))

    h2 = h + ["gross", "discount_amount", "tax", "total",
              "region_code", "is_outlier", "is_high_value"]
    os.makedirs(os.path.dirname(o) or ".", exist_ok=True)
    with open(o, "w", newline="", encoding="utf-8") as f2:
        w = csv.writer(f2)
        w.writerow(h2)
        w.writerows(data2)
    return {"n": len(data2), "th": th, "mu": mu, "sd": sd}


def main():
    ap = argparse.ArgumentParser(description="enrich")
    ap.add_argument("--input", default="output/clean.csv")
    ap.add_argument("--output", default="output/enriched.csv")
    ap.add_argument("--no-tax", action="store_true")
    ap.add_argument("--drop-outliers", action="store_true")
    ap.add_argument("-v", action="count", default=0)
    a = ap.parse_args()
    res = p(a.input, a.output, not a.no_tax, a.drop_outliers, "normal", a.v)
    if res is None:
        print("[fail] no input")
        return
    print("[ok] " + a.input + " -> " + a.output)
    print("     rows=" + str(res["n"]) + "  threshold=" + str(res["th"]))


if __name__ == "__main__":
    main()
