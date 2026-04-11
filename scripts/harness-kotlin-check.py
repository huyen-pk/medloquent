#!/usr/bin/env python3
"""
Heuristic Kotlin checks: function/class length, cyclomatic complexity, and camelCase function naming.
This is a fallback if detekt is unavailable.
"""

import os
import re
import subprocess
import sys

CC_THRESHOLD = 7
FUNC_MAX_LINES = 100
CLASS_MAX_LINES = 800
# Require CamelCaps (UpperCamelCase) for functions and types
NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
CLASS_NAME_RE = NAME_RE


def git_kt_files():
    try:
        out = (
            subprocess.check_output(["git", "ls-files", "*.kt", "*.kts"])
            .decode()
            .splitlines()
        )
        return [p for p in out if p]
    except Exception:
        files = []
        for root, _, filenames in os.walk("."):
            for fn in filenames:
                if fn.endswith(".kt") or fn.endswith(".kts"):
                    files.append(os.path.join(root, fn))
        return files


def find_brace_block(lines, start_index):
    # Find first '{' from start_index and balance braces
    n = len(lines)
    i = start_index
    # find opening brace
    while i < n and "{" not in lines[i]:
        i += 1
    if i >= n:
        return start_index, start_index
    depth = 0
    for j in range(i, n):
        depth += lines[j].count("{")
        depth -= lines[j].count("}")
        if depth <= 0:
            return i, j
    return i, n - 1


def analyze_file(path, violations):
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    text = "".join(lines)

    # functions
    for m in re.finditer(r"\bfun\b[^\S\n\r\(\{]*([A-Za-z_][A-Za-z0-9_]*)\s*\(", text):
        pre = text[: m.start()]
        lineno = pre.count("\n") + 1
        name = m.group(1)
        # convert to line index
        start_idx = lineno - 1
        bstart, bend = find_brace_block(lines, start_idx)
        length = bend - start_idx + 1
        # extract body text
        body = "".join(lines[bstart : (bend + 1)])
        cc = 1 + len(
            re.findall(
                r"\b(if|for|while|when|catch|case|else if|\band\b|\bor\b)\b|&&|\|\|",
                body,
            )
        )
        if cc > CC_THRESHOLD:
            violations.append(("complexity", path, f"{name}:{lineno}", cc))
        if length > FUNC_MAX_LINES:
            violations.append(("func_length", path, f"{name}:{lineno}", length))
        if not NAME_RE.match(name):
            violations.append(("naming", path, f"{name}:{lineno}", name))

    # classes/objects
    for m in re.finditer(
        r"\b(class|object|interface|enum)\b\s+([A-Za-z_][A-Za-z0-9_]*)", text
    ):
        pre = text[: m.start()]
        lineno = pre.count("\n") + 1
        name = m.group(2)
        start_idx = lineno - 1
        bstart, bend = find_brace_block(lines, start_idx)
        length = bend - start_idx + 1
        if length > CLASS_MAX_LINES:
            violations.append(("class_length", path, f"{name}:{lineno}", length))
        # Enforce CamelCaps for class/type names
        if not CLASS_NAME_RE.match(name):
            violations.append(("naming_class", path, f"{name}:{lineno}", name))


def main(argv):
    if len(argv) > 1:
        files = [
            p
            for p in argv[1:]
            if (p.endswith(".kt") or p.endswith(".kts")) and os.path.isfile(p)
        ]
    else:
        files = git_kt_files()

    violations = []
    for f in files:
        analyze_file(f, violations)

    if violations:
        for v in violations:
            kind = v[0]
            if kind == "complexity":
                _, path, loc, val = v
                print(f"{path}:{loc}: cyclomatic complexity {val} > {CC_THRESHOLD}")
            elif kind == "func_length":
                _, path, loc, val = v
                print(f"{path}:{loc}: function length {val} lines > {FUNC_MAX_LINES}")
            elif kind == "class_length":
                _, path, loc, val = v
                print(f"{path}:{loc}: class length {val} lines > {CLASS_MAX_LINES}")
            elif kind == "naming":
                _, path, loc, val = v
                print(
                    f"{path}:{loc}: function name '{val}' does not follow CamelCaps (UpperCamelCase)"
                )
            elif kind == "naming_class":
                _, path, loc, val = v
                print(
                    f"{path}:{loc}: class/type name '{val}' does not follow CamelCaps (UpperCamelCase)"
                )
        return 1
    print("kotlin heuristic checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
