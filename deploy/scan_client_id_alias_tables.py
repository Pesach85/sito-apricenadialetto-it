from __future__ import annotations

import glob
import re


tables = set()
pattern_from = re.compile(r"from\(\s*['\"]#__([a-zA-Z0-9_]+)\s+AS\s+a['\"]", re.IGNORECASE)
pattern_join = re.compile(r"join\(\s*['\"][^'\"]*#__([a-zA-Z0-9_]+)\s+AS\s+a[^'\"]*['\"]", re.IGNORECASE)

for path in glob.glob('**/*.php', recursive=True):
    try:
        text = open(path, 'r', encoding='utf-8', errors='ignore').read()
    except Exception:
        continue

    if 'a.client_id' not in text:
        continue

    for table in pattern_from.findall(text):
        tables.add(table)

    for table in pattern_join.findall(text):
        tables.add(table)

for table in sorted(tables):
    print(table)
