"""
metrics.py — مقياس نظافة بالمكتبة القياسية وحدها. لا يحتاج أي تثبيت.

شبكة أمان لمختبرات اليوم إن تعذّر تثبيت ruff أو radon في القاعة.
يقيس ما يمكن قياسه فعلاً، ويسكت عمّا هو ذوق.

    python metrics.py enrich.py
    python metrics.py enrich.py solutions/enrich_clean.py     # مقارنة
"""

import ast
import sys

MAX_FUNCTION_LINES = 30
MAX_PARAMETERS = 4
MAX_NESTING = 3
BAD_NAME_LENGTH = 2

NESTING_NODES = (ast.If, ast.For, ast.While, ast.With, ast.Try)


def nesting_depth(node, depth=0):
    """أعمق تداخل داخل جسم الدالة."""
    deepest = depth
    for child in ast.iter_child_nodes(node):
        child_depth = depth + 1 if isinstance(child, NESTING_NODES) else depth
        deepest = max(deepest, nesting_depth(child, child_depth))
    return deepest


def local_names(node):
    """أسماء المتغيّرات المحلّية المُسنَدة داخل الدالة."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            names.add(child.id)
    return names


def short_names(names):
    return sorted(n for n in names if len(n) <= BAD_NAME_LENGTH and n != "_")


def inspect(path):
    source = open(path, encoding="utf-8").read()
    tree = ast.parse(source)
    report = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        length = (node.end_lineno or node.lineno) - node.lineno + 1
        args = node.args
        params = len(args.posonlyargs) + len(args.args) + len(args.kwonlyargs)
        depth = nesting_depth(node)
        names = short_names(local_names(node) | {a.arg for a in args.args})
        report.append({
            "name": node.name, "line": node.lineno, "lines": length,
            "params": params, "depth": depth, "short": names,
        })
    return sorted(report, key=lambda r: -r["lines"]), source.count("\n") + 1


def show(path):
    functions, total_lines = inspect(path)
    problems = 0
    print(f"\n── {path}  ({total_lines} سطراً)")
    print(f"{'الدالة':<22}{'الأسطر':>7}{'المعاملات':>11}{'التداخل':>9}   أسماء قصيرة")
    print("─" * 72)
    for f in functions:
        marks = ""
        if f["lines"] > MAX_FUNCTION_LINES:
            marks += "!"
            problems += 1
        if f["params"] > MAX_PARAMETERS:
            marks += "!"
            problems += 1
        if f["depth"] > MAX_NESTING:
            marks += "!"
            problems += 1
        if f["short"]:
            problems += len(f["short"])
        names = ", ".join(f["short"][:8]) or "—"
        print(f"{f['name']:<22}{f['lines']:>7}{f['params']:>11}{f['depth']:>9}   {names} {marks}")
    print("─" * 72)
    print(f"مجموع الملاحظات: {problems}"
          f"    (الحدود: {MAX_FUNCTION_LINES} سطراً · {MAX_PARAMETERS} معاملات ·"
          f" تداخل {MAX_NESTING} · اسم أطول من {BAD_NAME_LENGTH} حرفين)")
    return problems


def main():
    paths = sys.argv[1:] or ["enrich.py"]
    scores = [(p, show(p)) for p in paths]
    if len(scores) > 1:
        print("\n═══ المقارنة ═══")
        for path, score in scores:
            print(f"  {score:>4} ملاحظة   {path}")


if __name__ == "__main__":
    main()
