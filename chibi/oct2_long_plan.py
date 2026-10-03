"""Shot plan for the long Oct 2 vlog: what is on screen for every voice line (oct2_long_lines.py).

SHOTS[i] belongs to LINES[i]. A shot is a dict:
    clock   the log time shown in the header ("8:15"); a (start, end) pair makes the clock run fast (time-lapse)
    scr     a screen key, or [(at, key), ...] to switch screens during the line
    cam     [(at, target)]: target is a data-t box name, "full", or (cx, cy, zoom) in screen CSS px
    cur     [(at, target)] mouse moves; clicks: [at, ...] (mouse click sound + ripple at the cursor)
    keys    [(at0, at1)] keyboard sound between two moments
    sfx     [(at, name)] extra sounds
    face    chibi face for the line (default from the tone tag)
    fx      special overlays: "title", "montage", "confetti", "stats", "counter", "end"
"at" is a word in the line (its first match), a fraction 0..1 of the line, or a number of seconds ("1.2s").
Every screen key is built by screen_jobs() below with fake data only.
"""

# ------------------------------------------------------------------ screen states (key -> (screen, state))
J = {}


def s(key, scr_name, clock, **st):
    J[key] = (scr_name, dict(st, clock=clock))
    return key


T_TYPO = "wow it gave me tons of rtecs the second i started it.. how?? i bareely did anything... did it read my lgos fromt oday so far"
T_ENV = "btw.. using enviroment variables.. whats that about? its like holding api keys for programs installed on windows?"
T_WHY = "ok.. but my question is.. why didnt you make it into a program like mt log? u dont need to.. but just curious?"
T_QUIT = "honestly i dont like the assistant thing.. id rather just ask my claude chat thats connected to my logs when i want to"
A = lambda t, *k: ("a", t, *k)  # noqa: E731
U = lambda t, *k: ("u", t, *k)  # noqa: E731


def screen_jobs():
    J.clear()
    # hook
    s("printq", "printq", "3:02 PM")
    s("printq_hl", "printq", "3:02 PM", hl=1)
    # sync
    s("sales_toast", "sheets_sales", "8:00 AM", rows=8, toast=1)
    s("sales_new", "sheets_sales", "8:00 AM", rows=9, flash=1, sum=1)
    # check-in
    s("teams_vid", "teams_video", "8:15 AM")
    s("player1", "video_player", "8:16 AM", k=0.08)
    s("player2", "video_player", "8:17 AM", k=0.21)
    s("msgs0", "sc_messages", "8:19 AM")
    s("msgs_open", "sc_messages", "8:19 AM", open=0, read=1)
    s("msgs_read", "sc_messages", "8:20 AM", open=3, read=4)
    s("listing", "amazon_listing", "8:20 AM")
    # MT Log
    s("cl_links", "claude", "8:21 AM", on=0, conv=[U("can u give me the download links for the new mt log and the indesign logger"),
      A("<p>Here you go:</p><p>1. <b style='color:#c96442'>MTLog-win-x64.zip</b> (the new version)<br>2. <b style='color:#c96442'>mpp-indesign-logger.jsx</b> (drop it in InDesign's Startup Scripts folder)</p><p>Uninstall the old MT Log first.</p>")])
    s("prog_sel", "programs", "8:25 AM", sel=1)
    s("prog_confirm", "programs", "8:25 AM", sel=1, confirm=1)
    s("prog_setup40", "programs", "8:26 AM", gone=1, setup=40)
    s("prog_setup100", "programs", "8:27 AM", gone=1, setup=100)
    s("startup_drag", "startup_scripts", "8:33 AM", drag=1, downloads=1)
    s("startup_drop", "startup_scripts", "8:33 AM", dropped=1)
    s("fallbreak", "teams_chat", "8:36 AM", msgs=[("them", "morning! envelopes for the 3 rush orders are loaded", "", "8:31 AM"),
      ("me", "fyi my kid's school is closed for fall break next week so i'll be in and out 🙃", "fb", "8:36 AM")])
    # assistant
    s("as0", "assistant", "8:44 AM", cards=0)
    for n in (1, 3, 5, 7):
        s(f"as{n}", "assistant", "8:51 AM", cards=n)
    s("as_hl", "assistant", "8:53 AM", cards=7, hl=1)
    for k in (0.25, 0.5, 0.75, 1.0):
        s(f"typo{int(k * 100)}", "claude", "8:51 AM", on=1, conv=[U("i did it.. i hit enter..")], typing=T_TYPO[:int(len(T_TYPO) * k)])
    s("typo_sent", "claude", "8:51 AM", on=1, conv=[U("i did it.. i hit enter.."), U(T_TYPO, "typo"),
      A("<p>Ha! It probably did read today's logs. It looks at everything since you started MT Log this morning, so it already had about 40 minutes of you to work with.</p>")])
    # setup
    s("keys0", "console", "8:54 AM")
    s("keys1", "console", "8:55 AM", new=1)
    s("env_new", "envvars", "8:57 AM", newdlg=("ANTHROPIC_API_KEY", "sk-ant-api03-••••••••••••••••XyZ"))
    s("env_k1", "envvars", "8:57 AM", k1=1)
    s("model", "assistant", "9:00 AM", cards=7, countdown="now using Claude")
    s("as_proj", "apps_script", "9:10 AM", name="ai mt log recs")
    s("as_new", "apps_script", "9:12 AM", name="ai mt log recs", dlg="new")
    s("as_done", "apps_script", "9:13 AM", name="ai mt log recs", dlg="done")
    s("env_k2", "envvars", "9:13 AM", k1=1, k2=1)
    s("as_plus", "apps_script", "9:11 AM", name="Dalia project manager")
    for k in (0.5, 1.0):
        s(f"env_q{int(k * 100)}", "claude", "9:14 AM", on=1, conv=[U(T_TYPO), A("<p>Ha! It probably did read today's logs.</p>")], typing=T_ENV[:int(len(T_ENV) * k)])
    s("env_a", "claude", "9:14 AM", on=1, conv=[U(T_ENV), A("<p>Yes, exactly. An <b>environment variable</b> is a named value Windows keeps for programs, like a labeled jar. "
      "The assistant reads <code>ANTHROPIC_API_KEY</code> from there, so the key never sits inside the script itself.</p>")])
    s("ps1", "powershell", "9:18 AM", lines=["PS C:\\Users\\User&gt; cd .\\MppAssistant", "PS C:\\Users\\User\\MppAssistant&gt; .\\setup.ps1",
      "<span style='color:#f9f1a5'>Checking Python... ok</span>", "<span style='color:#f9f1a5'>Checking ANTHROPIC_API_KEY... ok</span>"])
    s("ps2", "powershell", "9:19 AM", lines=["PS C:\\Users\\User\\MppAssistant&gt; .\\setup.ps1", "<span style='color:#f9f1a5'>Checking ANTHROPIC_API_KEY... ok</span>",
      "<span style='color:#e74856'>.\\setup.ps1 : File cannot be loaded because running scripts is disabled on this system.</span>",
      "<span style='color:#e74856'>    + CategoryInfo          : SecurityError: (:) [], PSSecurityException</span>", "PS C:\\Users\\User\\MppAssistant&gt; gcloud auth login",
      "<span style='color:#e74856'>gcloud : The term 'gcloud' is not recognized as the name of a cmdlet...</span>", "PS C:\\Users\\User\\MppAssistant&gt; _"])
    s("gcloud", "gcloud", "9:20 AM")
    s("why", "claude", "9:22 AM", on=1, conv=[U(T_WHY), A("<p>Fair question! I kept it as a small Python script so it's easy to change while we test. "
      "If you want it to feel like a program, save a <b>Start Assistant.cmd</b> on your desktop and double-click it.</p>")])
    s("saveas_cmd", "notepad", "9:23 AM", tabs=["Start Assistant.cmd"], text=["@echo off", "cd /d %USERPROFILE%\\MppAssistant", "python assistant.py", "pause"],
      saveas="Start Assistant.cmd")
    s("countdown", "assistant", "9:09 AM", cards=7, countdown="0:38")
    s("mem", "notepad", "9:27 AM", tabs=["memory.md", "learned.json", "recommendations.json"], on=0,
      text=["# What I know about this shop", "- Orders: Amazon, Etsy, Shopify", "- Printing: InDesign + 2 printers + DYMO labels", "- Team checks Amazon messages 3x a day", "", "# Open questions",
            "- Which screenshots are useful for SOPs?"])
    s("learned", "notepad", "9:28 AM", tabs=["memory.md", "learned.json", "recommendations.json"], on=1,
      text=["{", '  "apps_used_today": 14,', '  "longest_task_minutes": 52,', '  "repeat_actions": ["copy order id", "open customization"],', '  "shortcuts_seen": ["Ctrl+Shift+V"]', "}"])
    s("recs", "notepad", "9:29 AM", tabs=["memory.md", "learned.json", "recommendations.json"], on=2,
      text=["[", '  {"card": "Batch your Amazon replies", "shown": 1},', '  {"card": "Great job using Ctrl + Shift + V!", "shown": 1},', '  {"card": "Close unused Chrome tabs", "shown": 1}', "]"])
    # review
    s("rev_player1", "video_player", "9:44 AM", k=0.15)
    s("rev_player2", "video_player", "10:20 AM", k=0.72)
    s("proofs", "proofs", "10:41 AM", sel=1)
    s("results", "notepad", "10:44 AM", tabs=["proof_results.txt"], text=["AUTO PROOFS - 10/02/2026 9:39 AM", "", "7612 - SAMPLE ORDER A - 20 - FLAT    proof made   sent ✓",
      "7614 - SAMPLE ORDER B - 10 - FLD     proof made   sent ✓", "7619 - SAMPLE ORDER C - 50 - FLD     proof made   sent ✓", "", "3 of 3 done · 0 errors"])
    s("proofs_copy", "proofs", "11:06 AM", copy=1, sel=2)
    s("proofs_ren", "proofs", "11:06 AM", copy=1, sel=2, rename=1)
    s("reload_q", "teams_chat", "11:20 AM", msgs=[("them", "the reload worked, it made a new proof 👍", "", "11:18 AM"),
      ("me", "ok but when a customer asks for another proof and it gets reloaded.. does the right follow up message go out to them?", "rq", "11:20 AM")])
    s("waiting", "sc_messages", "11:21 AM", read=0)
    # shopify
    s("shopify", "shopify", "11:30 AM")
    s("cost", "console", "11:36 AM", page="cost")
    s("track1", "tracker", "11:40 AM", hl={1})
    s("track2", "tracker", "11:41 AM", hl={2})
    s("cs_save", "notepad", "11:47 AM", tabs=["Shopify CS script 10.1.26"], text=["▸ Proof questions (collapsed)", "▸ Shipping and tracking (collapsed)", "▸ Changes after printing (collapsed)",
      "▾ Reprints", "    1. Ask for a photo", "    2. Check the proof they approved", "    3. Offer reprint or refund", "▸ Wholesale (collapsed)"], saveas="Shopify CS script 10.1.26")
    s("bee", "bee", "11:49 AM", who="Jess", msgs=[("me", "can we go over the new cs script today?", "11:47"), ("them", "ok after work it is..", "11:49")])
    # quit
    for k in (0.5, 1.0):
        s(f"quit{int(k * 100)}", "claude", "11:57 AM", on=1, conv=[U(T_WHY), A("<p>Fair question! I kept it as a small Python script so it's easy to change while we test.</p>")],
          typing=T_QUIT[:int(len(T_QUIT) * k)])
    s("quit_a", "claude", "11:57 AM", on=1, conv=[U(T_QUIT, "quit"), A("<p>Totally fair. You don't need cards popping up. Your chat already has your logs, so you can just ask me "
      "<i>\"what did I do today?\"</i> whenever you want. I'll write down how to remove the assistant so nothing is left running.</p>")])
    s("rein40", "programs", "11:59 AM", gone=1, setup=40)
    s("rein100", "programs", "12:00 PM", gone=1, setup=100)
    # pop-ups
    s("cust0", "sc_customize", "12:08 PM")
    s("cust1", "sc_customize", "12:11 PM", label="dsadasdasdasd", x="-5")
    s("cust2", "sc_customize", "12:12 PM", label="dsadasdasdasd", x="122", h="6")
    s("pop1", "amazon_popup", "12:12 PM", fields={"Name of Host": "Sample Host"})
    s("pop2", "amazon_popup", "12:30 PM", fields={"Name of Host": "Sample Host", "Time": "8 am", "RSVP Info and/or Additional Text to Print": "please bring your favorite bottle of"})
    # win
    s("wf0", "workflow", "12:18 PM", stage=None, msgs=[A("Hi! Tell me what you want this workflow to do, or pick a template.")])
    s("wf_typing", "workflow", "12:19 PM", stage=None, msgs=[A("Hi! Tell me what you want this workflow to do, or pick a template.")],
      typing="get me the customization details for every order that is not shipped yet")
    s("wf_prev", "workflow", "12:21 PM", stage="preview0", msgs=[A("Hi! Tell me what you want this workflow to do, or pick a template."),
      U("get me the customization details for every order that is not shipped yet"), A("Here's a preview on 5 unshipped orders.")])
    s("wf_q", "workflow", "1:13 PM", stage="preview0", msgs=[U("well i previewed it but it didnt return wqirh any cuwstomizations"),
      A("Thanks! I'll add the Amazon Custom fields to the export."),
      U("well if it runs at 7 am on monday, then on tuesday it runs again.. will it also pull the orders that already were pulled the day before?"),
      A("Yes. It pulls every order that is still unshipped at run time.")])
    s("wf_not", "workflow", "1:22 PM", stage="preview0", msgs=[A("Yes. It pulls every order that is still unshipped at run time.")], typing="what order details does it NOT")
    s("wf_name", "workflow", "1:30 PM", stage="setup", name="Unshipped Orders Customization Export", msgs=[A("Ready when you are. Name it and turn it on.")])
    s("wf_on", "workflow", "1:30 PM", stage="setup", name="Unshipped Orders Customization Export", on=1, msgs=[A("Ready when you are. Name it and turn it on.")])
    s("wf_ran", "workflow", "1:32 PM", stage="setup", name="Unshipped Orders Customization Export", on=1, ran=1, msgs=[A("Done! 72 orders exported.")])
    s("csv", "csv_view", "1:33 PM")
    s("zip", "zipview", "1:34 PM", sel=0)
    s("zip_xml", "zipview", "1:35 PM", sel=0, xml=1)
    s("csv_match", "csv_view", "1:40 PM", match=1)
    # printer
    s("rules", "github_md", "12:34 PM")
    s("blank", "gdoc", "12:35 PM", tabs=[(("#4285f4", "≡"), "Untitled document - Google Docs"), (("#4285f4", "≡"), "Untitled document - Google Docs")], active=1)
    P49 = ("<h1 style='font-size:24px;margin-bottom:10px'>P-049 · AI drafts staff meeting notes</h1><p>Use production numbers to draft the weekly team meeting notes.</p>"
           "<h2 style='font-size:18px;margin:14px 0 6px'>Inputs</h2><p>Orders per person, reprints, late orders, printer issues.</p>")
    P88 = ("<div style='font:700 24px Arial;margin-bottom:10px'>P-088 · MT Log for data collection</div><div style='font:700 24px Arial;margin:16px 0 6px'>What it logs</div>"
           "<p>Apps, clicks, typed fields, prints, files.</p><div style='font:700 24px Arial;margin:16px 0 6px'>Why</div><p>See where the day goes.</p>")
    s("p49", "gdoc", "12:41 PM", title="P-049 - AI REPLACE: staff meeting notes", content=P49, print=1)
    s("p88", "gdoc", "12:52 PM", title="P-088 - MT Log - for data collection", content=P88)
    s("p88_print", "gdoc", "12:52 PM", title="P-088 - MT Log - for data collection", content=P88, print=1)
    s("printq2", "printq", "12:53 PM", hl=1)
    # orders
    s("mailmsg", "mail_msg", "1:01 PM")
    s("schome", "sc_home", "1:18 PM")
    s("custmsg", "teams_chat", "1:20 PM", msgs=[("them", "testing the amazon messages script now", "", "1:12 PM"),
      ("me", "sometimes customers message just to double check their customization details.. can ur amazon messages test handle that?", "cm", "1:20 PM")])
    s("indd", "indesign", "1:24 PM", dirty=1)
    s("indd8", "indesign", "1:32 PM", dirty=1, mins=8)
    # timing
    chart = ("<p>Here's regular-order time per order, before and after break:</p><div data-t='chart' style='display:flex;align-items:flex-end;gap:14px;height:200px;padding:10px 0;"
             "border-bottom:2px solid #ccc'>" + "".join(f"<div style='flex:1;height:{h}%;background:{c};border-radius:4px 4px 0 0'></div>" for h, c in
                                                          ((52, "#87867f"), (60, "#87867f"), (48, "#87867f"), (64, "#d97757"), (100, "#c5221f"), (58, "#d97757")))
             + "</div><p style='font-family:Inter;font-size:13px;color:#73726c'>gray = before break · orange = after</p><p><b>One thing looks off:</b> one person shows "
               "<b style='color:#c5221f'>idle 26 min</b> on every order after break.</p>")
    s("timing", "claude", "2:13 PM", on=2, conv=[U("can u compare the team's timing on regular orders before and after break"), A(chart)])
    s("sorry", "teams_chat", "2:20 PM", msgs=[("them", "i was waiting on the next batch, i thought we were supposed to wait", "", "2:18 PM"),
      ("me", "my apologies for not communicating properly. that one is on me 💗", "sorry", "2:20 PM")])
    # wrap
    s("ord0", "sc_order", "2:43 PM")
    s("ord1", "sc_order", "2:44 PM", note="DO NOT TOUCH - waiting on customer to reply by 10/5")
    s("wflink", "teams_chat", "2:47 PM", msgs=[("me", "try this amazon workflow when u get a sec 👉 sellercentral.amazon.com/myworkflows/…", "wl", "2:47 PM"),
      ("them", "ooh ok!", "", "2:48 PM")])
    s("gm_sel", "gmail", "2:50 PM", sel={1, 3, 4, 6, 8, 9})
    s("gm_arch", "gmail", "2:50 PM", archived=6, snack="6 conversations archived.")
    s("gm_unread", "gmail", "2:52 PM", archived=6, unread=1, sel={2}, snack="Conversation marked as unread.")
    s("spapi", "spapi", "2:55 PM")
    s("health", "health", "3:01 PM", v=770)
    # done
    s("bowl", "lunch", "3:09 PM")
    s("cake", "lunch", "3:12 PM", cake=1)
    s("startup_end", "startup_scripts", "3:18 PM", dropped=1)
    s("tomorrow", "notepad", "3:20 PM", tabs=["tomorrow.txt"], box=(120, 120, 1040, 820), text=["TOMORROW", "", "☐ unpause the printer + reprint P-049 and P-088",
      "☐ answer the 4 Amazon messages (for real)", "☐ ship the late one", "☐ reply to the email I marked unread twice", "☐ clean up assistant stuff + the public web link",
      "☐ Amazon workflow: name match + schedule", "☐ talk to the team about timing"])
    return [(k, n, st) for k, (n, st) in J.items()]


# ------------------------------------------------------------------ shots (one per line)
def sh(scr, clock=None, cam=None, cur=None, clicks=None, keys=None, sfx=None, face=None, fx=None):
    return dict(scr=scr, clock=clock, cam=cam or [(0, "full")], cur=cur or [], clicks=clicks or [], keys=keys or [], sfx=sfx or [], face=face, fx=fx)


Z = lambda x, y, z: (x, y, z)  # noqa: E731

SHOTS = [
    # 0 hook
    sh("printq", "3:02", cam=[(0, Z(640, 545, 1.15)), ("paused", Z(500, 395, 2.3))], sfx=[(0.02, "error")], face="annoyed"),
    sh("printq_hl", "3:02", cam=[(0, Z(450, 395, 2.6)), ("three", Z(640, 545, 1.3))], face="eye_roll"),
    sh("printq", "3:02", fx="title", face="excited"),
    sh("printq", ("8:00", "3:20"), fx="montage", face="smug"),
    # 1 sync
    sh("sales_toast", "8:00", cam=[(0, Z(1100, 1270, 2.2)), ("drops", Z(400, 420, 1.6))], sfx=[(0.05, "notif")]),
    sh("sales_new", "8:00", cam=[(0, Z(420, 430, 1.9))], cur=[(0, (900, 700)), (0.4, (400, 420))]),
    sh("sales_new", "8:00", cam=[(0, Z(640, 600, 1.2))], face="smug"),
    # 2 check-in
    sh("teams_vid", "8:15", cam=[(0, "full"), ("Teams", Z(700, 700, 1.4))], sfx=[(0.1, "notif")]),
    sh([(0, "teams_vid"), ("watching", "player1")], "8:16", cam=[(0, Z(830, 860, 1.8)), ("watching", Z(640, 560, 1.15))], cur=[(0, (900, 1000)), (0.2, "clip")], clicks=[0.3]),
    sh("msgs0", "8:19", cam=[(0, Z(420, 340, 1.8))], cur=[(0, (700, 600)), (0.3, "needs")], clicks=[0.45]),
    sh("msgs_open", "8:19", cam=[(0, Z(420, 560, 1.7)), ("question", Z(420, 640, 2.1)), ("two", Z(420, 760, 1.9))], cur=[(0, "msg0")], clicks=[0.05]),
    sh("msgs_read", "8:20", cam=[(0, Z(820, 560, 1.7)), ("not", Z(820, 620, 2.4))], face="smug"),
    sh("listing", "8:20", cam=[(0, Z(640, 600, 1.2)), ("looking", Z(450, 560, 1.7))], cur=[(0, (800, 400)), (0.5, "photo")]),
    # 3 MT Log
    sh("prog_sel", "8:21", cam=[(0, Z(640, 440, 1.5))], fx="mtlogpop", face="excited", sfx=[(0.1, "whoosh")]),
    sh("cl_links", "8:21", cam=[(0, Z(640, 520, 1.6))], face="neutral"),
    sh([(0, "prog_sel"), ("uninstalled", "prog_confirm"), ("installed", "prog_setup40")], "8:25",
       cam=[(0, Z(520, 520, 1.8)), ("uninstalled", Z(640, 470, 2.0)), ("installed", Z(640, 860, 1.8))], cur=[(0, "prog_mt"), ("uninstalled", "yes")], clicks=["uninstalled"]),
    sh([(0, "startup_drag"), ("drop", "startup_drop")], "8:33", cam=[(0, Z(640, 600, 1.15)), ("drop", Z(500, 380, 1.9))], cur=[(0, (400, 830)), ("drop", (600, 360))],
       clicks=["drop"], sfx=[("logs", "ding")]),
    sh("startup_drop", "8:33", cam=[(0, Z(420, 360, 2.4))], face="smug"),
    sh("fallbreak", "8:36", cam=[(0, Z(830, 1000, 1.9))], keys=[(0, 0.3)], sfx=[(0.32, "send")]),
    sh("fallbreak", "8:36", cam=[(0, Z(830, 1000, 2.4))], face="eye_roll"),
    # 4 assistant
    sh("as0", "8:44", cam=[(0, Z(1000, 260, 1.9))], sfx=[(0.05, "open")]),
    sh("as0", "8:46", cam=[(0, Z(900, 400, 1.3))], fx="counter"),
    sh([(0, "as1"), ("second", "as3"), ("pile", "as5"), (0.85, "as7")], "8:51", cam=[(0, Z(1020, 360, 1.7)), ("pile", Z(1020, 560, 1.4))],
       sfx=[("second", "notif"), ("pile", "notif"), (0.8, "notif"), (0.88, "notif")], face="surprised"),
    sh("as7", "8:51", cam=[(0, Z(1020, 560, 1.4)), ("How?", Z(1020, 560, 1.9))], face="surprised"),
    sh("as_hl", "8:53", cam=[(0, Z(1030, 310, 2.4))], face="smug"),
    sh("as_hl", "8:53", cam=[(0, Z(1030, 310, 3.0)), ("Thank", Z(1020, 500, 1.5))], face="eye_roll"),
    sh([(0, "typo25"), (0.3, "typo50"), (0.55, "typo75"), (0.75, "typo100")], "8:51", cam=[(0, Z(640, 1150, 2.0))], keys=[(0, 0.85)], face="smug"),
    sh("typo_sent", "8:51", cam=[(0, Z(830, 400, 2.2))], sfx=[(0.02, "send")], face="smug"),
    # 5 setup
    sh("keys0", "8:54", cam=[(0, Z(640, 400, 1.5))], face="annoyed"),
    sh([(0, "keys0"), ("Okay", "keys1"), ("save", "env_new"), (0.85, "env_k1")], "8:55", cam=[(0, Z(1050, 230, 2.2)), ("Okay", Z(640, 330, 1.7)), ("save", Z(640, 650, 1.7))],
       cur=[(0, "create"), ("save", "ok")], clicks=[0.12, 0.8], keys=[("save", 0.75)], face="annoyed"),
    sh("model", "9:00", cam=[(0, Z(1100, 1240, 2.4))], face="surprised"),
    sh([(0, "as_proj"), ("deploying", "as_new"), ("copying", "as_done"), ("saving", "env_k2")], "9:12",
       cam=[(0, Z(400, 190, 2.0)), ("deploying", Z(640, 560, 1.4)), ("copying", Z(640, 600, 1.8)), ("saving", Z(560, 380, 1.9))],
       cur=[(0, "pname"), ("deploying", "dodeploy"), ("copying", "copy")], clicks=["deploying", "copying"], face="annoyed"),
    sh("as_plus", "9:11", cam=[(0, Z(420, 260, 2.0)), ("plus", Z(250, 250, 2.6)), ("Named", Z(400, 190, 2.4))], cur=[(0, (600, 500)), ("plus", "plus")], clicks=["plus"]),
    sh([(0, "env_q50"), (0.4, "env_q100"), ("yes", "env_a")], "9:14", cam=[(0, Z(640, 1150, 2.0)), ("yes", Z(640, 420, 1.7))], keys=[(0, 0.42)]),
    sh([(0, "ps1"), ("Cloud", "gcloud")], "9:18", cam=[(0, Z(500, 330, 1.9)), ("Cloud", Z(640, 300, 1.6))], keys=[(0, 0.4)], face="annoyed"),
    sh("ps2", "9:19", cam=[(0, Z(600, 400, 1.8)), ("Google", Z(600, 480, 2.1))], sfx=[(0.1, "error")], face="annoyed"),
    sh([(0, "why"), ("file", "saveas_cmd")], "9:22", cam=[(0, Z(640, 380, 1.8)), ("file", Z(640, 620, 1.6))], cur=[("file", "save")], clicks=[0.9], face="smug"),
    sh("countdown", "9:09", cam=[(0, Z(1100, 1260, 2.8))], face="happy"),
    sh([(0, "mem"), ("learned", "learned"), ("recommendations", "recs")], "9:27", cam=[(0, Z(500, 330, 1.9))]),
    sh("recs", ("9:30", "9:31"), cam=[(0, Z(640, 600, 1.0))], fx="clockpunch", face="annoyed"),
    # 6 review
    sh([(0, "rev_player1"), (0.7, "rev_player2")], ("9:44", "10:40"), cam=[(0, Z(640, 560, 1.15))], fx="timelapse"),
    sh("proofs", "10:41", cam=[(0, Z(500, 330, 1.8))], cur=[(0, "f0")], clicks=[0.1]),
    sh("results", "10:44", cam=[(0, Z(560, 300, 2.0))]),
    sh([(0, "proofs_copy"), ("date", "proofs_ren")], "11:06", cam=[(0, Z(450, 350, 2.2))], cur=[(0, "f2")], clicks=[0.15], keys=[("date", 0.8)], face="excited"),
    sh("reload_q", "11:20", cam=[(0, Z(830, 1000, 1.9))], keys=[(0, 0.4)], sfx=[(0.42, "send")]),
    sh("waiting", "11:21", cam=[(0, Z(420, 560, 1.8))], face="annoyed"),
    # 7 shopify
    sh("shopify", "11:30", cam=[(0, Z(640, 400, 1.6))], cur=[(0, "unf")], clicks=[0.3], face="excited"),
    sh("cost", "11:36", cam=[(0, Z(500, 300, 2.4)), ("Three", Z(450, 300, 3.0))], face="happy"),
    sh("track1", "11:40", cam=[(0, Z(500, 300, 2.0))]),
    sh("track2", "11:41", cam=[(0, Z(500, 330, 2.2))]),
    sh("cs_save", "11:47", cam=[(0, Z(500, 330, 1.8)), ("saved", Z(640, 620, 1.7))], cur=[("saved", "save")], clicks=[0.5], face="excited"),
    sh("bee", "11:49", cam=[(0, Z(640, 500, 1.9))], sfx=[(0.05, "bee")]),
    # 8 quit
    sh([(0, "quit50"), (0.5, "quit100")], "11:57", cam=[(0, Z(640, 1150, 2.0))], keys=[(0.1, 0.9)]),
    sh("quit_a", "11:57", cam=[(0, Z(640, 400, 1.8))], sfx=[(0.02, "send")]),
    sh("as7", "11:58", cam=[(0, Z(1020, 560, 1.4))], face="eye_roll"),
    sh([(0, "rein40"), ("logging", "rein100")], "11:59", cam=[(0, Z(640, 860, 1.8))], sfx=[("logging", "ding")]),
    sh("rein100", ("8:40", "12:00"), fx="montage2", face="smug"),
    # 9 pop-ups
    sh("cust0", "12:08", cam=[(0, Z(640, 600, 1.2))]),
    sh([(0, "cust0"), ("typing", "cust1"), ("sizes", "cust2")], "12:11", cam=[(0, Z(400, 500, 1.8)), ("moving", Z(400, 660, 2.2))],
       cur=[(0, "label"), ("moving", "in_X"), ("sizes", "in_Height")], clicks=[0.1, "moving", "sizes"], keys=[("typing", "moving")]),
    sh("pop1", "12:12", cam=[(0, Z(640, 600, 1.2))]),
    sh("cust1", "12:11", cam=[(0, Z(300, 400, 2.6))], face="smug"),
    sh("pop2", "12:30", cam=[(0, Z(930, 700, 1.9)), ("never", Z(500, 560, 2.0))], keys=[(0, 0.3)], face="smug"),
    sh("pop2", "12:30", cam=[(0, Z(500, 560, 2.2))], face="eye_roll"),
    sh("cust1", "12:31", cam=[(0, Z(870, 560, 2.2))], face="smug"),
    # 10 win
    sh("wf0", "12:18", cam=[(0, Z(640, 560, 1.15))], face="excited", sfx=[(0.05, "whoosh")]),
    sh([(0, "wf_typing"), (0.8, "wf_prev")], "12:19", cam=[(0, Z(320, 900, 2.0))], keys=[(0.2, 0.75)]),
    sh("wf_prev", "12:21", cam=[(0, Z(840, 420, 1.8))], face="eye_roll"),
    sh("wf_q", "1:13", cam=[(0, Z(330, 720, 1.9))]),
    sh("wf_not", "1:22", cam=[(0, Z(330, 900, 2.2))], keys=[(0, 0.3)], face="smug"),
    sh([(0, "wf_name"), ("on", "wf_on")], "1:30", cam=[(0, Z(830, 400, 2.0))], cur=[(0, "wfname"), ("on.", "toggle"), ("Run", "runnow")], clicks=["on.", "Run"],
       keys=[("name", "hit")], face="excited"),
    sh([(0, "wf_ran"), ("spreadsheet", "csv")], "1:32", cam=[(0, Z(830, 560, 2.0)), ("spreadsheet", Z(640, 500, 1.3)), ("customizations", Z(800, 450, 1.8))],
       sfx=[(0.02, "success"), ("spreadsheet", "whoosh")], face="excited"),
    sh("csv", "1:33", cam=[(0, Z(640, 500, 1.4))], fx="confetti", face="happy", sfx=[(0.05, "tada")]),
    sh([(0, "zip"), ("raw", "zip_xml")], "1:34", cam=[(0, Z(500, 300, 2.0)), ("raw", Z(560, 760, 1.7))], cur=[(0, "f0")], clicks=[0.15]),
    sh("csv_match", "1:40", cam=[(0, Z(900, 450, 1.8)), ("eighty", Z(1150, 450, 2.4))]),
    sh("csv_match", "1:40", cam=[(0, Z(900, 440, 2.0)), ("different", Z(1050, 470, 2.6))], face="neutral"),
    sh("csv_match", "1:41", cam=[(0, Z(640, 600, 1.1))], face="smug"),
    # 11 printer
    sh("rules", "12:34", cam=[(0, Z(640, 500, 1.6))]),
    sh("blank", "12:35", cam=[(0, Z(640, 500, 1.3)), ("still", Z(640, 600, 1.9))], face="eye_roll"),
    sh("p49", "12:41", cam=[(0, Z(640, 560, 1.2)), ("staff", Z(900, 520, 1.8))], cur=[(0, "printbtn")], clicks=[0.85], sfx=[(0.88, "print")]),
    sh([(0, "p88"), ("eighteen", "p88_print")], "12:52", cam=[(0, Z(640, 420, 1.7)), ("eighteen", Z(640, 560, 1.2))], cur=[("eighteen", "printbtn")], clicks=[0.9],
       sfx=[(0.92, "print")]),
    sh("printq2", "12:53", cam=[(0, Z(450, 395, 2.6))], sfx=[("paused", "error")], face="eye_roll"),
    # 12 orders
    sh("mailmsg", "1:01", cam=[(0, Z(500, 330, 1.9))], face="annoyed"),
    sh("mailmsg", "1:01", cam=[(0, Z(500, 340, 2.3)), ("No.", Z(640, 600, 1.3))], face="annoyed"),
    sh("schome", "1:18", cam=[(0, Z(640, 260, 1.5)), ("pending", Z(170, 260, 2.6)), ("seventy", Z(410, 260, 2.6)), ("late", Z(650, 260, 2.6))]),
    sh("custmsg", "1:20", cam=[(0, Z(830, 1000, 1.9))], keys=[(0, 0.5)], sfx=[(0.52, "send")]),
    sh("custmsg", "1:20", cam=[(0, Z(830, 990, 2.3))]),
    sh([(0, "indd"), ("eight", "indd8")], ("1:24", "1:32"), cam=[(0, Z(450, 120, 2.6)), ("eight", Z(1050, 140, 2.6)), ("dangerously", Z(640, 600, 1.0))], face="smug"),
    # 13 timing
    sh("timing", "2:13", cam=[(0, Z(640, 600, 1.4))]),
    sh("timing", "2:14", cam=[(0, Z(640, 700, 1.9))], face="surprised"),
    sh("timing", "2:15", cam=[(0, Z(640, 900, 1.6))], face="sad"),
    sh("sorry", "2:20", cam=[(0, Z(830, 1000, 2.0))], keys=[(0, 0.4)], sfx=[(0.42, "send")], face="sad"),
    # 14 wrap
    sh("ord0", "2:43", cam=[(0, Z(640, 450, 1.2))], sfx=[(0.05, "whoosh")]),
    sh([(0, "ord0"), ("Do", "ord1")], "2:44", cam=[(0, Z(400, 330, 1.6)), ("Do", Z(400, 520, 2.0))], cur=[(0, "note")], clicks=[0.2], keys=[(0.25, "Do")]),
    sh("ord1", "2:44", cam=[(0, Z(400, 520, 2.6))], face="sad"),
    sh("wflink", "2:47", cam=[(0, Z(830, 960, 2.0))], sfx=[(0.05, "send")]),
    sh([(0, "gm_sel"), ("Six.", "gm_arch"), ("unread", "gm_unread")], "2:50", cam=[(0, Z(640, 450, 1.4)), ("unread", Z(500, 300, 2.0))],
       cur=[(0, "archive"), ("unread", "markunread")], clicks=["archived", "unread", "Twice"], face="smug"),
    sh("spapi", "2:55", cam=[(0, Z(640, 400, 1.5))], cur=[(0, "saveapp"), ("support", "case")], clicks=["saving"]),
    sh("health", "3:01", cam=[(0, Z(300, 420, 2.0))], face="happy", sfx=[(0.3, "success")]),
    # 15 done
    sh("bowl", "3:09", cam=[(0, Z(640, 500, 1.4))], face="happy"),
    sh("cake", "3:12", cam=[(0, Z(640, 500, 1.4)), ("growth", Z(880, 560, 2.0))], face="smug"),
    sh("startup_end", ("3:18", "3:20"), cam=[(0, Z(420, 360, 2.0)), ("logged", Z(640, 600, 1.0))], fx="logoff"),
    # 16 stats + tomorrow + bye
    sh("startup_end", "3:20", fx="stats", face="excited"),
    sh("startup_end", "3:20", fx="stats", face="neutral"),
    sh("startup_end", "3:20", fx="stats", face="happy"),
    sh("tomorrow", "3:20", cam=[(0, Z(500, 330, 1.9))], keys=[(0, 0.9)]),
    sh("tomorrow", "3:20", cam=[(0, Z(500, 420, 1.9))]),
    sh("tomorrow", "3:20", cam=[(0, Z(500, 500, 1.9))]),
    sh("tomorrow", "3:20", fx="end", face="smug"),
    sh("tomorrow", "3:20", fx="end", face="happy"),
]


# ------------------------------------------------------------------ camera, by named parts of each screen
# ("box", zoom) centers on that box; ("box", zoom, fy) puts the view at height fy (0 top .. 1 bottom) of the box.
CAMS = {
    0: [(0, ("queue", 1.3, 0.2)), ("paused", ("queue_title", 2.6))],
    1: [(0, ("queue_title", 2.8)), ("three", ("queue", 1.5, 0.1))],
    4: [(0, ("toast", 2.2)), ("drops", ("grid", 1.7, 0.12, 0.3))],
    5: [(0, ("grid", 2.0, 0.12, 0.3))],
    6: [(0, ("grid", 1.3, 0.2, 0.4))],
    7: [(0, ("msgs", 1.2, 1)), ("Teams", ("clip", 2.0))],
    8: [(0, ("clip", 2.0)), ("watching", ("player", 1.2))],
    9: [(0, ("needs", 2.2))],
    10: [(0, ("list", 1.8, 0.1)), ("question", ("msg1", 2.4)), ("two", ("msg2", 2.0, 0.9))],
    11: [(0, ("thread", 1.6, 0.25)), ("not", ("reply", 2.2))],
    12: [(0, "full"), ("looking", ("photo", 1.8))],
    13: [(0, ("prog_mt", 1.6))],
    14: [(0, ("conv", 1.45))],
    15: [(0, ("prog_mt", 2.0)), ("uninstalled", ("yes", 2.0)), ("installed", ("setup", 1.8))],
    16: [(0, "full"), ("drop", ("f0", 2.0))],
    17: [(0, ("f0", 2.6))],
    18: [(0, ("fb", 2.0))],
    19: [(0, ("fb", 2.6))],
    20: [(0, ("panel", 1.8))],
    21: [(0, ("panel", 1.3))],
    22: [(0, ("panel", 1.6, 0.1)), ("pile", ("panel", 1.35))],
    23: [(0, ("panel", 1.35)), ("How?", ("panel", 1.8, 0.3))],
    24: [(0, ("short", 1.8))],
    25: [(0, ("short", 2.2)), ("Thank", ("panel", 1.4))],
    26: [(0, ("prompt", 2.0))],
    27: [(0, ("typo", 2.4))],
    28: [(0, ("create", 1.6))],
    29: [(0, ("create", 2.2)), ("Okay", ("create", 1.5)), ("save", ("vname", 2.0))],
    30: [(0, ("tip", 1.7, 0.2))],
    31: [(0, ("pname", 2.2)), ("deploying", ("dodeploy", 1.4)), ("copying", ("url", 2.0)), ("saving", ("uservars", 1.8))],
    32: [(0, ("pname", 2.0)), ("plus", ("plus", 2.6)), ("Named", ("pname", 2.6))],
    33: [(0, ("prompt", 2.0)), ("yes", ("last", 1.8))],
    34: [(0, ("out", 2.0, 0)), ("Cloud", ("proj", 2.0))],
    35: [(0, ("out", 1.8, 0)), ("Google", ("out", 2.4, 0.8))],
    36: [(0, ("last", 1.8)), ("file", ("fname", 1.8))],
    37: [(0, ("tip", 2.2, 0.2))],
    38: [(0, ("text", 2.0, 0.1, 0.3))],
    39: [(0, "full")],
    40: [(0, ("player", 1.2))],
    41: [(0, ("f0", 2.0))],
    42: [(0, ("text", 1.8, 0.1, 0.35))],
    43: [(0, ("f2", 2.4))],
    44: [(0, ("rq", 2.0))],
    45: [(0, ("list", 1.8, 0.1))],
    46: [(0, ("orders", 1.6, 0.2)), ("unfulfilled", ("unf", 2.4))],
    47: [(0, ("cost", 2.4)), ("Three", ("cost", 3.2))],
    48: [(0, ("grid", 1.8, 0.1, 0.35))],
    49: [(0, ("grid", 2.1, 0.12, 0.35))],
    50: [(0, ("text", 1.8, 0.1, 0.3)), ("saved", ("fname", 2.0))],
    51: [(0, ("beein", 1.6, 0)), ("okay", ("beein", 2.2, -1.5))],
    52: [(0, ("prompt", 2.0))],
    53: [(0, ("last", 1.8))],
    54: [(0, ("panel", 1.35))],
    55: [(0, ("setup", 1.8))],
    57: [(0, "full")],
    58: [(0, ("label", 2.2)), ("moving", ("in_X", 2.4)), ("sizes", ("in_Height", 2.4))],
    59: [(0, "full")],
    60: [(0, ("label", 3.0))],
    61: [(0, ("pf3", 2.0)), ("never", ("pf3", 3.0))],
    62: [(0, ("pf3", 2.6))],
    63: [(0, ("box", 2.4))],
    64: [(0, "full")],
    65: [(0, ("wfin", 2.2))],
    66: [(0, ("right", 1.8, 0.2))],
    67: [(0, ("chat", 1.8, 0.75))],
    68: [(0, ("wfin", 2.4))],
    69: [(0, ("wfname", 2.2)), ("on.", ("toggle", 2.6)), ("Run", ("runnow", 2.4))],
    70: [(0, ("ran", 2.4)), ("spreadsheet", ("grid", 1.3, 0.2, 0.4)), ("customizations", ("grid", 1.9, 0.15, 0.6))],
    71: [(0, ("grid", 1.4, 0.2, 0.45))],
    72: [(0, ("f0", 2.0)), ("raw", ("text", 1.0))],
    73: [(0, ("grid", 1.4, 0.2, 0.6)), ("eighty", ("grid", 2.0, 0.15, 0.85))],
    74: [(0, ("grid", 2.0, 0.15, 0.7)), ("different", ("grid", 2.4, 0.15, 0.75))],
    75: [(0, ("grid", 1.2, 0.2, 0.5))],
    76: [(0, "full")],
    77: [(0, ("paper", 1.4, 0.1)), ("still", ("paper", 1.9, 0.2))],
    78: [(0, "full"), ("staff", ("printbtn", 1.6))],
    79: [(0, ("paper", 1.8, 0.05)), ("eighteen", ("printbtn", 1.3))],
    80: [(0, ("queue_title", 2.8))],
    81: [(0, ("msg", 2.0))],
    82: [(0, ("msg", 2.4)), ("No.", ("msg", 1.4))],
    83: [(0, ("tile1", 1.4)), ("pending", ("tile0", 2.6)), ("seventy", ("tile1", 2.6)), ("late", ("tile2", 2.6))],
    84: [(0, ("cm", 2.0))],
    85: [(0, ("cm", 2.4))],
    86: [(0, ("doctab", 2.6)), ("eight", ("timer", 2.6)), ("dangerously", "full")],
    87: [(0, ("conv", 1.4))],
    88: [(0, ("chart", 1.8))],
    89: [(0, ("last", 1.5, 0.8))],
    90: [(0, ("sorry", 2.2))],
    91: [(0, "full")],
    92: [(0, ("note", 1.8, 0.5, 0.3)), ("Do", ("note", 2.4, 0.5, 0.25))],
    93: [(0, ("note", 2.8, 0.5, 0.22))],
    94: [(0, ("wl", 2.2))],
    95: [(0, ("inbox", 1.5, 0.1)), ("unread", ("markunread", 2.4))],
    96: [(0, ("saveapp", 1.5)), ("support", ("case", 1.8))],
    97: [(0, ("ring", 1.8))],
    98: [(0, "full")],
    99: [(0, "full"), ("growth", "full")],
    100: [(0, ("f0", 2.4)), ("logged", "full")],
    104: [(0, ("text", 1.9, 0.1, 0.35))],
    105: [(0, ("text", 1.9, 0.25, 0.35))],
    106: [(0, ("text", 1.9, 0.35, 0.35))],
}
for _i, _c in CAMS.items():
    SHOTS[_i]["cam"] = _c
