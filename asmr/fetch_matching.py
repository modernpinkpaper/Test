"""Targeted sound fetch: try several searches (CC0 only) and keep only results whose title has one of the keywords,
so a 'hooves' slot can't end up holding a bottle. Replaces KEY_1..KEY_3 in the library.

    python asmr/fetch_matching.py LIB_DIR KEY "Name" "query one|query two" "kw1,kw2"
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_sounds import UA, search  # noqa: E402

lib_dir, key, name, queries, kws = sys.argv[1:6]
kws = [k.strip().lower() for k in kws.split(",")]
seen, picks = set(), []
for q in queries.split("|"):
    for r in sorted(search(q, tries=2), key=lambda r: -r["downloads"]):
        if r["id"] in seen or not (2 <= r["dur"] <= 600) or not any(k in r["title"].lower() for k in kws):
            continue
        seen.add(r["id"])
        picks.append(r)
    time.sleep(8)
    if len(picks) >= 3:
        break
lj = os.path.join(lib_dir, "library.json")
lib = [x for x in json.load(open(lj)) if not x["id"].startswith(key + "_")]
cat = "Foley"
for n, r in enumerate(picks[:3], 1):
    sid = f"{key}_{n}"
    raw, dst = os.path.join(lib_dir, "sounds", sid + "_raw.mp3"), os.path.join(lib_dir, "sounds", sid + ".mp3")
    open(raw, "wb").write(urllib.request.urlopen(urllib.request.Request(r["mp3"], headers=UA), timeout=60).read())
    start = 1.0 if r["dur"] > 30 else 0.0
    d = min(20.0, r["dur"] - start)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-t", str(d), "-i", raw, "-af",
                    f"loudnorm=I=-20:TP=-2:LRA=11,afade=t=in:d=0.05,afade=t=out:st={max(0, d - 0.5)}:d=0.5",
                    "-ar", "44100", "-b:a", "96k", dst], check=True)
    os.remove(raw)
    lib.append(dict(id=sid, cat=cat, type=name, title=r["title"], author=r["user"], freesound_id=r["id"],
                    url=f"https://freesound.org/people/{urllib.parse.quote(r['user'])}/sounds/{r['id']}/",
                    full_length=round(r["dur"], 1), clip=round(d, 1), license="CC0"))
    print(sid, round(d, 1), r["title"][:60], flush=True)
    time.sleep(1)
json.dump(lib, open(lj, "w"), indent=1)
print("kept", len(picks[:3]))
