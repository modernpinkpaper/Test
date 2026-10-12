"""Make the monthly Pinterest bulk-upload file (extra pins on top of the automatic RSS pins).

    python tools/pinterest_csv.py            # next 30 days -> build/pinterest/pins-<start>-partN.csv

Upload: Pinterest (desktop) -> Create -> "Create Pins in bulk" -> upload each CSV (max 200 rows each).
The pins are scheduled, so they publish on their own over the month.
It remembers what it already exported (state/pinterest_csv.json) so next month has no repeats.
Run it AFTER the site is deployed with the same content, so the image URLs work.
"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402
import images  # noqa: E402

STATE = common.ROOT / "state" / "pinterest_csv.json"
HOURS = [13, 15, 17, 19, 21, 23, 1, 3, 14, 16, 18, 20, 22, 0, 2, 12, 13, 15, 17, 19]  # UTC = US morning..night
HEADERS = ["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link", "Publish date", "Keywords"]


def candidates(cfg, site, until):
    tag = cfg["amazon"]["tag_pinterest"]
    rows = []
    for f in common.live(common.load_finds(), until):
        spec = images.find_pin_specs(f)[1]           # the 'findnote' design -> straight to Amazon
        rows.append({"key": spec["key"], "date": f["date"], "Title": f["hook"],
                     "Media URL": f"{site}/pins/{images.image_name(spec)}", "Pinterest board": f.get("board", "Amazon Home Finds"),
                     "Description": f"{f['why']} {f['name']} on Amazon. #ad affiliate link",
                     "Link": common.amazon_link(f["search"], tag),
                     "Keywords": ", ".join(["adhd home", f.get("category", "home") + " organization", "amazon finds"])})
    for p in common.live(common.load_posts(), until):
        for spec in images.post_pin_specs(p)[1:]:      # designs 2 and 3 -> our post (design 1 goes out by RSS)
            rows.append({"key": spec["key"], "date": p["date"], "Title": spec["title"],
                         "Media URL": f"{site}/pins/{images.image_name(spec)}", "Pinterest board": p.get("board", "ADHD Home Organization"),
                         "Description": p["description"] + (" #ad" if p["type"] == "finds" else ""),
                         "Link": f"{site}{p['url']}", "Keywords": ", ".join(p.get("keywords", [])[:5])})
    return rows


def main(days=30):
    cfg = common.config()
    site = cfg["site_url"].rstrip("/")
    start = common.today() + dt.timedelta(days=1)
    state = json.loads(STATE.read_text()) if STATE.exists() else {"exported": []}
    done = set(state["exported"])
    pool = [r for r in candidates(cfg, site, start + dt.timedelta(days=days)) if r["key"] not in done]
    ramp = cfg["schedule"]["pinterest_csv_pins_per_day"]
    sched_start = dt.date.fromisoformat(cfg["schedule"]["start"])

    out = []
    for d in range(days):
        day = start + dt.timedelta(days=d)
        n = common.per_day(ramp, (day - sched_start).days)
        ready = [r for r in pool if r["date"] <= day][:n]   # never schedule a pin before its page/image exists
        for i, r in enumerate(ready):
            pool.remove(r)
            hour = HOURS[i % len(HOURS)]
            when = dt.datetime.combine(day + (dt.timedelta(days=1) if hour < 12 else dt.timedelta()), dt.time(hour, 7 * i % 60))
            r["Publish date"] = when.strftime("%Y-%m-%dT%H:%M:%S")
            out.append(r)

    folder = common.BUILD / "pinterest"
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for part in range(0, len(out), 200):
        path = folder / f"pins-{start.isoformat()}-part{part // 200 + 1}.csv"
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=HEADERS, extrasaction="ignore")
            w.writeheader()
            for r in out[part:part + 200]:
                w.writerow({**r, "Thumbnail": ""})
        files.append(path)
    state["exported"] = sorted(done | {r["key"] for r in out})
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))
    print(f"pinterest csv: {len(out)} pins over {days} days -> " + ", ".join(str(f) for f in files))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
