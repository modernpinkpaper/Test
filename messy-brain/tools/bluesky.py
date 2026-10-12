"""Post the next item to Bluesky (one post per run). Runs from GitHub Actions a few times a day.

Needs two secrets (Bluesky -> Settings -> Privacy and security -> App passwords):
    BLUESKY_HANDLE=messybraintidyhome.bsky.social   BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

    python tools/bluesky.py          # post one
    python tools/bluesky.py --dry    # show what would be posted
Remembers what it posted in state/bluesky.json.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402
import images  # noqa: E402

API = "https://bsky.social/xrpc/"
STATE = common.ROOT / "state" / "bluesky.json"


def call(method, body=None, token=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(API + method, data=data, method="POST" if data is not None else "GET")
    req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def queue(cfg):
    """Alternate: find, find, post ... newest live items that were not posted yet."""
    site = cfg["site_url"].rstrip("/")
    tag = cfg["amazon"]["tag_bluesky"]
    finds, posts = [], []
    for f in common.live(common.load_finds()):
        spec = images.find_pin_specs(f)[0]
        finds.append({"key": f"find-{f['id']}", "spec": spec, "alt": f"{f['hook']} — {f['name']}",
                      "text": f"{f['hook']}\n\n{f['why']}", "link": common.amazon_link(f["search"], tag),
                      "link_label": "See it on Amazon", "ad": True})
    for p in common.live(common.load_posts()):
        spec = images.post_pin_specs(p)[0]
        posts.append({"key": f"post-{p['slug']}", "spec": spec, "alt": p["title"],
                      "text": f"{p['title']}\n\n{p['description']}", "link": f"{site}{p['url']}",
                      "link_label": "Read it", "ad": p["type"] == "finds"})
    mixed = []
    while finds or posts:
        mixed += [finds.pop(0) for _ in range(2) if finds]
        if posts:
            mixed.append(posts.pop(0))
    return mixed


def build_post(item):
    tail = "\n\n" + item["link_label"] + " →"
    suffix = " #ad" if item["ad"] else ""
    tags = " #ADHD #HomeOrganization"
    text = item["text"]
    budget = 295 - len(tail) - len(suffix) - len(tags)
    if len(text) > budget:
        text = text[: budget - 1].rsplit(" ", 1)[0] + "…"
    text = text + tail + suffix + tags
    # Link facet over the "Read it →" / "See it on Amazon →" words, hashtag facets for the tags.
    b = text.encode()
    label = (item["link_label"] + " →").encode()
    start = b.rfind(label)
    facets = [{"index": {"byteStart": start, "byteEnd": start + len(label)},
               "features": [{"$type": "app.bsky.richtext.facet#link", "uri": item["link"]}]}]
    for t in ("ADHD", "HomeOrganization"):
        s = b.rfind(("#" + t).encode())
        facets.append({"index": {"byteStart": s, "byteEnd": s + len(t) + 1},
                       "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": t}]})
    return text, facets


def _jpeg(path):
    """Bluesky images must be under ~1 MB; a JPEG of a pin is ~150 KB."""
    import io

    from PIL import Image
    buf = io.BytesIO()
    Image.open(path).convert("RGB").save(buf, "JPEG", quality=88)
    return buf.getvalue()


def main(dry=False):
    cfg = common.config()
    state = json.loads(STATE.read_text()) if STATE.exists() else {"posted": []}
    todo = [i for i in queue(cfg) if i["key"] not in set(state["posted"])]
    if not todo:
        print("bluesky: nothing new to post")
        return
    item = todo[0]
    text, facets = build_post(item)
    if dry:
        print(text, "\n", item["link"])
        return
    img_name = images.render_specs([item["spec"]])[item["spec"]["key"]]
    session = call("com.atproto.server.createSession",
                   {"identifier": os.environ["BLUESKY_HANDLE"], "password": os.environ["BLUESKY_APP_PASSWORD"]})
    token = session["accessJwt"]
    blob = call("com.atproto.repo.uploadBlob", token=token, raw=_jpeg(common.IMG_CACHE / img_name), ctype="image/jpeg")["blob"]
    record = {"$type": "app.bsky.feed.post", "text": text, "facets": facets, "langs": ["en"],
              "createdAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
              "embed": {"$type": "app.bsky.embed.images",
                        "images": [{"image": blob, "alt": item["alt"], "aspectRatio": {"width": 1000, "height": 1500}}]}}
    call("com.atproto.repo.createRecord", {"repo": session["did"], "collection": "app.bsky.feed.post", "record": record}, token=token)
    state["posted"].append(item["key"])
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))
    print("bluesky: posted", item["key"])


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
