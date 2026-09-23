"""Check every content file against content/FORMATS.md. Exit code 1 if anything is wrong.

    python tools/check.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402

errors = []
BANNED = re.compile(r"\b(lazy(?![ -]susan)|treats?|cures?|symptoms?|best[- ]?seller|\$\d)", re.I)


def err(where, msg):
    errors.append(f"{where}: {msg}")


def limit(where, field, text, n):
    if text is not None and len(text) > n:
        err(where, f"{field} is {len(text)} chars (max {n})")


def main():
    cfg = common.config()
    boards = set(cfg["pinterest"]["boards"])
    cats = {"kitchen", "laundry", "bathroom", "entryway", "bedroom", "closet", "cleaning", "paper", "kids", "time", "desk", "car"}

    finds = json.loads((common.CONTENT / "finds.json").read_text())
    ids = set()
    for f in finds:
        w = f"finds.json[{f.get('id')}]"
        for k in ("id", "name", "search", "category", "hook", "why", "board"):
            if not f.get(k):
                err(w, f"missing {k}")
        if f.get("id") in ids:
            err(w, "duplicate id")
        ids.add(f.get("id"))
        limit(w, "hook", f.get("hook"), 48)
        limit(w, "why", f.get("why"), 170)
        if f.get("board") not in boards:
            err(w, f"unknown board {f.get('board')!r}")
        if f.get("category") not in cats:
            err(w, f"unknown category {f.get('category')!r}")
        if BANNED.search(json.dumps(f)):
            err(w, f"banned word: {BANNED.search(json.dumps(f)).group(0)}")

    slugs = set()
    for path in sorted((common.CONTENT / "posts").glob("*.json")):
        w = path.name
        try:
            p = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            err(w, f"bad JSON: {e}")
            continue
        for k in ("slug", "date", "type", "title", "description", "board", "intro", "pins"):
            if not p.get(k):
                err(w, f"missing {k}")
        if p.get("slug") in slugs:
            err(w, "duplicate slug")
        slugs.add(p.get("slug"))
        if not path.name.startswith(f"{p.get('date')}-"):
            err(w, "file name must start with the post date")
        limit(w, "description", p.get("description"), 155)
        if p.get("board") not in boards:
            err(w, f"unknown board {p.get('board')!r}")
        if p.get("type") == "finds" and not 5 <= len(p.get("finds", [])) <= 8:
            err(w, "finds posts need 5-8 finds")
        for f in p.get("finds", []):
            if not (f.get("name") and f.get("search") and f.get("why")):
                err(w, "each find needs name, search, why")
        if len(p.get("pins", [])) != 3:
            err(w, "needs exactly 3 pins")
        for pin in p.get("pins", []):
            limit(w, "pin title", pin.get("title"), 48)
            limit(w, "pin sub", pin.get("sub"), 44)
            if pin.get("style") not in ("list", "bold", "note"):
                err(w, f"bad pin style {pin.get('style')!r}")

    for path in sorted((common.CONTENT / "carousels").glob("*.json")):
        w = path.name
        c = json.loads(path.read_text())
        s = c.get("slides", [])
        if not 6 <= len(s) <= 9:
            err(w, "needs 6-9 slides")
        if s and (s[0].get("kind") != "hook" or s[-1].get("kind") != "cta"):
            err(w, "first slide must be hook, last must be cta")
        for sl in s:
            k = sl.get("kind")
            if k == "hook":
                limit(w, "hook title", sl.get("title"), 70)
            if k == "point":
                limit(w, "point title", sl.get("title"), 50)
                limit(w, "point body", sl.get("body"), 180)
            if k == "list":
                if len(sl.get("items", [])) > 6:
                    err(w, "list has more than 6 items")
                for it in sl.get("items", []):
                    limit(w, "list item", it, 45)
            if k == "quote":
                limit(w, "quote", sl.get("title"), 110)
            if k == "cta":
                limit(w, "cta title", sl.get("title"), 60)
                limit(w, "cta body", sl.get("body"), 140)

    if errors:
        print("\n".join(errors))
        print(f"\n{len(errors)} problem(s)")
        sys.exit(1)
    print(f"content OK: {len(finds)} finds, {len(slugs)} posts, {len(list((common.CONTENT / 'carousels').glob('*.json')))} carousels")


if __name__ == "__main__":
    main()
