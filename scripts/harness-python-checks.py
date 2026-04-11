#!/usr/bin/env python3
"""
Lightweight Python harness: enforce cyclomatic complexity, function/class length, and naming styles.

Constraints (config below):
- Cyclomatic complexity <= 7
- Function/method length <= 100 lines
- Class length <= 800 lines
- Python function/method names must be snake_case (lowercase with underscores)
- Python class/type names must be CamelCaps (UpperCamelCase)

This script is intentionally self-contained and uses the AST for accurate line spans.
"""

import ast
import os
import re
import subprocess
import sys

CC_THRESHOLD = 7
FUNC_MAX_LINES = 100
CLASS_MAX_LINES = 800
# Python functions: require snake_case (allow a single leading underscore for private functions)
NAME_RE = re.compile(r"^_?[a-z][a-z0-9_]*$")
# Enforce CamelCaps (UpperCamelCase) for class/type names
CLASS_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")


def git_py_files():
    try:
        out = subprocess.check_output(["git", "ls-files"]).decode().splitlines()
        files = [p for p in out if p.endswith(".py")]
        if files:
            return files
        # fallthrough to filesystem walk if git lists nothing
    except Exception:
        pass
    # if git returned no matches, fallback to filesystem walk
    exclude_dirs = {
        ".gradle",
        "build",
        "hf_env",
        ".venv",
        "androidApp/build",
        "node_modules",
        "venv",
        "__pycache__",
        ".git",
    }
    files = []
    for root, dirs, filenames in os.walk("."):
        # prune excluded dirs in-place to avoid walking into them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        # skip if this root is under an excluded path
        if any(part in exclude_dirs for part in root.split(os.sep)):
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                path = os.path.join(root, fn)
                files.append(path)
    return files


def cc_for_node(node):
    cc = 1
    for n in ast.walk(node):
        t = type(n).__name__
        if t in ("If", "For", "While", "AsyncFor"):
            cc += 1
        elif t == "BoolOp":
            # each boolean operator increases complexity by number of ops
            try:
                cc += max(0, len(n.values) - 1)
            except Exception:
                pass
        elif t == "Try":
            try:
                cc += len(n.handlers)
            except Exception:
                pass
        elif t == "IfExp":
            cc += 1
        elif t == "Match":
            try:
                cc += len(n.cases)
            except Exception:
                pass
        elif t == "comprehension":
            cc += 1
    return cc


def analyze_file(path, violations):
    try:
        source = open(path, "r", encoding="utf-8").read()
    except Exception as e:
        violations.append(("read_error", path, str(e)))
        return

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        violations.append(("parse_error", path, str(e)))
        return

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            lineno = getattr(node, "lineno", 0)
            end = getattr(node, "end_lineno", lineno)
            length = end - lineno + 1
            cc = cc_for_node(node)
            if cc > CC_THRESHOLD:
                violations.append(("complexity", path, f"{name}:{lineno}", cc))
            if length > FUNC_MAX_LINES:
                violations.append(("func_length", path, f"{name}:{lineno}", length))
            if not NAME_RE.match(name):
                violations.append(("naming", path, f"{name}:{lineno}", name))

        elif isinstance(node, ast.ClassDef):
            lineno = getattr(node, "lineno", 0)
            end = getattr(node, "end_lineno", lineno)
            length = end - lineno + 1
            if length > CLASS_MAX_LINES:
                violations.append(
                    ("class_length", path, f"{node.name}:{lineno}", length)
                )
            # Enforce CamelCaps for class/type names
            if not CLASS_NAME_RE.match(node.name):
                violations.append(
                    ("naming_class", path, f"{node.name}:{lineno}", node.name)
                )


def main(argv):
    if len(argv) > 1:
        files = [p for p in argv[1:] if p.endswith(".py") and os.path.isfile(p)]
    else:
        files = git_py_files()

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
                    f"{path}:{loc}: function name '{val}' does not follow snake_case (lowercase with underscores)"
                )
            elif kind == "naming_class":
                _, path, loc, val = v
                print(
                    f"{path}:{loc}: class/type name '{val}' does not follow CamelCaps (UpperCamelCase)"
                )
            elif kind == "read_error":
                _, path, msg = v
                print(f"{path}: read error: {msg}")
            elif kind == "parse_error":
                _, path, msg = v
                print(f"{path}: parse error: {msg}")
        sys.exit(1)

    print("python harness checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
