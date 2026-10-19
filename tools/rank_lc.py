#!/usr/bin/env python3
"""Rank LeetCode company-tag CSVs (snehasishroy snapshot) with a recency bias.

score = sum over windows of (window_weight * frequency%) — a problem that shows up
in the 30-day list, the 3-month list, the 6-month list *and* the all-time list gets
credit from each window, so recent + frequent problems float to the top.

Usage: rank_lc.py <dataset_dir> <out_dir> slug=Company [slug=Company ...]
"""
import csv, json, os, sys, re

WINDOWS = [  # (file, weight, label)
    ("thirty-days", 4.0, "30d"),
    ("three-months", 3.0, "3mo"),
    ("six-months", 2.0, "6mo"),
    ("more-than-six-months", 0.6, "older"),
    ("all", 1.0, "all"),
]

def pct(s):
    try:
        return float(str(s).strip().rstrip("%"))
    except Exception:
        return 0.0

def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")

def rank(dataset_dir, folder, limit=50):
    probs = {}
    for fname, weight, label in WINDOWS:
        path = os.path.join(dataset_dir, folder, fname + ".csv")
        if not os.path.exists(path):
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try:
                    lid = int(row["ID"])
                except Exception:
                    continue
                p = probs.setdefault(lid, {
                    "lcId": lid, "title": row["Title"].strip(),
                    "url": row["URL"].strip().rstrip("/") + "/",
                    "difficulty": row["Difficulty"].strip(),
                    "acceptance": pct(row.get("Acceptance %")),
                    "score": 0.0, "windows": {}, "recency": "older",
                })
                f = pct(row.get("Frequency %"))
                p["windows"][label] = f
                p["score"] += weight * f
    order = {"30d": 0, "3mo": 1, "6mo": 2, "older": 3, "all": 4}
    for p in probs.values():
        best = min((w for w in p["windows"] if w != "all"), key=lambda w: order[w], default=None)
        p["recency"] = best or "all"
        p["slug"] = slugify(p["title"])
    ranked = sorted(probs.values(), key=lambda p: (-p["score"], p["lcId"]))
    return ranked[:limit], len(probs)

def main():
    dataset_dir, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    summary = []
    for arg in sys.argv[3:]:
        slug, folder = arg.split("=", 1) if "=" in arg else (arg, arg)
        top, total = rank(dataset_dir, folder)
        with open(os.path.join(out_dir, slug + ".json"), "w") as fh:
            json.dump({"company": slug, "folder": folder, "totalTagged": total, "top": top}, fh, indent=1)
        rec = sum(1 for p in top if p["recency"] in ("30d", "3mo", "6mo"))
        summary.append(f"{slug:12s} tagged={total:5d} top={len(top):3d} recent(<=6mo)={rec}")
    print("\n".join(summary))

if __name__ == "__main__":
    main()
