#!/usr/bin/env python3
"""Merge the LeetCode company-tag rankings (lc/*.json) with the research files
(research/*.json) into a single data.js consumed by index.html.

Usage: merge.py <prep_dir> <out data.js>
"""
import json, os, re, sys, datetime

CAPS = {"dsa": 50, "design": 50, "lld": 30}
CAPS_OVERRIDE = {"google": {"dsa": 100}}  # Google L4 is DSA-only, so give it a deeper list
COMPANIES = [
    # id, name, color, emoji, default level label
    ("google",     "Google",      "#58a6ff", "G", "L4 · SWE III"),
    ("uber",       "Uber",        "#3fd6c2", "U", "L4 · SWE II"),
    ("stripe",     "Stripe",      "#8b7cff", "S", "L2"),
    ("databricks", "Databricks",  "#ff6b4a", "D", "L4 · SWE II"),
    ("airbnb",     "Airbnb",      "#ff5a8a", "A", "L4 · SWE"),
    ("atlassian",  "Atlassian",   "#6d8dff", "At", "P4 · Senior SWE"),
    ("microsoft",  "Microsoft",   "#9ece6a", "M", "61–62 · SDE II"),
    ("amazon",     "Amazon",      "#e3b341", "Am", "L5 · SDE II"),
    ("booking",    "Booking.com", "#4f9cf9", "B", "SWE II / Senior"),
    ("rubrik",     "Rubrik",      "#00b4d8", "R", "MTS-2 / MTS-3"),
    ("coinbase",   "Coinbase",    "#4a7dff", "C", "IC3 / IC4"),
    ("broadcom",   "Broadcom",    "#f85149", "Br", "SMTS / SWE"),
    ("linkedin",   "LinkedIn",    "#2f8fe6", "Li", "SE / Senior SE"),
    ("intuit",     "Intuit",      "#36c5f0", "In", "SE2 / Senior SE"),
    ("apple",      "Apple",       "#c9cfd8", "Ap", "ICT3 / ICT4"),
    ("adobe",      "Adobe",       "#ff4f4f", "Ad", "SDE / Computer Scientist 1"),
    ("nutanix",    "Nutanix",     "#7a5cff", "Nu", "MTS-3 / MTS-4"),
    ("thoughtspot","ThoughtSpot", "#ff8a3d", "Ts", "SE2 / Senior SE"),
    ("arista",     "Arista",      "#2bb673", "Ar", "SWE / Senior SWE"),
    ("nvidia",     "NVIDIA",      "#76b900", "Nv", "SWE / Senior SWE"),
    ("confluent",  "Confluent",   "#1e90ff", "Cf", "SE2 / Senior SE"),
    ("salesforce", "Salesforce",  "#00a1e0", "Sf", "SMTS / LMTS"),
    ("agoda",      "Agoda",       "#ff5a3c", "Ag", "SWE / Senior SWE"),
]
DIFF_FACTOR = {"Easy": 0.55, "Medium": 1.0, "Hard": 1.05}

def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")

def load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

def recency_year(r):
    m = re.search(r"(20\d\d)", str(r or ""))
    return int(m.group(1)) if m else 0

def recency_points(r):
    y = recency_year(r)
    return {2026: 40, 2025: 30, 2024: 15, 2023: 8}.get(y, 3 if y else 0)

def conf_points(c):
    return {"high": 20, "medium": 10, "low": 0}.get(str(c or "").lower(), 8)

def lc_url_id(url):
    m = re.search(r"leetcode\.com/problems/([a-z0-9-]+)", url or "")
    return m.group(1) if m else None

def main():
    prep, out = sys.argv[1], sys.argv[2]
    catalog = load(os.path.join(prep, "lc", "catalog.json"), {})
    by_slug = {v["s"]: int(k) for k, v in catalog.items()}
    by_title = {slugify(v["t"]): int(k) for k, v in catalog.items()}
    lc150 = set(load(os.path.join(prep, "lc", "lc150.json"), {"ids": []})["ids"])

    questions = {}   # id -> record
    companies_out = []
    stats = []

    def lc_record(lid, title=None, url=None, difficulty=None):
        qid = f"lc-{lid}"
        if qid in questions:
            return questions[qid]
        c = catalog.get(str(lid))
        rec = {
            "id": qid, "kind": "dsa", "lcId": lid, "onLeetcode": True,
            "title": (c["t"] if c else title) or f"LeetCode {lid}",
            "url": url or (f"https://leetcode.com/problems/{c['s']}/" if c else ""),
            "difficulty": (c["d"] if c else difficulty) or "",
            "topics": (c["k"] if c else []) or [],
            "lc150": lid in lc150,
            "statement": "", "companies": [],
        }
        questions[qid] = rec
        return rec

    for cid, name, color, emoji, level in COMPANIES:
        lc = load(os.path.join(prep, "lc", f"{cid}.json"), {"top": [], "totalTagged": 0})
        rs = load(os.path.join(prep, "research", f"{cid}.json"), {})
        maxscore = max([p["score"] for p in lc["top"]] + [1.0])
        per_company = {"dsa": {}, "design": {}, "lld": {}}

        # ---- DSA from LeetCode tags
        for p in lc["top"]:
            rec = lc_record(p["lcId"], p["title"], p["url"], p["difficulty"])
            base = p["score"] / maxscore * 100.0
            rank = base * DIFF_FACTOR.get(rec["difficulty"], 1.0)
            per_company["dsa"][rec["id"]] = {
                "q": rec, "score": rank, "lcWindows": p["windows"], "lcRecency": p["recency"],
                "reported": False, "evidence": "", "variant": "", "sources": [], "recency": "",
            }

        # ---- DSA from research
        for it in rs.get("dsa", []) or []:
            lid = it.get("lcId")
            if not lid:
                slug = lc_url_id(it.get("url", ""))
                lid = by_slug.get(slug) if slug else None
            if not lid and it.get("onLeetcode", False):
                lid = by_title.get(slugify(it.get("title", "")))
            if lid:
                rec = lc_record(int(lid), it.get("title"), it.get("url"), it.get("difficulty"))
                entry = per_company["dsa"].get(rec["id"])
                bonus = 40 + recency_points(it.get("recency")) * 0.5 + conf_points(it.get("confidence")) * 0.5
                if entry is None:
                    entry = {"q": rec, "score": 30 + bonus, "lcWindows": {}, "lcRecency": "",
                             "reported": True, "evidence": "", "variant": "", "sources": [], "recency": ""}
                    per_company["dsa"][rec["id"]] = entry
                else:
                    entry["score"] += bonus
                    entry["reported"] = True
                entry["evidence"] = it.get("evidence", "") or entry["evidence"]
                entry["variant"] = it.get("variant", "") or entry["variant"]
                entry["recency"] = it.get("recency", "") or entry["recency"]
                entry["sources"] = list(dict.fromkeys(entry["sources"] + list(it.get("sources") or [])))
                if not rec["topics"] and it.get("topics"):
                    rec["topics"] = it["topics"]
                if not rec["difficulty"] and it.get("difficulty"):
                    rec["difficulty"] = it["difficulty"]
            else:
                qid = f"{cid}-dsa-{slugify(it.get('title',''))[:60]}"
                if not it.get("title") or qid in questions:
                    continue
                rec = {
                    "id": qid, "kind": "dsa", "lcId": None, "onLeetcode": False,
                    "title": it["title"], "url": it.get("url", "") or "",
                    "difficulty": it.get("difficulty", "") or "Medium", "topics": it.get("topics", []) or [],
                    "lc150": False, "statement": it.get("statement", "") or "", "companies": [],
                }
                questions[qid] = rec
                per_company["dsa"][qid] = {
                    "q": rec, "score": 45 + recency_points(it.get("recency")) + conf_points(it.get("confidence")) * 0.5,
                    "lcWindows": {}, "lcRecency": "", "reported": True,
                    "evidence": it.get("evidence", ""), "variant": it.get("variant", ""),
                    "sources": list(it.get("sources") or []), "recency": it.get("recency", ""),
                }

        # ---- design / lld from research
        for kind in ("design", "lld"):
            for it in rs.get(kind, []) or []:
                if not it.get("title"):
                    continue
                qid = f"{cid}-{kind}-{slugify(it['title'])[:60]}"
                if qid in questions:
                    continue
                rec = {
                    "id": qid, "kind": kind, "lcId": None, "onLeetcode": False,
                    "title": it["title"], "url": "", "difficulty": it.get("difficulty", "") or "Medium",
                    "topics": it.get("topics", []) or [], "lc150": False,
                    "statement": it.get("prompt", "") or it.get("statement", "") or "",
                    "probes": it.get("probes", []) or [], "deliverable": it.get("deliverable", "") or "",
                    "round": it.get("round", "") or "", "classic": bool(it.get("classic")), "companies": [],
                }
                questions[qid] = rec
                per_company[kind][qid] = {
                    "q": rec, "score": 10 + (30 if it.get("classic") else 0) + recency_points(it.get("recency")) + conf_points(it.get("confidence")),
                    "lcWindows": {}, "lcRecency": "", "reported": True,
                    "evidence": it.get("evidence", ""), "variant": "",
                    "sources": list(it.get("sources") or []), "recency": it.get("recency", ""),
                }

        # ---- cap + attach
        counts = {}
        for kind, cap in {**CAPS, **CAPS_OVERRIDE.get(cid, {})}.items():
            entries = sorted(per_company[kind].values(), key=lambda e: (-e["score"], e["q"]["title"]))[:cap]
            counts[kind] = len(entries)
            for rank, e in enumerate(entries, 1):
                e["q"]["companies"].append({
                    "id": cid, "rank": rank, "score": round(e["score"], 1),
                    "lcWindows": e["lcWindows"], "lcRecency": e["lcRecency"],
                    "reported": e["reported"], "evidence": e["evidence"], "variant": e["variant"],
                    "sources": e["sources"][:6], "recency": e["recency"],
                })
        proc = rs.get("process", {}) or {}
        companies_out.append({
            "id": cid, "name": name, "color": color, "emoji": emoji,
            "level": level, "levelMapping": rs.get("levelMapping") or "",
            "process": {
                "summary": proc.get("summary", ""), "rounds": proc.get("rounds", []) or [],
                "indiaNotes": proc.get("indiaNotes", ""), "timeline": proc.get("timeline", ""),
                "tips": proc.get("tips", []) or [], "notes": proc.get("notes", ""),
                "sources": (proc.get("sources", []) or [])[:12],
            },
            "lcTagged": lc.get("totalTagged", 0), "counts": counts,
            "researched": bool(rs),
        })
        stats.append(f"{name:12s} dsa={counts['dsa']:2d} design={counts['design']:2d} lld={counts['lld']:2d} researched={bool(rs)}")

    # drop questions no company kept
    qs = [q for q in questions.values() if q["companies"]]
    data = {
        "generatedAt": datetime.date.today().isoformat(),
        "lcSnapshot": "2026-07-12",
        "companies": companies_out,
        "questions": qs,
    }
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("window.PREP_DATA=")
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    print("\n".join(stats))
    print(f"questions={len(qs)} size={os.path.getsize(out)//1024}KB")
    idx = os.path.join(os.path.dirname(out), "index.html")
    if os.path.exists(idx):
        html = open(idx, encoding="utf-8").read()
        stamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
        html2 = re.sub(r'src="data\.js[^"]*"', f'src="data.js?v={stamp}"', html)
        if html2 != html:
            open(idx, "w", encoding="utf-8").write(html2)
            print(f"cache-busted index.html -> data.js?v={stamp}")

if __name__ == "__main__":
    main()
