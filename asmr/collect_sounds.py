"""Build the cozy ASMR sound library candidates: real recordings from Freesound, CC0 only (free for any use,
no credit needed). For each sound type: search (CC0 filter), keep clips 4 s to 10 min, take the 3 most
downloaded, download the HQ preview, trim to 20 s with fades, level the loudness.

    python asmr/collect_sounds.py OUT_DIR            -> OUT_DIR/sounds/*.mp3 + OUT_DIR/library.json
"""
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

CATS = {
    "Kitchen": [
        ("chop", "Chopping vegetables", "chopping vegetables cutting board"),
        ("slice", "Knife slicing", "knife slicing cucumber"),
        ("sizzle", "Sizzling oil", "sizzling oil pan"),
        ("wok", "Stir fry in a wok", "stir fry wok"),
        ("boil", "Boiling pot", "boiling water pot"),
        ("kettle", "Kettle coming to a boil", "kettle boiling"),
        ("pour_water", "Pouring water", "pouring water"),
        ("pour_tea", "Pouring tea", "pouring tea cup"),
        ("teacup", "Teacup on saucer", "teacup saucer"),
        ("rice", "Washing rice", "washing rice"),
        ("stir", "Stirring a pot", "stirring pot spoon"),
        ("egg", "Cracking eggs", "cracking egg"),
        ("whisk", "Whisking", "whisking bowl"),
        ("knead", "Kneading dough", "kneading dough"),
        ("fry_egg", "Frying an egg", "frying egg"),
        ("peel", "Peeling", "peeling vegetables"),
        ("mortar", "Mortar and pestle", "mortar pestle"),
        ("simmer", "Simmering stew", "simmering"),
        ("dishes", "Washing dishes", "washing dishes"),
    ],
    "Nature": [
        ("rain_roof", "Rain on a roof", "rain roof"),
        ("rain_leaves", "Light rain on leaves", "light rain leaves"),
        ("thunder", "Distant thunder", "distant thunder rain"),
        ("birds", "Morning birds", "morning birds forest"),
        ("stream", "Stream", "stream brook water"),
        ("wind_leaves", "Wind in the trees", "wind leaves trees"),
        ("bamboo", "Bamboo in the wind", "bamboo wind"),
        ("crickets", "Crickets at night", "crickets night"),
        ("frogs", "Frogs by the pond", "frogs pond"),
        ("rooster", "Rooster", "rooster crow"),
        ("chickens", "Chickens", "chickens clucking"),
        ("purr", "Cat purring", "cat purring"),
    ],
    "Fire": [
        ("campfire", "Campfire", "campfire crackling"),
        ("stove", "Wood stove", "wood stove fire"),
        ("fireplace", "Fireplace", "fireplace crackle"),
    ],
    "Homestead": [
        ("axe", "Splitting wood", "chopping wood axe"),
        ("saw", "Hand saw", "hand saw wood"),
        ("broom", "Sweeping", "sweeping broom"),
        ("gravel", "Footsteps on gravel", "footsteps gravel"),
        ("leaves_steps", "Footsteps in leaves", "footsteps leaves"),
        ("snow_steps", "Footsteps in snow", "footsteps snow"),
        ("bucket", "Water bucket", "bucket water"),
        ("digging", "Digging soil", "digging soil shovel"),
        ("garden", "Picking vegetables", "picking vegetables garden"),
        ("door", "Wooden door", "wooden door creak"),
    ],
    "Crafts": [
        ("knit", "Knitting", "knitting needles"),
        ("sew", "Hand sewing", "hand sewing fabric"),
        ("scissors", "Scissors on fabric", "scissors cutting fabric"),
        ("pages", "Turning pages", "page turning book"),
        ("pencil", "Pencil on paper", "pencil writing paper"),
        ("brush", "Brush on paper", "calligraphy brush paper"),
        ("pottery", "Pottery wheel", "pottery wheel clay"),
        ("cloth", "Folding cloth", "folding fabric cloth"),
    ],
}
UA = {"User-Agent": "Mozilla/5.0 (cozy-asmr-library; personal use)"}
ATTR = re.compile(r'data-([a-z0-9-]+)="([^"]*)"')


def search(q, tries=4):
    for k in range(tries):
        res = _search(q)
        if res:
            return res
        time.sleep(60 * (k + 1))                      # empty page = probably throttled: back off and retry
    return []


def _search(q):
    url = "https://freesound.org/search/?" + urllib.parse.urlencode(
        {"q": q, "f": 'license:"Creative Commons 0"'})
    page = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode()
    out = []
    for block in page.split('class="bw-player"')[1:]:
        a = dict(ATTR.findall(block[:2500]))
        if "sound-id" in a and "mp3" in a:
            out.append(dict(id=a["sound-id"], user=html.unescape(a.get("username", "")),
                            title=html.unescape(a.get("title", "")), dur=float(a.get("duration", 0)),
                            downloads=int(a.get("num-downloads", 0) or 0),
                            mp3=a["mp3"].replace("-lq.mp3", "-hq.mp3")))
    return out


def main(out_dir):
    os.makedirs(os.path.join(out_dir, "sounds"), exist_ok=True)
    lj = os.path.join(out_dir, "library.json")
    lib = json.load(open(lj)) if os.path.exists(lj) else []
    done = {x["id"] for x in lib}
    for cat, items in CATS.items():
        for key, name, q in items:
            if f"{key}_1" in done:
                continue
            try:
                res = [r for r in search(q) if 4 <= r["dur"] <= 600]
            except Exception as e:
                print("search failed", q, e, flush=True)
                continue
            seen, picks = set(), []
            for r in sorted(res, key=lambda r: -r["downloads"]):
                if r["id"] not in seen:
                    seen.add(r["id"])
                    picks.append(r)
                if len(picks) == 3:
                    break
            for n, r in enumerate(picks, 1):
                sid = f"{key}_{n}"
                raw = os.path.join(out_dir, "sounds", sid + "_raw.mp3")
                dst = os.path.join(out_dir, "sounds", sid + ".mp3")
                try:
                    data = urllib.request.urlopen(urllib.request.Request(r["mp3"], headers=UA), timeout=60).read()
                    open(raw, "wb").write(data)
                    start = 2.0 if r["dur"] > 30 else 0.0          # skip handling noise at the very start
                    d = min(20.0, r["dur"] - start)
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-t", str(d), "-i", raw,
                                    "-af", f"loudnorm=I=-20:TP=-2:LRA=11,afade=t=in:d=0.3,afade=t=out:st={max(0, d - 0.8)}:d=0.8",
                                    "-ar", "44100", "-b:a", "96k", dst], check=True)
                    os.remove(raw)
                except Exception as e:
                    print("download failed", sid, e, flush=True)
                    continue
                lib.append(dict(id=sid, cat=cat, type=name, title=r["title"], author=r["user"],
                                freesound_id=r["id"], url=f"https://freesound.org/people/{urllib.parse.quote(r['user'])}/sounds/{r['id']}/",
                                full_length=round(r["dur"], 1), clip=round(d, 1), license="CC0"))
                json.dump(lib, open(lj, "w"), indent=1)                    # resumable
                print(f"{sid:16s} {d:5.1f}s  {r['title'][:50]}", flush=True)
                time.sleep(0.5)
            time.sleep(10.0)                                 # be gentle: Freesound throttles bursts
    json.dump(lib, open(os.path.join(out_dir, "library.json"), "w"), indent=1)
    print("total", len(lib))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "asmr_library")
