from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> int:
    patterns = [
        re.compile(r"from\(\s*\$db->quoteName\(\s*['\"]#__([a-z_]+)['\"]\s*\)\s*\.\s*['\"]\s*AS\s+a['\"]\s*\)", re.IGNORECASE),
        re.compile(r"from\(\s*['\"]#__([a-z_]+)\s+AS\s+a['\"]\s*\)", re.IGNORECASE),
        re.compile(r"from\(\s*['\"]#__([a-z_]+)['\"]\s*\)\s*;", re.IGNORECASE),
    ]

    for path in ROOT.rglob("*.php"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "a.client_id" not in text:
            continue

        tables: set[str] = set()
        for pattern in patterns:
            for match in pattern.finditer(text):
                table = match.group(1)
                if table:
                    tables.add(table)

        rel = path.relative_to(ROOT).as_posix()
        if tables:
            print(f"{rel}: {', '.join(sorted(tables))}")
        else:
            print(f"{rel}: <table-not-detected>")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
