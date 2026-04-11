#!/usr/bin/env python3
"""
Fix Python function/async function names that don't follow snake_case by renaming
definitions and updating references across the repository's Python files.

This is a best-effort tool. It preserves leading/trailing underscores and handles
async functions. It performs whole-word replacements across .py files, which is
usually safe for function identifiers but may require manual review for edge cases.
"""

import ast
import os
import re
import subprocess
import sys

SNAKE_RE = re.compile(r"^_?[a-z][a-z0-9_]*$")


def git_py_files():
    try:
        out = subprocess.check_output(["git", "ls-files"]).decode().splitlines()
        files = [p for p in out if p.endswith(".py")]
        if files:
            return files
    except Exception:
        pass
    files = []
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
    for root, dirs, filenames in os.walk("."):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        if any(part in exclude_dirs for part in root.split(os.sep)):
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                files.append(os.path.join(root, fn))
    return files


def camel_to_snake(name: str) -> str:
    m = re.match(r"^(_*)(.*?)(_*)$", name)
    if not m:
        core = name
        leading = trailing = ""
    else:
        leading, core, trailing = m.group(1), m.group(2), m.group(3)
    if core == "":
        return name
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", core)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    converted = s2.replace("-", "_")
    converted = converted.lower()
    return f"{leading}{converted}{trailing}"


def find_invalid_functions(path: str):
    try:
        src = open(path, "r", encoding="utf-8").read()
    except Exception:
        return []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    invalids = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if not SNAKE_RE.match(name):
                invalids.append((name, node.lineno))
    return invalids


def replace_in_file_defs(path: str, old: str, new: str) -> bool:
    try:
        s = open(path, "r", encoding="utf-8").read()
    except Exception:
        return False
    # replace def/async def declarations (only for the specific name)
    pattern = re.compile(
        r"(^\s*(?:async\s+)?def\s+)" + re.escape(old) + r"(\s*\()", re.M
    )
    new_s, n_defs = pattern.subn(r"\1" + new + r"\2", s)
    if n_defs > 0:
        open(path, "w", encoding="utf-8").write(new_s)
        return True
    return False


def replace_references(repo_files, old: str, new: str):
    word = re.compile(r"\b" + re.escape(old) + r"\b")
    changed = []
    for p in repo_files:
        try:
            s = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue
        new_s, n = word.subn(new, s)
        if n > 0:
            open(p, "w", encoding="utf-8").write(new_s)
            changed.append(p)
    return changed


def main():
    files = git_py_files()
    repo_files = files[:]  # for cross-file replacements
    total_changes = []
    for f in files:
        invalids = find_invalid_functions(f)
        if not invalids:
            continue
        for oldname, lineno in invalids:
            newname = camel_to_snake(oldname)
            if newname == oldname:
                continue
            # update definition in this file
            ok = replace_in_file_defs(f, oldname, newname)
            if ok:
                total_changes.append((f, oldname, newname))
                # update references across repo
                changed = replace_references(repo_files, oldname, newname)
                print(
                    f"Renamed {oldname} -> {newname} (defs updated in {f}; {len(changed)} files updated)"
                )
            else:
                print(f"Warning: could not find def for {oldname} in {f}; skipped")

    if not total_changes:
        print("No Python naming fixes required.")
        return 0
    print("Applied naming fixes:")
    for f, old, new in total_changes:
        print(f" - {f}: {old} -> {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
