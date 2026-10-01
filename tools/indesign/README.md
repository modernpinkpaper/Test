# MT Log — InDesign logger (`.jsx`)

This is a small script that runs **inside Adobe InDesign** and writes down what you do
while you design: which document you opened, which object or text box you clicked (and its
script label, if it has one), which tool you picked, which swatch/ink colour you applied,
and when you edited or saved. One plain-text file per day.

It answers the questions you asked:

- **Does it log everything on InDesign for the date?** Yes — one file per day holds the
  whole day (`mpp-indesign-2026-10-01.jsonl`).
- **Do I double-click to start it?** You double-click it **once** per InDesign session (or
  let it auto-start — see below). After that it keeps logging on its own until you quit
  InDesign. You do not keep clicking.
- **Does it live in MT Log?** It can. By default it only writes its own file so you can
  test it with nothing else running. When you're ready, flip one setting and it also hands
  every action to MT Log through the same local API your Tampermonkey scripts use, so it
  lands in the normal MT Log alongside everything else on the PC.

---

## 1. Set the secret, then install

First, open `mpp-indesign-logger.jsx` in any text editor and paste in the shared secret
(the one in MT Log's `config.json` → `local_api.shared_secret`; ask the admin):

```js
SHARED_SECRET: "the-real-shared-secret",
```

It is already set to send to MT Log (`SEND_TO_MT_LOG: true`). Then:

1. Open InDesign.
2. Open the Scripts panel: **Window → Utilities → Scripts**.
3. In the panel, right-click the **User** folder → **Reveal in Explorer**.
4. Copy `mpp-indesign-logger.jsx` into the folder that opens.
5. Back in InDesign, the script now shows in the Scripts panel. **Double-click it.**
6. Do some normal work — it now feeds MT Log live. (Or set it to auto-start — section 2.)

To stop it, just quit InDesign. Running the script again restarts it cleanly (it never
stacks up duplicate loggers).

### Want to eyeball the output while testing?

Set `LOG_TO_FILE: true` and it also writes a local copy you can open:

```
C:\Users\<you>\AppData\Local\MT Log\indesign\mpp-indesign-<PC>-<today>.jsonl
```

Each line is one action, for example:

```json
{"ts":"2026-10-01T14:03:40","event":"indesign_selection","doc":"Spring Catalog.indd","details":{"kind":"TextFrame","script_label":"headline","page":"3","fill":"PANTONE 185 C"}}
{"ts":"2026-10-01T14:04:05","event":"indesign_tool","doc":"Spring Catalog.indd","details":{"tool":"TYPE_TOOL"}}
{"ts":"2026-10-01T14:05:02","event":"indesign_swatch_changed","doc":"Spring Catalog.indd","details":{"swatch":"PANTONE 185 C","from":"CMYK(0,100,100,0)","to":"CMYK(0,80,80,0)"}}
{"ts":"2026-10-01T14:05:30","event":"indesign_attr_changed","doc":"Spring Catalog.indd","details":{"attr":"stroke_weight","from":1,"to":2}}
{"ts":"2026-10-01T14:06:00","event":"indesign_doc_save","doc":"Spring Catalog.indd","details":{"doc":"Spring Catalog.indd"}}
```

---

## 2. Make it start on its own (no clicking)

Put the file in InDesign's **startup scripts** folder and it runs every time InDesign opens:

```
C:\Program Files\Adobe\Adobe InDesign <version>\Scripts\startup scripts\
```

Create the `startup scripts` folder if it isn't there, drop the `.jsx` in, and restart
InDesign. That's it.

---

## 3. How it reaches MT Log

Every InDesign action is posted live to MT Log's local API on `127.0.0.1:47821`, signed
the same way the Tampermonkey helper signs its events. MT Log then stamps each one with
this **PC's name**, the **employee**, and the **date**, and files it in that person's day
automatically — so there's no filename or folder for you to manage.

In MT Log these arrive as normal events with:

- `collector: "local_api"`
- `script_name: "MPP InDesign Logger"`
- `event_type:` one of `indesign_doc_open`, `indesign_doc_close`, `indesign_doc_save`,
  `indesign_doc_active`, `indesign_selection`, `indesign_tool`, `indesign_edit`,
  `indesign_command`, `indesign_script_run`, `indesign_swatch_added`,
  `indesign_swatch_changed`, `indesign_swatch_renamed`, `indesign_swatch_removed`,
  `indesign_moved`, `indesign_resized`, `indesign_rotated`, `indesign_attr_changed`,
  `indesign_logger_started`
- all the InDesign details inside `data`.

If MT Log isn't running or the secret is wrong, nothing breaks — the post quietly fails
and InDesign carries on.

---

## What it can and can't see

**It can see:**
- the active document name, and opens / closes / saves (the `@125%` zoom noise is stripped);
- the type of object selected, its **script label** (even while you're typing in the box),
  the page, and the applied fill/stroke **swatch**;
- the selected **tool**;
- **swatch edits** — a swatch added, removed, renamed, or **recoloured, and to what**
  (e.g. `PANTONE 185 C: CMYK(0,100,100,0) -> CMYK(0,80,80,0)`);
- **changes on the selected object** — **position (x/y) and how far it moved (dx/dy)**,
  **size (width/height)**, **rotation**, stroke colour/weight/style, fill, opacity, and for
  text the font, size, and paragraph/character style — reporting **what changed to what**;
- **menu commands** you run (Export, Print, Place, …) and **menu-scripts**;
- when you edit and save.

**It can't see:**
- Raw **keystrokes / shortcuts** — InDesign never exposes the keyboard to scripts (the
  *result*, like the tool changing, is still caught).
- The **actual text** you typed — only lengths/structure, on purpose, to keep the log
  small and avoid copying customer text.
- A **panel being clicked or opened** (Swatches, Stroke, …) — InDesign fires no panel
  event. But the *result* of using those panels is captured (see the swatch/stroke/style
  items above), which is the useful part.
- **Scripts double-clicked in the Scripts panel** — no event for those. Scripts run from a
  **menu** are caught; for panel scripts, add one reporting line inside the script (ask and
  I'll give you the snippet).

---

## Settings reference

| Setting | Default | What it does |
|---|---|---|
| `SEND_TO_MT_LOG` | `true` | Post each action live to MT Log's local API. |
| `SHARED_SECRET` | *(placeholder)* | Must match MT Log's `local_api.shared_secret`. **Fill this in.** |
| `PORT` | `47821` | MT Log's local API port. |
| `LOG_TO_FILE` | `false` | Optional local `.jsonl` copy (off — MT Log is the destination). Turn on to eyeball output while testing. |
| `POLL_MS` | `2000` | How often it checks tool / doc / swatch edits / stroke & style changes. |
| `SELECTION_MIN_GAP_MS` | `800` | Don't log the same selection more than once this often. |
| `WATCH_SWATCHES` | `true` | Watch for swatch add/remove/rename/recolour. |
| `WATCH_ATTRS` | `true` | Watch stroke/fill/style/font/size changes on the selected object. |
| `LOG_COMMANDS` | `true` | Log menu commands and menu-scripts. |
| `KEEP_BACKUP_DAYS` / `OUTPUT_FOLDER` | `30` / *(empty)* | Only used if `LOG_TO_FILE` is on. |
