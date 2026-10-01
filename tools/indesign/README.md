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

## 1. Test it the quick way (double-click)

1. Open InDesign.
2. Open the Scripts panel: **Window → Utilities → Scripts**.
3. In the panel, right-click the **User** folder → **Reveal in Explorer**.
4. Copy `mpp-indesign-logger.jsx` into the folder that opens.
5. Back in InDesign, the script now shows in the Scripts panel. **Double-click it.**
6. Do some normal work: open a document, click a text box, change a tool, apply a swatch, save.
7. Check the log. By default it is here:

   ```
   C:\Users\<you>\AppData\Local\MT Log\indesign\mpp-indesign-<today>.jsonl
   ```

   (If that folder can't be made it falls back to `Documents\MT Log\indesign\`.)

Each line is one action, for example:

```json
{"ts":"2026-10-01T14:03:22","event":"indesign_doc_open","doc":"Spring Catalog.indd","details":{"doc":"Spring Catalog.indd"}}
{"ts":"2026-10-01T14:03:40","event":"indesign_selection","doc":"Spring Catalog.indd","details":{"doc":"Spring Catalog.indd","kind":"TextFrame","script_label":"headline","page":"3","fill":"PANTONE 185 C"}}
{"ts":"2026-10-01T14:04:05","event":"indesign_tool","doc":"Spring Catalog.indd","details":{"doc":"Spring Catalog.indd","tool":"TYPE_TOOL"}}
{"ts":"2026-10-01T14:05:11","event":"indesign_edit","doc":"Spring Catalog.indd","details":{"doc":"Spring Catalog.indd"}}
{"ts":"2026-10-01T14:06:00","event":"indesign_doc_save","doc":"Spring Catalog.indd","details":{"doc":"Spring Catalog.indd"}}
```

To stop it, just quit InDesign. Running the script again restarts it cleanly (it never
stacks up duplicate loggers).

---

## 2. Make it start on its own (no clicking)

Put the file in InDesign's **startup scripts** folder and it runs every time InDesign opens:

```
C:\Program Files\Adobe\Adobe InDesign <version>\Scripts\startup scripts\
```

Create the `startup scripts` folder if it isn't there, drop the `.jsx` in, and restart
InDesign. That's it.

---

## 3. Send it into MT Log (when you're ready)

Open `mpp-indesign-logger.jsx` in any text editor and edit the **SETTINGS** block at the top:

```js
SEND_TO_MT_LOG: true,                         // turn it on
SHARED_SECRET: "the-real-shared-secret",      // same value as MT Log's config.json
```

The secret must match `local_api.shared_secret` in MT Log's `config.json` (ask the admin).
From then on, every InDesign action is also posted to MT Log's local API on
`127.0.0.1:47821`, signed the same way the Tampermonkey helper signs its events. It still
keeps writing the local file too, unless you set `LOG_TO_FILE: false`.

In MT Log these arrive as normal events with:

- `collector: "local_api"`
- `script_name: "MPP InDesign Logger"`
- `event_type:` one of `indesign_doc_open`, `indesign_doc_close`, `indesign_doc_save`,
  `indesign_doc_active`, `indesign_selection`, `indesign_tool`, `indesign_edit`,
  `indesign_logger_started`
- all the InDesign details inside `data`.

If MT Log isn't running, nothing breaks — the post quietly fails and InDesign carries on.

---

## What it can and can't see

**It can see:** the active document name, the type of object selected (text frame,
rectangle, graphic, etc.), the object's **script label**, the page it's on, the applied
fill/stroke **swatch**, the selected **tool**, text styles on a text selection, and the
moments you edit and save.

**It can't see (yet):** the exact keystrokes or the before/after text of an edit, or which
menu command you ran. InDesign doesn't give scripts a general "this exact thing changed"
event, so the logger infers activity from selection, tool, and the document's
unsaved-changes flag. That's plenty to reconstruct *what you worked on and for how long*,
which is what the reports need. Deeper per-change capture (e.g. listening to specific menu
actions) can be added later if you want it.

---

## Settings reference

| Setting | Default | What it does |
|---|---|---|
| `LOG_TO_FILE` | `true` | Write the daily `.jsonl` file. |
| `SEND_TO_MT_LOG` | `false` | Also post each action to MT Log's local API. |
| `SHARED_SECRET` | *(placeholder)* | Must match MT Log's `local_api.shared_secret`. |
| `PORT` | `47821` | MT Log's local API port. |
| `POLL_MS` | `2000` | How often it checks the tool / active doc / unsaved flag. |
| `SELECTION_MIN_GAP_MS` | `800` | Don't log the same selection more than once this often. |
| `OUTPUT_FOLDER` | *(empty)* | Leave empty for the default folder, or set a full path. |
