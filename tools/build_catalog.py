#!/usr/bin/env python3
"""Compact LeetCode catalog (id -> title/slug/difficulty/topics) from prathameshakole/leetcode-problems."""
import json, sys
src, out = sys.argv[1], sys.argv[2]
rows = json.load(open(src)); rows = rows["questions"] if isinstance(rows, dict) else rows
cat = {}
for r in rows:
    try: fid = int(r["frontend_id"])
    except Exception: continue
    cat[fid] = {"t": r["title"], "s": r["problem_slug"], "d": r.get("difficulty", ""), "k": r.get("topics", [])}
json.dump(cat, open(out, "w"), separators=(",", ":"))
print(len(cat), "problems")
