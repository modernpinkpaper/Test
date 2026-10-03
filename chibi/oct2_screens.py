"""App screens for the long Oct 2 vlog, rebuilt as HTML/CSS and rendered to PNG with Playwright.

    python chibi/oct2_screens.py OUT_DIR [name ...]

Every screen is a 1280 x 1422 CSS-pixel "tall monitor" (Windows 11 desktop, taskbar with the log's clock) rendered at
2.5x, so the video can punch in to ~2.4x and stay sharp. Elements marked data-t="..." have their boxes saved next to
the PNG (name.json) so the video can move the mouse to them and click.

Everything on screen is a fake example: names, order numbers, amounts, keys, links. Layouts follow the real apps.
"""
import html
import json
import os
import sys

VW, VH, DPR = 1280, 1422, 2.5
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.environ.get("OCT2_FONTS", "")
E = html.escape

# ------------------------------------------------------------------ base css
def font_css():
    out = []
    for fam, pkg, ws in (("Segoe UI", "open-sans", (400, 600, 700)), ("Roboto", "roboto", (400, 500, 700)),
                         ("Inter", "inter", (400, 500, 600, 700, 800)), ("Serif4", "source-serif-4", (400, 600)),
                         ("Mono", "cascadia-code", (400, 600)), ("Noto", "noto-sans", (400, 500, 700))):
        for w in ws:
            p = os.path.join(FONTS, pkg, "package", "files", f"{pkg}-latin-{w}-normal.woff2")
            out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('file://{p}') format('woff2')}}")
    return "\n".join(out)


BASE = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1280px;height:1422px;overflow:hidden}
body{font-family:'Segoe UI',sans-serif;font-size:13px;color:#1b1b1b;position:relative;
 background:radial-gradient(ellipse at 30% 35%,#a9c8f5 0,#5b8fdc 35%,#2a4f9e 70%,#16285a 100%)}
.wall:after{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 70% 60%,rgba(140,200,255,.55),transparent 55%)}
.taskbar{position:absolute;left:0;right:0;bottom:0;height:48px;background:rgba(243,243,243,.93);border-top:1px solid #d6d6d6;
 display:flex;align-items:center;justify-content:center;gap:6px;z-index:50;backdrop-filter:blur(20px)}
.tb{width:40px;height:40px;border-radius:5px;display:flex;align-items:center;justify-content:center}
.tb.on{background:rgba(255,255,255,.75)}
.tb.on:after{content:"";position:absolute;bottom:3px;width:16px;height:3px;border-radius:2px;background:#0067c0}
.tb{position:relative}
.ico{width:24px;height:24px;border-radius:5px;display:flex;align-items:center;justify-content:center;color:#fff;font:700 11px Inter}
.tray{position:absolute;right:12px;top:0;height:48px;display:flex;align-items:center;gap:14px;font-size:12px;color:#1b1b1b}
.tray .clk{text-align:right;line-height:16px}
.search{width:200px;height:32px;border-radius:16px;background:#fff;border:1px solid #e0e0e0;display:flex;align-items:center;
 padding-left:12px;color:#666;font-size:13px;margin:0 6px}
/* windows 11 window */
.w{position:absolute;background:#fff;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.28),0 0 0 1px rgba(0,0,0,.12);overflow:hidden;
 display:flex;flex-direction:column}
.wt{height:32px;display:flex;align-items:center;padding-left:12px;font-size:12px;background:#f3f3f3;flex:none;gap:8px}
.wt .ctl{margin-left:auto;display:flex;height:32px}
.wt .ctl span{width:46px;display:flex;align-items:center;justify-content:center;font:400 13px 'Segoe UI';color:#333}
.wb{flex:1;position:relative;overflow:hidden}
.btn{display:inline-flex;align-items:center;justify-content:center;height:32px;padding:0 18px;border-radius:4px;border:1px solid #d1d1d1;
 background:#fdfdfd;font-size:13px;min-width:80px}
.btn.pri{background:#005fb8;border-color:#005fb8;color:#fff}
/* chrome */
.ch{position:absolute;inset:0 0 48px 0;display:flex;flex-direction:column;background:#fff}
.tabs{height:40px;background:#dfe3e8;display:flex;align-items:flex-end;padding-left:8px;gap:0;flex:none;position:relative}
.tab{height:34px;width:230px;padding:0 12px;display:flex;align-items:center;gap:8px;font:400 12px Roboto;color:#3c4043;position:relative}
.tab.on{background:#fff;border-radius:10px 10px 0 0}
.tab .fav{width:16px;height:16px;border-radius:3px;flex:none;display:flex;align-items:center;justify-content:center;font:700 9px Inter;color:#fff}
.tab .tt{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}
.tab .x{font-size:12px;color:#5f6368}
.tab:not(.on)+.tab:not(.on):before{content:"";position:absolute;left:0;top:9px;bottom:9px;width:1px;background:#a8acb1}
.tabs .wc{position:absolute;right:0;top:0;display:flex;height:34px}
.tabs .wc span{width:46px;display:flex;align-items:center;justify-content:center;color:#333}
.omni{height:44px;display:flex;align-items:center;gap:6px;padding:0 10px;border-bottom:1px solid #dadce0;flex:none;background:#fff}
.omni .nb{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#5f6368;font-size:17px}
.url{flex:1;height:34px;border-radius:17px;background:#e9eef6;display:flex;align-items:center;padding:0 14px;font:400 14px Roboto;color:#1f1f1f;gap:10px}
.url .dom{color:#1f1f1f}.url .rest{color:#5f6368}
.bm{height:28px;display:flex;align-items:center;gap:16px;padding:0 14px;font:400 12px Roboto;color:#3c4043;border-bottom:1px solid #e8eaed;flex:none}
.page{flex:1;position:relative;overflow:hidden}
.toast{position:absolute;right:14px;bottom:62px;width:364px;background:#f9f9f9;border-radius:8px;box-shadow:0 8px 28px rgba(0,0,0,.3);
 padding:14px 16px;z-index:60;border:1px solid #e3e3e3}
.toast .ap{font-size:12px;color:#444;display:flex;gap:8px;align-items:center;margin-bottom:8px}
.toast b{display:block;font-size:14px;margin-bottom:3px}
.hl{outline:4px solid #ff3b7f;outline-offset:3px;border-radius:6px}
"""

ICONS = {   # taskbar / favicon squares: (bg, label)
    "start": ("#0067c0", "⊞"), "chrome": ("conic-gradient(#ea4335 0 33%,#fbbc05 0 66%,#34a853 0)", ""),
    "explorer": ("#f8c43a", ""), "teams": ("#5b5fc7", "T"), "claude": ("#d97757", "✳"), "id": ("#49021f", "Id"),
    "notepad": ("#3d8bd9", "≡"), "term": ("#2b2b2b", ">_"), "bee": ("#f2b632", "B"), "mtlog": ("#e8547f", "M"),
    "excel": ("#107c41", "X"), "settings": ("#6b6b6b", "⚙"),
}


def ico(k, size=24):
    bg, lab = ICONS[k]
    style = f"width:{size}px;height:{size}px;background:{bg}"
    if k == "chrome":
        style += ";border-radius:50%;box-shadow:inset 0 0 0 5px rgba(0,0,0,0)"
        return f'<div class="ico" style="{style}"><div style="width:42%;height:42%;border-radius:50%;background:#4285f4;border:2px solid #fff"></div></div>'
    return f'<div class="ico" style="{style}">{lab}</div>'


def taskbar(clock, on=("chrome",), date="10/2/2026"):
    items = ["start", "chrome", "explorer", "teams", "claude", "id", "notepad", "bee", "mtlog"]
    tbs = "".join(f'<div class="tb{" on" if k in on else ""}">{ico(k)}</div>' + ('<div class="search">🔍&nbsp; Search</div>' if k == "start" else "")
                  for k in items)
    return (f'<div class="taskbar">{tbs}<div class="tray"><span>^</span><span>📶</span><span>🔊</span>'
            f'<div class="clk">{clock}<br>{date}</div></div></div>')


def window(title, body, x, y, w, h, icon=None, extra="", tid=""):
    ic = ico(icon, 16) if icon else ""
    t = f' data-t="{tid}"' if tid else ""
    return (f'<div class="w" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"{t}>'
            f'<div class="wt">{ic}<span>{E(title)}</span>{extra}<div class="ctl"><span>—</span><span>☐</span><span>✕</span></div></div>'
            f'<div class="wb">{body}</div></div>')


def chrome(tabs, active, url, body, bookmarks=True):
    ts = ""
    for i, (fav, title) in enumerate(tabs):
        bg, lab = fav if isinstance(fav, tuple) else ICONS[fav]
        ts += (f'<div class="tab{" on" if i == active else ""}"><div class="fav" style="background:{bg}">{lab}</div>'
               f'<div class="tt">{E(title)}</div><div class="x">✕</div></div>')
    dom, _, rest = url.partition("/")
    bms = ('<div class="bm"><span>📁 Orders</span><span>📁 Amazon</span><span>📁 Shopify</span><span>📁 Etsy</span>'
           '<span>📁 Team</span><span>📁 Tools</span></div>') if bookmarks else ""
    return (f'<div class="ch"><div class="tabs">{ts}<div style="padding:0 0 8px 8px;font-size:18px;color:#444">+</div>'
            f'<div class="wc"><span>—</span><span>☐</span><span>✕</span></div></div>'
            f'<div class="omni"><div class="nb">←</div><div class="nb">→</div><div class="nb">⟳</div>'
            f'<div class="url"><span style="color:#5f6368">⚲</span><span><span class="dom">{E(dom)}</span><span class="rest">/{E(rest)}</span></span>'
            f'<span style="margin-left:auto;color:#5f6368">☆</span></div><div class="nb">⋮</div></div>{bms}'
            f'<div class="page">{body}</div></div>')


def toast(app, title, body, icon="chrome"):
    return (f'<div class="toast" data-t="toast"><div class="ap">{ico(icon, 16)}{E(app)}<span style="margin-left:auto">✕</span></div>'
            f'<b>{E(title)}</b><div style="color:#444">{E(body)}</div></div>')


def desk(clock, inner, on=("chrome",), extra_css=""):
    return f'<style>{extra_css}</style><div class="wall"></div>{inner}{taskbar(clock, on)}'


# ------------------------------------------------------------------ Amazon Seller Central
SC_CSS = """
.sc{font-family:Noto,Arial,sans-serif;color:#0f1111;height:100%;background:#fff;display:flex;flex-direction:column}
.scn{height:48px;background:#002f36;display:flex;align-items:center;gap:16px;padding:0 16px;color:#fff;flex:none}
.scn .logo{font:700 15px Inter;letter-spacing:.2px}.scn .logo i{font-style:normal;color:#ff9900}
.scn .srch{flex:1;max-width:420px;height:32px;background:#1e4e57;border-radius:4px 0 0 4px;display:flex;align-items:center;padding:0 12px;color:#9fb5b9;font-size:13px;font-style:italic;margin-left:auto}
.scn .sb{width:38px;height:32px;background:#2f7f8c;border-radius:0 4px 4px 0;display:flex;align-items:center;justify-content:center}
.scn .mk{background:#fff;color:#0f1111;border-radius:4px;padding:6px 10px;font-size:13px}
.scn .r{margin-left:auto;display:flex;gap:18px;font-size:13px;align-items:center}
.scs{height:40px;display:flex;align-items:center;gap:22px;padding:0 14px;font-size:13px;color:#fff;flex:none;background:#002f36;border-top:1px solid #1d4a52}
.scs .ed{margin-left:auto;border:1px solid #6f8b90;border-radius:4px;padding:4px 10px}
.scb{flex:1;padding:22px 30px;background:#fff;overflow:hidden}
.tabsr{display:flex;gap:36px;font-size:18px;color:#565959;border-bottom:1px solid #d5d9d9;margin-bottom:16px}
.tabsr span{padding-bottom:8px}.tabsr span.on{color:#0f1111;font-weight:700;box-shadow:inset 0 -3px #e77600}
.gb{display:inline-flex;align-items:center;height:29px;padding:0 12px;border-radius:8px;background:#f0f2f2;border:1px solid #d5d9d9;font-size:13px}
.card{background:#fff;border:1px solid #d5d9d9;border-radius:8px;padding:16px 18px}
.h1{font:400 28px Noto;margin-bottom:14px}
.lnk{color:#007185}
.ab{display:inline-flex;align-items:center;height:32px;padding:0 14px;border-radius:100px;font:500 13px Inter;border:1px solid #888c8c;background:#fff}
.ab.y{background:#ffd814;border-color:#fcd200}.ab.o{background:#ff9900;border-color:#ff9900;color:#0f1111}
.ab.b{background:#008296;border-color:#008296;color:#fff}
table.t{width:100%;border-collapse:collapse;font-size:13px}
table.t th{text-align:left;font-weight:600;padding:9px 10px;border-bottom:1px solid #d5d9d9;background:#f0f2f2;color:#0f1111}
table.t td{padding:11px 10px;border-bottom:1px solid #e7e9ec;vertical-align:top}
.pill{display:inline-block;padding:2px 9px;border-radius:10px;font-size:12px;font-weight:600}
"""


def sc_frame(body, sub=("Manage Orders", "Manage All Inventory", "Business Reports", "Buyer Messages", "Manage Customization", "Seller Assistant")):
    subs = "".join(f"<span>{s}</span>" for s in sub)
    return (f'<div class="sc"><div class="scn"><span style="font-size:20px;padding-right:14px;border-right:1px solid #3d5f66">☰</span><div class="logo">amazon <i>seller central</i></div>'
            f'<div class="mk"><b>Sample Paper Co</b> | United States ▾</div><div class="srch">Search</div><div class="sb">🔍</div>'
            f'<div class="r"><span>✉</span><span>⚙</span><span>EN ▾</span><span>Help</span></div></div>'
            f'<div class="scs"><span>🔖</span>{subs}<span class="ed">Edit</span></div><div class="scb">{body}</div></div>')


def sc_page(title, url, body, tabs=None, active=0):
    tabs = tabs or [(("#ff9900", "a"), title)]
    return chrome(tabs, active, url, sc_frame(body))


# ------------------------------------------------------------------ screens
S = {}


def screen(fn):
    S[fn.__name__] = fn
    return fn


@screen
def printq(st):
    jobs = [("P-049 - AI REPLACE: staff meeting notes from production numbers - Google Docs", "Dalia", "2", "12:41 PM"),
            ("P-088 - MT Log - for data collection - Google Docs", "Dalia", "3", "12:52 PM")]
    rows = "".join(f'<tr data-t="job{i}"><td>📄 {E(d)}</td><td>{"Paused" if st.get("paused", 1) else "Printing"}</td><td>{o}</td><td>{p}</td><td>{t}</td></tr>'
                   for i, (d, o, p, t) in enumerate(jobs[:st.get("n", 2)]))
    body = f"""<div style="height:100%;display:flex;flex-direction:column;font-size:12px">
    <div style="display:flex;gap:18px;padding:6px 10px;border-bottom:1px solid #e5e5e5"><span data-t="menu_printer">Printer</span><span>Document</span><span>View</span></div>
    <table style="width:100%;border-collapse:collapse"><tr style="text-align:left;color:#333">
    <th style="padding:6px 10px;font-weight:400;border-bottom:1px solid #ddd;width:56%">Document Name</th><th style="font-weight:400;border-bottom:1px solid #ddd">Status</th>
    <th style="font-weight:400;border-bottom:1px solid #ddd">Owner</th><th style="font-weight:400;border-bottom:1px solid #ddd">Pages</th><th style="font-weight:400;border-bottom:1px solid #ddd">Submitted</th></tr>
    {rows.replace('<td>', '<td style="padding:7px 10px">')}</table>
    <div style="margin-top:auto;border-top:1px solid #e5e5e5;padding:5px 10px;color:#555">{st.get("n", 2)} document(s) in queue</div></div>"""
    title = "Office Printer - Paused" if st.get("paused", 1) else "Office Printer"
    w = window(title, body, 150, 380, 980, 330, "settings", tid="queue")
    if st.get("hl"):
        w = w.replace(f'<span>{title}</span>', f'<span class="hl" style="padding:2px 6px">{title}</span>')
    return desk(st["clock"], w, on=("settings",))


@screen
def sheets_sales(st):
    hours = ["12 AM", "1 AM", "2 AM", "3 AM", "4 AM", "5 AM", "6 AM", "7 AM", "8 AM"]
    vals = [42.97, 0, 18.99, 0, 24.5, 31.98, 56.47, 88.95, 64.0]
    rows = ""
    for r in range(1, 30):
        if r == 1:
            cells = ["Hour", "Orders", "Units", "Sales", "Ads spend", "Synced"]
        elif r - 2 < len(hours) and r - 2 < st.get("rows", 9):
            i = r - 2
            cells = [hours[i], str([2, 0, 1, 0, 1, 2, 3, 5, 3][i]), str([4, 0, 2, 0, 1, 3, 5, 9, 6][i]), f"${vals[i]:.2f}",
                     f"${[1.12, .4, .3, .2, .3, .9, 2.1, 3.4, 2.2][i]:.2f}", "✓"]
        else:
            cells = [""] * 6
        sty = ' style="font-weight:600;background:#f8f9fa"' if r == 1 else ""
        new = r - 2 == st.get("rows", 9) - 1 and st.get("flash")
        rows += f'<tr{sty}{" class=new" if new else ""}><td class="rh">{r}</td>' + "".join(f"<td>{E(c)}</td>" for c in cells) + "<td></td>" * 6 + "</tr>"
    body = sheets_frame("Hourly Sales - Amazon (auto)", rows, "D10", "=SUM(D2:D10)" if st.get("sum") else "64",
                        ["Hourly", "Daily", "Ads", "Log"], cols="ABCDEFGHIJKL")
    page = chrome([(("#0f9d58", "▦"), "Hourly Sales - Amazon (auto) - Google Sheets")], 0, "docs.google.com/spreadsheets/d/1sAmPLe-hourly-sales/edit", body)
    t = toast("Google Drive", "hourly_sales.json is up to date", "1 file synced to My Drive · 8:00 AM", "explorer") if st.get("toast") else ""
    return desk(st["clock"], page + t)


SHEETS_CSS = """
.gs{height:100%;display:flex;flex-direction:column;font-family:Roboto,Arial;background:#f9fbfd}
.gs .top{height:64px;display:flex;align-items:center;gap:12px;padding:0 14px}
.gs .logo{width:28px;height:38px;background:#0f9d58;border-radius:3px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px}
.gs .nm{font-size:18px;color:#1f1f1f}.gs .mn{font-size:14px;color:#444;display:flex;gap:14px;margin-top:2px}
.gs .share{margin-left:auto;background:#c2e7ff;border-radius:18px;height:40px;padding:0 22px;display:flex;align-items:center;font:500 14px Roboto;color:#001d35}
.gs .tool{height:40px;margin:0 10px;border-radius:24px;background:#edf2fa;display:flex;align-items:center;gap:18px;padding:0 16px;color:#444;font-size:14px}
.gs .fx{height:32px;display:flex;align-items:center;border-bottom:1px solid #c7c7c7;background:#fff;margin-top:6px;font-size:13px}
.gs .fx .nb{width:90px;border-right:1px solid #c7c7c7;padding-left:10px;height:100%;display:flex;align-items:center}
.gs .fx .f{padding-left:10px;color:#222}
.gs table{border-collapse:collapse;background:#fff;font-size:13px;table-layout:fixed}
.gs td{border:1px solid #e1e1e1;height:24px;padding:0 6px;white-space:nowrap;overflow:hidden;width:118px}
.gs td.rh,.gs th{background:#f8f9fa;color:#5f6368;text-align:center;width:46px;font-weight:400;font-size:12px;border:1px solid #c7c7c7}
.gs th{height:22px}
.gs tr.new td{background:#e6f4ea}
.gs .tabsb{margin-top:auto;height:40px;background:#f9fbfd;border-top:1px solid #c7c7c7;display:flex;align-items:center;gap:6px;padding-left:12px;font-size:13px}
.gs .tabsb span{padding:8px 14px;border-radius:6px 6px 0 0;color:#444}
.gs .tabsb span.on{background:#e1e9f7;color:#0b57d0;font-weight:500}
.sel{outline:2px solid #1a73e8;outline-offset:-2px}
"""


def sheets_frame(name, rows, ref, fx, tabs, cols="ABCDEFGHIJ", active=0, widths=None):
    th = '<tr><th></th>' + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
    tbs = "".join(f'<span class="{"on" if i == active else ""}">{E(t)}</span>' for i, t in enumerate(tabs))
    cg = ""
    if widths:
        cg = "<colgroup><col style='width:46px'>" + "".join(f"<col style='width:{w}px'>" for w in widths) + "</colgroup>"
    return (f'<style>{SHEETS_CSS}</style><div class="gs"><div class="top"><div class="logo">▦</div><div><div class="nm">{E(name)} ☆</div>'
            f'<div class="mn"><span>File</span><span>Edit</span><span>View</span><span>Insert</span><span>Format</span><span>Data</span>'
            f'<span>Tools</span><span>Extensions</span><span>Help</span></div></div><div class="share">🔒 Share</div></div>'
            f'<div class="tool"><span>🔍</span><span>↶</span><span>↷</span><span>🖨</span><span>100% ▾</span><span>$</span><span>%</span>'
            f'<span>Default... ▾</span><span>— 10 +</span><span><b>B</b></span><span><i>I</i></span><span>A</span></div>'
            f'<div class="fx"><div class="nb">{ref}</div><div class="f"><i style="color:#888">fx</i>&nbsp;&nbsp;{E(fx)}</div></div>'
            f'<div style="flex:1;overflow:hidden"><table>{cg}{th}{rows}</table></div><div class="tabsb">＋ ☰ {tbs}</div></div>')


TEAMS_CSS = """
.tm{height:100%;display:flex;font-family:'Segoe UI';background:#f5f5f5}
.tm .rail{width:68px;background:#ebebeb;display:flex;flex-direction:column;align-items:center;gap:6px;padding-top:10px;flex:none}
.tm .rail div{width:56px;height:52px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:10px;color:#424242;border-radius:6px}
.tm .rail div.on{color:#5b5fc7;background:#fff}
.tm .rail b{font-size:19px;font-weight:400}
.tm .list{width:320px;background:#fafafa;border-right:1px solid #e0e0e0;flex:none}
.tm .lh{height:56px;display:flex;align-items:center;padding:0 16px;font:700 18px 'Segoe UI'}
.tm .ci{display:flex;gap:10px;padding:10px 14px;align-items:center}
.tm .ci.on{background:#fff;box-shadow:inset 3px 0 #5b5fc7}
.av{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font:600 13px 'Segoe UI';flex:none}
.tm .ci .n{font-weight:600;font-size:14px}.tm .ci .p{color:#616161;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;width:220px}
.tm .main{flex:1;display:flex;flex-direction:column;background:#fff}
.tm .mh{height:56px;border-bottom:1px solid #e0e0e0;display:flex;align-items:center;gap:10px;padding:0 20px;font:700 16px 'Segoe UI'}
.tm .mh span{font-weight:400;font-size:14px;color:#424242;margin-left:18px}
.tm .msgs{flex:1;padding:18px 26px;display:flex;flex-direction:column;gap:14px;justify-content:flex-end;background:#f5f5f5}
.mg{display:flex;gap:10px;max-width:78%}
.mg .b{background:#fff;border-radius:6px;padding:9px 13px;font-size:14px;line-height:1.45;box-shadow:0 1px 2px rgba(0,0,0,.1)}
.mg .meta{font-size:12px;color:#616161;margin-bottom:3px}
.mg.me{align-self:flex-end;flex-direction:row-reverse}
.mg.me .b{background:#e8ebfa}
.tm .cmp{margin:12px 20px 16px;border:1px solid #d1d1d1;border-bottom:2px solid #5b5fc7;border-radius:6px;height:46px;display:flex;align-items:center;padding:0 14px;color:#616161;font-size:14px;background:#fff}
"""


def teams(st):
    chats = st.get("chats", [("Maya R.", "Sent a video clip", "#c4314b"), ("Jess T.", "ok!", "#8764b8"), ("Bri S.", "thank you!!", "#038387"),
                             ("Production team", "Jess: envelopes are loaded", "#5b5fc7"), ("Nora P.", "see you tomorrow", "#ca5010")])
    li = "".join(f'<div class="ci{" on" if i == 0 else ""}"><div class="av" style="background:{c}">{n[0]}{n.split()[-1][0]}</div>'
                 f'<div><div class="n">{E(n)}</div><div class="p">{E(p)}</div></div></div>' for i, (n, p, c) in enumerate(chats))
    msgs = ""
    for m in st["msgs"]:
        who, text = m[0], m[1]
        me = who == "me"
        tid = f' data-t="{m[2]}"' if len(m) > 2 else ""
        av = "" if me else f'<div class="av" style="background:{chats[0][2]}">{chats[0][0][0]}{chats[0][0].split()[-1][0]}</div>'
        meta = (f'{m[3] if len(m) > 3 else ""}' if me else f'{E(chats[0][0])}&nbsp;&nbsp;{m[3] if len(m) > 3 else ""}')
        msgs += f'<div class="mg{" me" if me else ""}"{tid}>{av}<div><div class="meta">{meta}</div><div class="b">{text}</div></div></div>'
    body = (f'<style>{TEAMS_CSS}</style><div class="tm"><div class="rail"><div><b>🔔</b>Activity</div><div class="on"><b>💬</b>Chat</div>'
            f'<div><b>👥</b>Teams</div><div><b>📅</b>Calendar</div><div><b>📞</b>Calls</div><div><b>☁</b>OneDrive</div></div>'
            f'<div class="list"><div class="lh">Chat <span style="margin-left:auto;font-weight:400">⋯ &nbsp;✎</span></div>{li}</div>'
            f'<div class="main"><div class="mh"><div class="av" style="background:{chats[0][2]};width:32px;height:32px">{chats[0][0][0]}{chats[0][0].split()[-1][0]}</div>'
            f'{E(chats[0][0])}<span style="color:#5b5fc7;border-bottom:2px solid #5b5fc7;padding:16px 0">Chat</span><span>Shared</span></div>'
            f'<div class="msgs">{msgs}</div><div class="cmp" data-t="compose">{st.get("typing") or "Type a message"}<span style="margin-left:auto">😊 📎 ➤</span></div></div></div>')
    w = window("Chat | Maya R. | Microsoft Teams", body, 60, 70, 1160, 1150, "teams")
    return desk(st["clock"], w, on=("teams",))


@screen
def teams_video(st):
    clip = ('<div style="width:420px;border-radius:8px;overflow:hidden;background:#111" data-t="clip"><div style="height:236px;position:relative;'
            'background:linear-gradient(#fff 0 22px,#f1f1f1 22px);padding:28px 14px 0">'
            + "".join(f'<div style="height:24px;margin:6px 0;background:#fff;border:1px solid #e3e3e3;border-radius:3px;display:flex;align-items:center;gap:8px;padding:0 8px;font:11px Inter;color:#333">'
                      f'<span>#{1038 + i}</span><span style="width:{60 + i * 13 % 50}px;height:6px;background:#ccc;border-radius:3px"></span>'
                      f'<span style="margin-left:auto;background:#ffd79d;border-radius:8px;padding:0 6px">Unfulfilled</span></div>' for i in range(6))
            + '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center"><div style="width:58px;height:58px;border-radius:50%;'
            'background:rgba(0,0,0,.55);color:#fff;display:flex;align-items:center;justify-content:center;font-size:24px">▶</div></div></div>'
            '<div style="padding:8px 12px;color:#fff;font:12px \'Segoe UI\'">Shopify orders - screen recording.mp4 · 14:22</div></div>')
    msgs = [("them", "good morning!! here's yesterday's shopify orders walkthrough", "", "4:58 PM Yesterday"),
            ("them", clip, "", "4:59 PM Yesterday")]
    msgs += st.get("more", [])
    return teams(dict(st, msgs=msgs))


@screen
def teams_chat(st):
    return teams(st)


@screen
def sc_messages(st):
    rows = [("Kelsey W.", "Replacement request: item is different from what I ordered", "Respond within 4 hrs", "#c40000"),
            ("Dana P.", "Question about my order — can you rush it?", "Due in 11 hrs", "#c45500"),
            ("Mark L.", "Product question: are envelopes included?", "Due in 20 hrs", "#0f1111"),
            ("Tina R.", "Product question: what paper weight is this?", "Due in 22 hrs", "#0f1111")]
    lis = "".join(f'<div data-t="msg{i}" style="display:flex;gap:12px;padding:14px 16px;border-bottom:1px solid #e7e9ec;{"background:#edfdff;" if i == st.get("open", -1) else ""}">'
                  f'<div style="width:9px;height:9px;border-radius:50%;background:{"#007185" if i >= st.get("read", 0) else "transparent"};margin-top:6px"></div>'
                  f'<div style="flex:1"><div style="display:flex"><b style="font-size:14px">{n}</b><span style="margin-left:auto;font-size:12px;color:#565959">Oct 1</span></div>'
                  f'<div style="font-size:13px;margin:3px 0">{E(s)}</div><div style="font-size:12px;color:{c};font-weight:600">⏱ {d}</div></div></div>'
                  for i, (n, s, d, c) in enumerate(rows))
    o = st.get("open", -1)
    right = ('<div style="color:#565959;padding:60px;text-align:center">Select a message</div>' if o < 0 else
             f'<div style="padding:18px 22px"><div style="font:600 18px Inter">{E(rows[o][1])}</div>'
             f'<div style="font-size:12px;color:#565959;margin:6px 0 16px">Order 112-5550193-7781024 · Buyer: {rows[o][0]}</div>'
             f'<div style="background:#f0f2f2;border-radius:8px;padding:14px;font-size:14px;line-height:1.5;max-width:520px">'
             f'Hi, the invitations I got look different from the listing photo. The color is lighter than I expected. Can I get a replacement?</div>'
             f'<div style="margin-top:22px;border:1px solid #888c8c;border-radius:8px;height:120px;padding:12px;color:#6f7373" data-t="reply">Write a message…</div>'
             f'<div style="margin-top:12px;display:flex;gap:10px"><span class="ab y">Send</span><span class="ab">Templates</span><span class="ab">No response needed</span></div></div>')
    body = (f'<div class="h1">Buyer-Seller Messages</div><div style="display:flex;gap:10px;margin-bottom:14px">'
            f'<span class="ab b" data-t="needs">Needs response (4)</span><span class="ab">All messages</span><span class="ab">Unread</span><span class="ab">Archived</span></div>'
            f'<div style="display:flex;gap:16px;height:1000px"><div class="card" style="width:420px;padding:0;overflow:hidden">{lis}</div>'
            f'<div class="card" style="flex:1;padding:0">{right}</div></div>')
    return desk(st["clock"], f"<style>{SC_CSS}</style>" + sc_page("Amazon", "sellercentral.amazon.com/messaging/inbox?fi=responseNeeded", body))


@screen
def amazon_listing(st):
    inv = ('<div style="width:420px;height:520px;background:#fbf8f3;border:1px solid #ddd;display:flex;align-items:center;justify-content:center;position:relative" data-t="photo">'
           '<div style="width:300px;height:420px;background:#fff;box-shadow:0 6px 18px rgba(0,0,0,.18);display:flex;flex-direction:column;align-items:center;justify-content:center;'
           'font-family:Serif4;color:#5a3d6b;position:relative;overflow:hidden">'
           '<div style="position:absolute;top:-30px;left:-30px;width:150px;height:150px;border-radius:50%;background:radial-gradient(#b48ad8,#7d4fa8 60%,transparent 62%);opacity:.65"></div>'
           '<div style="position:absolute;bottom:-40px;right:-30px;width:170px;height:170px;border-radius:50%;background:radial-gradient(#d7b6ef,#9b6cc4 60%,transparent 62%);opacity:.6"></div>'
           '<div style="font-size:13px;letter-spacing:3px">TOGETHER WITH THEIR FAMILIES</div><div style="font-size:40px;margin:14px 0;font-style:italic">Emma &amp; Noah</div>'
           '<div style="font-size:12px;letter-spacing:2px">REQUEST THE HONOR OF YOUR PRESENCE</div><div style="font-size:15px;margin-top:16px">June 6, 2027</div></div></div>')
    body = (f'<div style="font-family:Inter,Arial;background:#fff;height:100%">'
            f'<div style="height:60px;background:#131921;display:flex;align-items:center;gap:16px;padding:0 16px;color:#fff">'
            f'<b style="font:700 22px Inter">amazon</b><div style="flex:1;height:40px;background:#fff;border-radius:6px;margin:0 20px;display:flex;align-items:center;'
            f'justify-content:flex-end"><div style="width:46px;height:40px;background:#febd69;border-radius:0 6px 6px 0;color:#111;display:flex;align-items:center;justify-content:center">🔍</div></div>'
            f'<span style="font-size:13px">Hello, sign in<br><b>Account &amp; Lists</b></span><span>🛒 Cart</span></div>'
            f'<div style="height:38px;background:#232f3e;color:#fff;display:flex;align-items:center;gap:18px;padding:0 16px;font-size:14px"><span>☰ All</span><span>Today\'s Deals</span><span>Registry</span><span>Gift Cards</span></div>'
            f'<div style="display:flex;gap:30px;padding:24px 30px">{inv}<div style="flex:1">'
            f'<div style="font:500 22px Inter;line-height:1.3">Purple Flower Wedding Invitations With Envelopes, Watercolor Floral Wedding Invites Set (Sample Shop)</div>'
            f'<div class="lnk" style="color:#007185;margin:6px 0">Visit the Sample Paper Co. Store</div><div style="color:#de7921">★★★★★ <span style="color:#007185">412 ratings</span></div>'
            f'<hr style="margin:12px 0;border:0;border-top:1px solid #ddd"><div style="font-size:28px"><sup style="font-size:13px">$</sup>54<sup style="font-size:13px">99</sup></div>'
            f'<div style="margin-top:14px;background:#fff;border:1px solid #d5d9d9;border-radius:8px;padding:14px">'
            f'<b>Customize now</b><div style="font-size:13px;color:#565959;margin:4px 0 10px">Names, date, venue · prints in uppercase as shown</div>'
            f'<div style="background:#ffd814;border-radius:20px;height:36px;display:flex;align-items:center;justify-content:center;font-size:14px" data-t="customize">Customize Now</div></div>'
            f'<ul style="margin:16px 0 0 18px;font-size:14px;line-height:1.6"><li>Set of 25 invitations with envelopes</li><li>Printed on thick 120 lb cardstock</li><li>Proof sent within 1 business day</li></ul></div></div></div>')
    return desk(st["clock"], chrome([(("#ff9900", "a"), "Amazon.com: Purple Flower Wedding Invitations")], 0, "amazon.com/dp/B0SAMPLE01", body))


@screen
def programs(st):
    progs = [("Adobe Creative Cloud", "Adobe Inc.", "9/12/2026", "421 MB"), ("BeeBEEP 5.8.6", "Marco Mastroddi", "3/2/2026", "38.1 MB"),
             ("DYMO Connect", "DYMO", "1/14/2026", "220 MB"), ("Google Chrome", "Google LLC", "9/30/2026", ""),
             ("Microsoft Teams", "Microsoft Corporation", "9/20/2026", "1.1 GB"), ("MT Log", "Modern Pink Paper", "9/29/2026", "72.4 MB"),
             ("Notepad++ (64-bit x64)", "Notepad++ Team", "6/2/2026", "14.2 MB")]
    rows = "".join(f'<tr{" data-t=prog_mt" if n == "MT Log" else ""} style="{"background:#cce8ff" if n == "MT Log" and st.get("sel") else ""}">'
                   f'<td style="padding:4px 8px">▣ {n}</td><td>{p}</td><td>{d}</td><td style="text-align:right;padding-right:10px">{s}</td></tr>'
                   for n, p, d, s in progs if not (n == "MT Log" and st.get("gone")))
    body = f"""<div style="display:flex;height:100%;font-size:12px"><div style="width:220px;background:#f0f6fd;padding:16px;line-height:2;color:#0645ad">Control Panel Home<br>View installed updates<br>Turn Windows features on or off</div>
    <div style="flex:1;padding:16px 20px"><div style="font-size:20px;color:#1e3287;margin-bottom:6px">Uninstall or change a program</div>
    <div style="color:#333;margin-bottom:10px">To uninstall a program, select it from the list and then click Uninstall, Change, or Repair.</div>
    <div style="border-bottom:1px solid #ddd;padding:4px 0;margin-bottom:4px">Organize ▾ &nbsp;&nbsp;<span data-t="uninstall" style="{'border:1px solid #7ab;padding:2px 8px;background:#e5f1fb' if st.get('sel') else 'color:#aaa'}">Uninstall</span></div>
    <table style="width:100%;border-collapse:collapse"><tr style="text-align:left;color:#4c607a"><th style="font-weight:400;padding:4px 8px">Name</th><th style="font-weight:400">Publisher</th><th style="font-weight:400">Installed On</th><th style="font-weight:400;text-align:right;padding-right:10px">Size</th></tr>{rows}</table></div></div>"""
    w = window("Programs and Features", body, 80, 120, 1120, 640, "settings")
    if st.get("confirm"):
        w += window("Programs and Features", '<div style="padding:22px;font-size:13px">Are you sure you want to uninstall MT Log?<div style="margin-top:28px;display:flex;gap:8px;justify-content:flex-end">'
                    '<span class="btn pri" data-t="yes">Yes</span><span class="btn">No</span></div></div>', 420, 380, 440, 170)
    if st.get("setup") is not None:
        k = st["setup"]
        w += window("MT Log Setup", f'<div style="padding:20px;font-size:13px"><b style="font-size:15px">{"Installing MT Log" if k < 100 else "MT Log is installed"}</b>'
                    f'<div style="color:#555;margin:6px 0 18px">{"Copying files…" if k < 100 else "Logging is on. You can close this window."}</div>'
                    f'<div style="height:14px;background:#e6e6e6;border-radius:7px;overflow:hidden"><div style="width:{k}%;height:100%;background:#06b025"></div></div>'
                    f'<div style="margin-top:26px;text-align:right"><span class="btn{" pri" if k >= 100 else ""}">{"Finish" if k >= 100 else "Cancel"}</span></div></div>', 380, 760, 520, 210, "mtlog")
    return desk(st["clock"], w, on=("settings",))


EXPLORER_CSS = """
.ex{height:100%;display:flex;flex-direction:column;font-size:13px;background:#fff}
.ex .bar{height:40px;display:flex;align-items:center;gap:10px;padding:0 10px;border-bottom:1px solid #e5e5e5}
.ex .addr{flex:1;height:30px;border:1px solid #e0e0e0;border-radius:4px;display:flex;align-items:center;padding:0 10px;gap:6px;color:#222;background:#fbfbfb;white-space:nowrap;overflow:hidden}
.ex .cmd{height:42px;display:flex;align-items:center;gap:20px;padding:0 14px;border-bottom:1px solid #e5e5e5;color:#333}
.ex .nav{width:210px;border-right:1px solid #eee;padding:10px 12px;line-height:2.1;color:#222;flex:none}
.ex table{width:100%;border-collapse:collapse}.ex th{font-weight:400;color:#555;text-align:left;padding:6px 8px;border-bottom:1px solid #eee}
.ex td{padding:6px 8px}
.ex tr.sel td{background:#cce8ff}
"""


def explorer(path, files, sel=None, rename=None, tid=None):
    crumbs = " › ".join(E(p) for p in path)
    rows = ""
    for i, (n, d, t, s) in enumerate(files):
        icon = "📁" if t == "File folder" else ("🗜" if "zip" in t.lower() else "📄")
        name = E(n)
        if rename is not None and i == rename[0]:
            name = f'<span style="border:1px solid #0067c0;padding:1px 4px;background:#fff">{E(rename[1])}</span>'
        rows += (f'<tr class="{"sel" if i == sel else ""}" data-t="f{i}"><td>{icon} {name}</td><td>{d}</td><td>{t}</td><td style="text-align:right">{s}</td></tr>')
    return (f'<style>{EXPLORER_CSS}</style><div class="ex"><div class="bar">← → ↑ ⟳<div class="addr">🖥 › {crumbs}</div>'
            f'<div style="width:220px;height:30px;border:1px solid #e0e0e0;border-radius:4px;padding:6px 10px;color:#777">Search</div></div>'
            f'<div class="cmd"><span>⊕ New ▾</span><span>✂</span><span>⧉</span><span>📋</span><span>✎</span><span>⤴</span><span>🗑</span><span>⇅ Sort ▾</span><span>☰ View ▾</span></div>'
            f'<div style="display:flex;flex:1"><div class="nav">🏠 Home<br>🖼 Gallery<br>☁ My Drive<br>🖥 Desktop<br>⬇ Downloads<br>📄 Documents<br>💻 This PC</div>'
            f'<div style="flex:1"><table><tr><th>Name</th><th>Date modified</th><th>Type</th><th style="text-align:right">Size</th></tr>{rows}</table></div></div></div>')


@screen
def startup_scripts(st):
    files = [("mpp-indesign-logger.jsx", "10/2/2026 8:33 AM", "JSX File", "18 KB")] if st.get("dropped") else []
    body = explorer(["Local Disk (C:)", "Users", "User", "AppData", "Roaming", "Adobe", "InDesign", "Version 20.0", "en_US", "Scripts", "Startup Scripts"],
                    files, sel=0 if st.get("dropped") else None)
    w = window("Startup Scripts - File Explorer", body, 60, 140, 1160, 560, "explorer", tid="explorer")
    if st.get("drag"):
        w += ('<div style="position:absolute;left:520px;top:470px;padding:6px 10px;background:rgba(204,232,255,.9);border:1px solid #99d1ff;'
              'font-size:12px;z-index:40" data-t="drag">📄 mpp-indesign-logger.jsx<br><span style="color:#0067c0">→ Copy to Startup Scripts</span></div>')
    if st.get("downloads"):
        w += window("Downloads - File Explorer", explorer(["Downloads"], [("mpp-indesign-logger.jsx", "10/2/2026 8:32 AM", "JSX File", "18 KB"),
                    ("MTLog-win-x64.zip", "10/2/2026 8:24 AM", "Compressed (zipped) Folder", "71,882 KB")], sel=0), 160, 720, 900, 380, "explorer")
    return desk(st["clock"], w, on=("explorer",))


@screen
def bee(st):
    msgs = "".join(f'<div style="margin:6px 0"><span style="color:{"#c0392b" if w == "me" else "#2471a3"};font-weight:700">'
                   f'{"Dalia" if w == "me" else st.get("who", "Jess")}</span> <span style="color:#888;font-size:11px">({t})</span><br>{E(m)}</div>'
                   for w, m, t in st["msgs"])
    body = (f'<div style="display:flex;height:100%;font:13px Noto"><div style="width:180px;background:#fdf6e3;border-right:1px solid #ddd;padding:10px;line-height:2">'
            f'<b>Users</b><br>🟢 Jess<br>🟢 Maya<br>🟢 Bri<br>🟡 Nora</div><div style="flex:1;display:flex;flex-direction:column">'
            f'<div style="flex:1;padding:12px;background:#fff">{msgs}</div><div style="height:70px;border-top:1px solid #ddd;padding:10px;color:#555" data-t="beein">{E(st.get("typing", ""))}</div></div></div>')
    w = window(f'{st.get("who", "Jess")} - BeeBEEP 5.8.6', body, 260, 300, 760, 520, "bee")
    return desk(st["clock"], st.get("under", "") + w, on=("bee",))


ASSIST_CSS = """
.as{position:absolute;right:30px;top:90px;width:430px;background:#1f1d2b;border-radius:14px;color:#eee;font-family:Inter;box-shadow:0 18px 50px rgba(0,0,0,.45);
 padding:16px;z-index:30}
.as .hd{display:flex;align-items:center;gap:10px;font:700 15px Inter;margin-bottom:12px}
.as .dot{width:10px;height:10px;border-radius:50%;background:#3ddc84;box-shadow:0 0 8px #3ddc84}
.rc{background:#2b2839;border-radius:10px;padding:12px 14px;margin-bottom:10px;border-left:4px solid #e8547f}
.rc b{display:block;font-size:13px;margin-bottom:4px}.rc span{font-size:12px;color:#b9b5c9;line-height:1.4}
.tip{position:absolute;right:40px;bottom:60px;background:#1f1d2b;color:#fff;border-radius:8px;padding:10px 14px;font:600 14px Inter;z-index:40}
"""


@screen
def assistant(st):
    cards = [("Batch your Amazon replies", "You opened 4 buyer messages. Reply to all of them in one sitting."),
             ("Great job using Ctrl + Shift + V!", "Pasting without formatting keeps your sheets clean. Keep it up!"),
             ("Close unused Chrome tabs", "You have 31 tabs open. Fewer tabs = faster Seller Central."),
             ("Save your InDesign file", "An order file has unsaved changes."),
             ("Try a template for customer replies", "Same question asked 3 times this week."),
             ("Pin MT Log to the taskbar", "So you can see it's running at a glance."),
             ("Take a 5 minute break", "You've been active for 52 minutes straight.")]
    n = st.get("cards", 0)
    hl = st.get("hl")
    cs = "".join(f'<div class="rc"{" data-t=short" if i == 1 else ""} style="{"outline:3px solid #ffd45e" if hl and i == 1 else ""}"><b>💡 {E(a)}</b><span>{E(b)}</span></div>'
                 for i, (a, b) in enumerate(cards[:n]))
    panel = (f'<style>{ASSIST_CSS}</style><div class="as" data-t="panel"><div class="hd"><div class="dot"></div>MPP Assistant'
             f'<span style="margin-left:auto;font-size:12px;color:#aaa">{n} new</span></div>'
             f'{cs or "<div style=color:#aaa;font-size:13px;padding:20px>Watching… first check soon.</div>"}</div>')
    if st.get("countdown"):
        panel += f'<div class="tip" data-t="tip">✳ MPP Assistant (Claude)<br><span style="color:#ffd45e">Next check in {st["countdown"]}</span></div>'
    under = st.get("under", "")
    return desk(st["clock"], under + panel, on=("mtlog", "claude"))


CLAUDE_CSS = """
.cl{height:100%;display:flex;font-family:Inter;background:#faf9f5;color:#141413}
.cl .side{width:260px;background:#f5f4ee;border-right:1px solid #e8e6dc;padding:14px 12px;font-size:13px;color:#3d3d3a;flex:none}
.cl .side .new{display:flex;align-items:center;gap:8px;padding:8px;border-radius:8px;font-weight:500;color:#c96442}
.cl .side .it{padding:7px 8px;border-radius:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cl .side .it.on{background:#e8e6dc}
.cl .main{flex:1;display:flex;flex-direction:column;align-items:center}
.cl .ttl{height:52px;width:100%;display:flex;align-items:center;justify-content:center;font-size:14px;color:#3d3d3a}
.cl .conv{width:720px;flex:1;display:flex;flex-direction:column;gap:20px;padding-top:12px;overflow:hidden}
.um{align-self:flex-end;background:#f0eee6;border-radius:14px;padding:11px 15px;font-size:15px;line-height:1.5;max-width:80%}
.am{font-family:Serif4;font-size:16.5px;line-height:1.62;color:#141413}
.am p{margin-bottom:10px}
.cl .inp{width:720px;margin:12px 0 20px;background:#fff;border:1px solid #e0ddd2;border-radius:18px;box-shadow:0 2px 10px rgba(0,0,0,.05);padding:14px 16px;min-height:96px;
 display:flex;flex-direction:column;font-size:15px}
.cl .inp .row{margin-top:auto;display:flex;align-items:center;gap:12px;color:#73726c;font-size:13px}
.cl .send{margin-left:auto;width:32px;height:32px;border-radius:9px;background:#c96442;color:#fff;display:flex;align-items:center;justify-content:center}
"""


@screen
def claude(st):
    conv = ""
    for m in st["conv"]:
        if m[0] == "u":
            conv += f'<div class="um"{" data-t=" + m[2] if len(m) > 2 else ""}>{E(m[1])}</div>'
        else:
            conv += f'<div class="am"{" data-t=" + m[2] if len(m) > 2 else ""}>{m[1]}</div>'
    chats = st.get("chats", ["MT Log install + InDesign logger", "MPP Assistant setup", "Team timing analysis", "Proof automator questions", "Printing log rules"])
    side = "".join(f'<div class="it{" on" if i == st.get("on", 0) else ""}">{E(c)}</div>' for i, c in enumerate(chats))
    typing = st.get("typing", "")
    body = (f'<style>{CLAUDE_CSS}</style><div class="cl"><div class="side"><div style="font:600 17px Serif4;padding:4px 8px 14px">Claude</div>'
            f'<div class="new">⊕ New chat</div><div style="margin:14px 8px 6px;color:#8a8880;font-size:12px">Recents</div>{side}</div>'
            f'<div class="main"><div class="ttl">{E(chats[st.get("on", 0)])} ▾</div><div class="conv">{conv}</div>'
            f'<div class="inp" data-t="prompt"><div style="color:{"#141413" if typing else "#8a8880"}">{E(typing) if typing else "Reply to Claude…"}</div>'
            f'<div class="row"><span>＋</span><span>⚙</span><span style="margin-left:auto">Opus ▾</span><div class="send">↑</div></div></div></div></div>')
    return desk(st["clock"], chrome([(("#d97757", "✳"), chats[st.get("on", 0)] + " - Claude")], 0, "claude.ai/chat/0a1b2c3d", body, bookmarks=False),
                on=("chrome",))


@screen
def console(st):
    if st.get("page") == "cost":
        body = ('<div style="padding:30px 40px;font-family:Inter"><div style="font:600 26px Serif4">Usage &amp; cost</div>'
                '<div style="display:flex;gap:16px;margin-top:22px">'
                '<div style="border:1px solid #e3e1d8;border-radius:12px;padding:18px 22px;width:300px" data-t="cost"><div style="color:#73726c;font-size:13px">Total cost · October</div>'
                '<div style="font:600 42px Inter;margin-top:6px">$0.03</div></div>'
                '<div style="border:1px solid #e3e1d8;border-radius:12px;padding:18px 22px;width:300px"><div style="color:#73726c;font-size:13px">Tokens</div><div style="font:600 42px Inter;margin-top:6px">9,412</div></div></div>'
                '<div style="margin-top:28px;height:220px;border:1px solid #e3e1d8;border-radius:12px;display:flex;align-items:flex-end;gap:10px;padding:20px">'
                + "".join(f'<div style="flex:1;height:{h}%;background:#d97757;border-radius:4px 4px 0 0;opacity:.85"></div>' for h in (3, 2, 4, 2, 6, 3, 2, 8, 5, 12, 4, 35))
                + '</div></div>')
    else:
        rows = [("mt-log-assistant", "sk-ant-api03-••••••••••••XyZ", "Oct 2, 2026", "Never"), ("sales-script", "sk-ant-api03-••••••••••••Ab9", "Aug 14, 2026", "Never")]
        if not st.get("new"):
            rows = rows[1:]
        body = ('<div style="padding:30px 40px;font-family:Inter"><div style="display:flex;align-items:center"><div style="font:600 26px Serif4">API keys</div>'
                '<span style="margin-left:auto;background:#141413;color:#fff;border-radius:8px;padding:9px 14px;font-size:14px" data-t="create">+ Create Key</span></div>'
                '<table style="width:100%;margin-top:22px;border-collapse:collapse;font-size:14px"><tr style="color:#73726c;text-align:left"><th style="padding:10px 0;font-weight:500">Name</th>'
                '<th style="font-weight:500">Key</th><th style="font-weight:500">Created</th><th style="font-weight:500">Expires</th></tr>'
                + "".join(f'<tr style="border-top:1px solid #e3e1d8"><td style="padding:14px 0">{a}</td><td style="font-family:Mono;font-size:13px">{b}</td><td>{c}</td><td>{d}</td></tr>' for a, b, c, d in rows)
                + '</table></div>')
    side = ('<div style="width:230px;background:#f5f4ee;border-right:1px solid #e8e6dc;padding:18px 14px;font:14px Inter;line-height:2.3;color:#3d3d3a">'
            '<div style="font:600 17px Serif4;margin-bottom:8px">Claude Console</div>Dashboard<br>Workbench<br>Usage<br>Cost<br>API keys<br>Settings</div>')
    page = f'<div style="display:flex;height:100%;background:#faf9f5">{side}<div style="flex:1">{body}</div></div>'
    return desk(st["clock"], chrome([(("#d97757", "✳"), "API keys | Claude Platform")], 0, "platform.claude.com/settings/keys", page, bookmarks=False))


@screen
def envvars(st):
    uv = [("OneDrive", "C:\\Users\\User\\OneDrive"), ("Path", "C:\\Users\\User\\AppData\\Local\\Microsoft\\WindowsApps;"), ("TEMP", "C:\\Users\\User\\AppData\\Local\\Temp")]
    if st.get("k1"):
        uv.insert(0, ("ANTHROPIC_API_KEY", "sk-ant-api03-••••••••••••XyZ"))
    if st.get("k2"):
        uv.insert(1, ("MPP_RECS_WEBAPP_URL", "https://script.google.com/macros/s/AKfy-SAMPLE/exec"))
    rows = "".join(f'<tr style="{"background:#cce8ff" if i == 0 and st.get("k1") and not st.get("k2") else ""}"><td style="padding:3px 6px">{a}</td><td>{E(b)}</td></tr>' for i, (a, b) in enumerate(uv))
    sv = "".join(f'<tr><td style="padding:3px 6px">{a}</td><td>{b}</td></tr>' for a, b in (("ComSpec", "C:\\Windows\\system32\\cmd.exe"), ("NUMBER_OF_PROCESSORS", "8"), ("OS", "Windows_NT"), ("Path", "C:\\Windows\\system32;C:\\Windows;…")))
    box = lambda t, r, tid: (f'<div style="margin:10px 14px 4px">{t}</div><div style="margin:0 14px;border:1px solid #c7c7c7;height:150px;overflow:hidden" data-t="{tid}">'
                             f'<table style="width:100%;border-collapse:collapse;font-size:12px"><tr style="text-align:left"><th style="font-weight:400;padding:3px 6px;border-bottom:1px solid #ddd;width:40%">Variable</th>'
                             f'<th style="font-weight:400;border-bottom:1px solid #ddd">Value</th></tr>{r}</table></div><div style="margin:8px 14px;text-align:right;display:flex;gap:6px;justify-content:flex-end">'
                             f'<span class="btn">New...</span><span class="btn">Edit...</span><span class="btn">Delete</span></div>')
    body = box("User variables for User", rows, "uservars") + box("System variables", sv, "sysvars") + \
        '<div style="margin:6px 14px;text-align:right;display:flex;gap:6px;justify-content:flex-end"><span class="btn pri">OK</span><span class="btn">Cancel</span></div>'
    w = window("Environment Variables", f'<div style="font-size:12px;background:#f9f9f9;height:100%">{body}</div>', 250, 220, 680, 560)
    if st.get("newdlg"):
        w += window("New User Variable", f'<div style="padding:18px;font-size:12px;background:#f9f9f9;height:100%"><div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">'
                    f'<span style="width:110px">Variable name:</span><div style="flex:1;border:1px solid #999;padding:5px;background:#fff" data-t="vname">{st["newdlg"][0]}</div></div>'
                    f'<div style="display:flex;align-items:center;gap:10px"><span style="width:110px">Variable value:</span><div style="flex:1;border:1px solid #999;padding:5px;background:#fff">{st["newdlg"][1]}</div></div>'
                    f'<div style="margin-top:18px;display:flex;gap:6px;justify-content:flex-end"><span class="btn pri" data-t="ok">OK</span><span class="btn">Cancel</span></div></div>', 330, 560, 600, 190)
    return desk(st["clock"], w, on=("settings",))


@screen
def apps_script(st):
    code = ["function doPost(e) {", "  const data = JSON.parse(e.postData.contents);", "  const sheet = SpreadsheetApp.getActive().getSheetByName('Recs');",
            "  sheet.appendRow([new Date(), data.card, data.reason]);", "  return ContentService.createTextOutput('ok');", "}"]
    lines = "".join(f'<div><span style="color:#999;display:inline-block;width:34px;text-align:right;margin-right:14px">{i + 1}</span>{E(l)}</div>' for i, l in enumerate(code))
    name = st.get("name", "Untitled project")
    body = (f'<div style="height:100%;display:flex;flex-direction:column;font-family:Roboto">'
            f'<div style="height:56px;display:flex;align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid #e0e0e0">'
            f'<div style="width:28px;height:28px;border-radius:6px;background:#4285f4;color:#fff;display:flex;align-items:center;justify-content:center">❯</div>'
            f'<span style="font-size:13px;color:#5f6368">Apps Script</span><span style="font-size:18px;color:#202124" data-t="pname">{E(name)}</span>'
            f'<span data-t="deploy" style="margin-left:auto;background:#1a73e8;color:#fff;border-radius:4px;padding:8px 16px;font-weight:500;font-size:14px">Deploy ▾</span></div>'
            f'<div style="display:flex;flex:1"><div style="width:56px;border-right:1px solid #e0e0e0;display:flex;flex-direction:column;align-items:center;gap:22px;padding-top:16px;color:#5f6368">ⓘ<br>&lt;&gt;<br>⏱<br>☰<br>⚙</div>'
            f'<div style="width:220px;border-right:1px solid #e0e0e0;padding:12px;font-size:14px;color:#202124"><div style="display:flex">Files <span style="margin-left:auto;color:#5f6368" data-t="plus">＋</span></div>'
            f'<div style="background:#e8f0fe;border-radius:0 16px 16px 0;padding:6px 10px;margin-top:8px;color:#1967d2">Code.gs</div><div style="margin-top:16px">Libraries ＋</div><div style="margin-top:12px">Services ＋</div></div>'
            f'<div style="flex:1"><div style="height:42px;display:flex;align-items:center;gap:16px;padding:0 14px;border-bottom:1px solid #e0e0e0;font-size:14px;color:#5f6368">↶ ↷ &nbsp;💾 &nbsp;▷ Run &nbsp;🐞 Debug &nbsp;<span style="border:1px solid #dadce0;border-radius:4px;padding:3px 8px">doPost ▾</span>&nbsp; Execution log</div>'
            f'<div style="font:14px Mono;padding:14px;line-height:1.7;color:#202124">{lines}</div></div></div></div>')
    page = chrome([(("#4285f4", "❯"), f"{name} - Project Editor - Apps Script")], 0, "script.google.com/home/projects/1SAMPLEprojectID/edit", body, bookmarks=False)
    if st.get("dlg") == "new":
        page += ('<div style="position:absolute;inset:0 0 48px 0;background:rgba(0,0,0,.35);z-index:20"></div><div style="position:absolute;left:250px;top:320px;width:780px;height:470px;'
                 'background:#fff;border-radius:8px;z-index:21;font-family:Roboto;padding:24px;box-shadow:0 12px 40px rgba(0,0,0,.4)"><div style="font-size:22px">New deployment</div>'
                 '<div style="display:flex;gap:30px;margin-top:20px"><div style="width:200px;font-size:14px;color:#5f6368">Select type ⚙<div style="margin-top:12px;background:#e8f0fe;color:#1967d2;padding:8px;border-radius:4px">Web app</div></div>'
                 '<div style="flex:1;font-size:14px"><div style="color:#5f6368">Configuration</div><div style="border:1px solid #dadce0;border-radius:4px;padding:10px;margin:10px 0">Description<br><b>mt log recs v1</b></div>'
                 '<div style="color:#5f6368;margin-top:14px">Web app</div><div style="border:1px solid #dadce0;border-radius:4px;padding:10px;margin:8px 0">Execute as<br><b>Me</b></div>'
                 '<div style="border:1px solid #dadce0;border-radius:4px;padding:10px" data-t="access">Who has access<br><b>Anyone</b></div></div></div>'
                 '<div style="position:absolute;right:24px;bottom:20px;display:flex;gap:10px"><span style="padding:9px 16px;color:#1a73e8">Cancel</span>'
                 '<span style="background:#1a73e8;color:#fff;border-radius:4px;padding:9px 18px" data-t="dodeploy">Deploy</span></div></div>')
    if st.get("dlg") == "done":
        page += ('<div style="position:absolute;inset:0 0 48px 0;background:rgba(0,0,0,.35);z-index:20"></div><div style="position:absolute;left:290px;top:400px;width:700px;height:270px;'
                 'background:#fff;border-radius:8px;z-index:21;font-family:Roboto;padding:24px"><div style="font-size:22px">Deployment successfully updated.</div>'
                 '<div style="margin-top:20px;color:#5f6368;font-size:14px">Web app</div><div style="font-size:14px">URL</div>'
                 '<div style="border:1px solid #dadce0;border-radius:4px;padding:10px;margin-top:6px;font-size:13px;color:#202124" data-t="url">https://script.google.com/macros/s/AKfy-SAMPLE-0000/exec</div>'
                 '<div style="color:#1a73e8;margin-top:10px;font-size:14px" data-t="copy">⧉ Copy</div><div style="position:absolute;right:24px;bottom:20px;background:#1a73e8;color:#fff;border-radius:4px;padding:9px 18px">Done</div></div>')
    return desk(st["clock"], page)


@screen
def powershell(st):
    lines = st.get("lines", [])
    out = "".join(f'<div>{l}</div>' for l in lines)
    body = (f'<div style="background:#0c0c0c;height:100%;display:flex;flex-direction:column"><div style="height:40px;background:#202020;display:flex;align-items:flex-end;padding-left:8px">'
            f'<div style="background:#0c0c0c;color:#fff;border-radius:8px 8px 0 0;padding:8px 16px;font-size:12px">⚡ Windows PowerShell &nbsp;✕</div><span style="color:#ccc;padding:8px">＋ ⌄</span></div>'
            f'<div style="padding:12px 14px;font:15px Mono;color:#cccccc;line-height:1.55">{out}</div></div>')
    w = '<div class="w" style="left:90px;top:200px;width:1100px;height:640px" data-t="term"><div class="wb">' + body + '</div></div>'
    return desk(st["clock"], st.get("under", "") + w, on=("term",))


@screen
def gcloud(st):
    body = ('<div style="font-family:Roboto;height:100%;background:#fff"><div style="height:56px;background:#fff;border-bottom:1px solid #dadce0;display:flex;align-items:center;gap:16px;padding:0 16px">'
            '<span>☰</span><b style="font:500 18px Roboto;color:#5f6368">Google Cloud</b><span style="border:1px solid #dadce0;border-radius:4px;padding:6px 12px;font-size:14px" data-t="proj">Select a project ▾</span>'
            '<div style="flex:1;height:40px;background:#f1f3f4;border-radius:8px;display:flex;align-items:center;padding:0 14px;color:#5f6368">🔍 Search (/) for resources, docs, products, and more</div></div>'
            '<div style="padding:30px 40px"><div style="font-size:24px;color:#202124">Welcome</div><div style="color:#5f6368;margin-top:6px">You\'re working in <b>no project selected</b></div>'
            '<div style="display:flex;gap:16px;margin-top:24px">' + "".join(f'<div style="border:1px solid #dadce0;border-radius:8px;padding:18px;width:250px;height:120px">'
                                                                              f'<b style="font-weight:500">{t}</b><div style="color:#5f6368;font-size:13px;margin-top:8px">{d}</div></div>'
                                                                              for t, d in (("Create a project", "Projects hold your APIs and billing"), ("APIs & Services", "Enable APIs, create credentials"),
                                                                                           ("Billing", "Set up a billing account"))) + '</div></div></div>')
    return desk(st["clock"], chrome([(("#4285f4", "☁"), "Welcome – Google Cloud console")], 0, "console.cloud.google.com/welcome", body, bookmarks=False))


@screen
def notepad(st):
    tabs = st["tabs"]
    ts = "".join(f'<div style="padding:8px 14px;border-radius:6px 6px 0 0;{"background:#fff" if i == st.get("on", 0) else ""};font-size:12px">{E(t)} ✕</div>' for i, t in enumerate(tabs))
    text = "".join(f"<div>{E(l) if l else '&nbsp;'}</div>" for l in st["text"])
    body = (f'<div style="height:100%;display:flex;flex-direction:column;background:#fff"><div style="height:38px;background:#f3f3f3;display:flex;align-items:flex-end;padding-left:6px">{ts}<span style="padding:8px">＋</span></div>'
            f'<div style="height:30px;display:flex;gap:18px;align-items:center;padding:0 12px;font-size:12px;border-bottom:1px solid #eee">File &nbsp; Edit &nbsp; View</div>'
            f'<div style="flex:1;padding:12px 16px;font:15px Mono;line-height:1.55;color:#111" data-t="text">{text}</div>'
            f'<div style="height:24px;border-top:1px solid #eee;font-size:11px;color:#555;padding:4px 12px">Ln 1, Col 1 &nbsp;|&nbsp; 100% &nbsp;|&nbsp; Windows (CRLF) &nbsp;|&nbsp; UTF-8</div></div>')
    x, y, w, h = st.get("box", (120, 160, 1040, 760))
    win = window(st.get("title", tabs[st.get("on", 0)] + " - Notepad"), body, x, y, w, h, "notepad")
    if st.get("saveas"):
        win += window("Save As", f'<div style="padding:16px;font-size:12px;background:#f9f9f9;height:100%"><div style="height:200px;border:1px solid #ddd;background:#fff;padding:8px;line-height:1.9">'
                      f'📁 Customer Service<br>📄 Shopify CS script 9.24.26.txt<br>📄 Amazon CS script.txt</div><div style="display:flex;gap:10px;align-items:center;margin-top:14px">'
                      f'<span style="width:80px">File name:</span><div style="flex:1;border:1px solid #0067c0;padding:5px;background:#fff" data-t="fname">{E(st["saveas"])}</div></div>'
                      f'<div style="display:flex;justify-content:flex-end;gap:6px;margin-top:14px"><span class="btn pri" data-t="save">Save</span><span class="btn">Cancel</span></div></div>',
                      300, 420, 680, 360, "notepad")
    return desk(st["clock"], st.get("under", "") + win, on=("notepad",))


@screen
def proofs(st):
    files = [("7612 - SAMPLE ORDER A - 20 - FLAT", "10/2/2026 9:31 AM", "File folder", ""), ("7614 - SAMPLE ORDER B - 10 - FLD", "10/2/2026 9:33 AM", "File folder", ""),
             ("7619 - SAMPLE ORDER C - 50 - FLD", "10/2/2026 9:36 AM", "File folder", ""), ("proof_results.txt", "10/2/2026 9:39 AM", "Text Document", "3 KB"),
             ("proof_report_0939.html", "10/2/2026 9:39 AM", "HTML File", "41 KB")]
    if st.get("copy"):
        files.insert(2, ("7614 - SAMPLE ORDER B - 10 - FLD - Copy", "10/2/2026 11:06 AM", "File folder", ""))
    ren = (2, "7614 - SAMPLE ORDER B - test diff date") if st.get("rename") else None
    body = explorer(["My Drive", "Orders", "Auto Proofs", "10-02-2026"], files, sel=st.get("sel"), rename=ren)
    return desk(st["clock"], window("10-02-2026 - File Explorer", body, 60, 140, 1160, 620, "explorer", tid="explorer"), on=("explorer",))


@screen
def video_player(st):
    k = st.get("k", 0.3)
    rows = "".join(f'<div style="height:38px;margin:6px 0;background:#fff;border:1px solid #e3e3e3;border-radius:6px;display:flex;align-items:center;gap:14px;padding:0 14px;font:13px Inter;color:#303030">'
                   f'<span>☐</span><b>#{1040 + i}</b><span style="color:#616161">Oct 1 at {9 + i % 7}:{(i * 17) % 60:02d} am</span><span>{n}</span>'
                   f'<span style="margin-left:auto;background:#ffd79d;border-radius:8px;padding:1px 8px;font-size:12px">● Unfulfilled</span><span>${p}</span></div>'
                   for i, (n, p) in enumerate((("Sample Customer", "64.00"), ("Jordan Lee", "42.50"), ("Avery Kim", "88.00"), ("Riley Fox", "120.00"),
                                                ("Casey Moore", "35.99"), ("Morgan Diaz", "54.00"), ("Taylor Brooks", "76.25"), ("Jamie Cruz", "49.00"))))
    vid = (f'<div style="position:absolute;left:0;right:0;top:0;bottom:84px;background:#f1f1f1;padding:60px 120px">'
           f'<div style="font:700 22px Inter;margin-bottom:12px">Orders <span style="font-weight:400;font-size:14px;color:#616161">Unfulfilled</span></div>{rows}</div>'
           f'<div style="position:absolute;left:0;right:0;bottom:0;height:84px;background:#1b1b1b;color:#fff;padding:14px 22px">'
           f'<div style="height:5px;background:#555;border-radius:3px"><div style="width:{k * 100:.0f}%;height:5px;background:#8c90ff;border-radius:3px"></div></div>'
           f'<div style="display:flex;gap:18px;margin-top:14px;font-size:14px">⏮ ⏸ ⏭ &nbsp; {int(k * 862) // 60}:{int(k * 862) % 60:02d} / 14:22 <span style="margin-left:auto">1x &nbsp; ⛶</span></div></div>')
    w = window("Shopify orders - screen recording.mp4 - OneDrive", f'<div style="position:relative;height:100%">{vid}</div>', 40, 60, 1200, 1000, "chrome", tid="player")
    return desk(st["clock"], w)


SHOPIFY_CSS = """
.sh{height:100%;display:flex;flex-direction:column;font-family:Inter;background:#f1f1f1;color:#303030}
.sh .top{height:56px;background:#1a1a1a;display:flex;align-items:center;gap:16px;padding:0 16px;color:#fff}
.sh .top .s{flex:1;max-width:520px;margin:0 auto;height:34px;border-radius:10px;background:#303030;color:#b5b5b5;display:flex;align-items:center;padding:0 12px;font-size:13px}
.sh .nav{width:240px;padding:12px;font-size:13px;line-height:2.3;color:#303030;flex:none;background:#ebebeb}
.sh .nav .on{background:#fff;border-radius:8px;padding:0 8px;font-weight:600}
.sh .card{background:#fff;border-radius:12px;box-shadow:0 1px 0 rgba(0,0,0,.07),inset 0 -1px 0 rgba(0,0,0,.08)}
.badge{display:inline-flex;align-items:center;gap:4px;border-radius:8px;padding:2px 8px;font-size:12px;font-weight:550}
"""


@screen
def shopify(st):
    orders = [("#1048", "Oct 2 at 11:02 am", "Sample Customer", "$64.00", "Paid", "Unfulfilled", "3 items"),
              ("#1047", "Oct 2 at 8:41 am", "Jordan Lee", "$42.50", "Paid", "Unfulfilled", "1 item"),
              ("#1046", "Oct 1 at 9:15 pm", "Avery Kim", "$88.00", "Paid", "Unfulfilled", "2 items"),
              ("#1045", "Oct 1 at 4:30 pm", "Riley Fox", "$120.00", "Paid", "Unfulfilled", "4 items"),
              ("#1044", "Oct 1 at 1:12 pm", "Casey Moore", "$35.99", "Paid", "Unfulfilled", "1 item"),
              ("#1043", "Oct 1 at 10:48 am", "Morgan Diaz", "$54.00", "Paid", "Unfulfilled", "2 items")]
    rows = "".join(f'<tr style="border-top:1px solid #ebebeb"><td style="padding:10px 12px">☐</td><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{d}</td>'
                   f'<td><span class="badge" style="background:#ebebeb">● {e}</span></td><td><span class="badge" style="background:#ffd6a4">◐ {f}</span></td><td>{g}</td></tr>'
                   for a, b, c, d, e, f, g in orders)
    body = (f'<style>{SHOPIFY_CSS}</style><div class="sh"><div class="top"><b style="font:700 16px Inter">🛍 shopify</b><div class="s">🔍 Search</div>'
            f'<span style="font-size:13px">Sample Paper Co ▾</span></div><div style="display:flex;flex:1"><div class="nav">🏠 Home<br><div class="on">📥 Orders <span style="float:right">6</span></div>'
            f'🏷 Products<br>👤 Customers<br>📣 Marketing<br>🏷 Discounts<br>📊 Analytics<br><br>Sales channels<br>🏪 Online Store</div>'
            f'<div style="flex:1;padding:20px 26px"><div style="display:flex;align-items:center;margin-bottom:14px"><b style="font-size:20px">📥 Orders</b>'
            f'<span style="margin-left:auto;background:#fff;border-radius:8px;padding:6px 12px;font-size:13px;box-shadow:0 1px 2px rgba(0,0,0,.2)">Export</span>'
            f'<span style="margin-left:8px;background:#303030;color:#fff;border-radius:8px;padding:6px 12px;font-size:13px">Create order</span></div>'
            f'<div class="card"><div style="display:flex;gap:6px;padding:8px;font-size:13px;border-bottom:1px solid #ebebeb"><span style="padding:4px 10px">All</span>'
            f'<span style="padding:4px 10px;background:#ebebeb;border-radius:8px;font-weight:600" data-t="unf">Unfulfilled</span><span style="padding:4px 10px">Unpaid</span><span style="padding:4px 10px">Open</span><span style="padding:4px 10px">Archived</span></div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:13px"><tr style="color:#616161;text-align:left;background:#f7f7f7"><th style="padding:8px 12px"></th><th>Order</th><th>Date</th><th>Customer</th><th>Total</th>'
            f'<th>Payment status</th><th>Fulfillment status</th><th>Items</th></tr>{rows}</table></div></div></div></div>')
    return desk(st["clock"], chrome([(("#5e8e3e", "S"), "Sample Paper Co · Orders · Shopify")], 0, "admin.shopify.com/store/sample-paper-co/orders?selectedView=unfulfilled", body))


@screen
def tracker(st):
    data = [("ID", "Project", "Owner", "Status", "Next step", "Due"),
            ("P-071", "Amazon customization pop-ups: Christmas, wedding, funeral listings", "Jess", "In progress", "Update the remaining listings", "10/9"),
            ("P-074", 'Add "prints in uppercase as shown" to listings', "Maya", "In progress", "Etsy + Amazon text", "10/7"),
            ("P-079", "New Shopify customer service script (collapsing)", "Dalia", "Done ✓", "Team uses new version", "10/2"),
            ("P-081", "Auto proofs: follow-up message on reload", "Bri", "Testing", "Check reload follow-up", "10/6"),
            ("P-085", "Seller Assistant workflow: unshipped customizations", "Dalia", "New", "Name match ~80%", "10/10"),
            ("P-088", "MT Log for data collection", "Dalia", "In progress", "InDesign logger on every PC", "10/3"),
            ("P-049", "AI drafts staff meeting notes from production numbers", "Dalia", "Idea", "Print + review", "10/15")]
    hl = st.get("hl")
    rows = ""
    for r in range(1, 26):
        cells = data[r - 1] if r - 1 < len(data) else [""] * 6
        sty = ' style="font-weight:700;background:#fde4ec"' if r == 1 else (' style="background:#fff7d6"' if hl and r - 1 in hl else "")
        rows += f'<tr{sty}><td class="rh">{r}</td>' + "".join(f"<td>{E(c)}</td>" for c in cells) + "</tr>"
    body = sheets_frame("MPP Project Tracker", rows, "B2", data[1][1], ["Active", "Ideas", "Done", "Team"], cols="ABCDEF", widths=[70, 470, 80, 110, 250, 60])
    return desk(st["clock"], chrome([(("#0f9d58", "▦"), "MPP Project Tracker - Google Sheets")], 0, "docs.google.com/spreadsheets/d/1sAmPLe-tracker/edit", body))


@screen
def sc_customize(st):
    lab = st.get("label", "Host name")
    form = (f'<div class="card" style="width:430px"><b style="font-size:16px">Text option</b>'
            f'<div style="margin-top:12px;font-size:13px">Label *</div><div style="border:1px solid #888c8c;border-radius:6px;padding:8px;margin-top:4px" data-t="label">{E(lab)}</div>'
            f'<div style="margin-top:10px;font-size:13px">Instructions</div><div style="border:1px solid #888c8c;border-radius:6px;padding:8px;margin-top:4px;color:#565959">Enter the host name(s)</div>'
            f'<div style="display:flex;gap:10px;margin-top:12px">' + "".join(f'<div style="flex:1"><div style="font-size:13px">{k}</div><div style="border:1px solid #888c8c;border-radius:6px;padding:8px;margin-top:4px" data-t="in_{k}">{v}</div></div>'
                                                                              for k, v in (("X", st.get("x", "122")), ("Y", "88"), ("Width", "260"), ("Height", st.get("h", "6")))) +
            f'</div><div style="margin-top:12px;font-size:13px">Font</div><div style="border:1px solid #888c8c;border-radius:6px;padding:8px;margin-top:4px">Playfair Display ▾</div>'
            f'<div style="margin-top:16px;display:flex;gap:10px"><span class="ab y" data-t="save">Save</span><span class="ab">Preview</span></div></div>')
    prev = ('<div class="card" style="flex:1;display:flex;align-items:center;justify-content:center;background:#fafafa"><div style="width:360px;height:500px;background:#fff;'
            'box-shadow:0 4px 16px rgba(0,0,0,.18);position:relative;font-family:Serif4;color:#9b1c1c;text-align:center;padding-top:60px;border:10px solid #f6eaea">'
            '<div style="font-size:15px;letter-spacing:3px">YOU\'RE INVITED TO A</div><div style="font-size:38px;font-style:italic;margin:10px 0">Holiday Cocktail Party</div>'
            f'<div style="border:2px dashed #2162a1;margin:20px 40px;padding:8px;color:#333;font-family:Inter;font-size:15px" data-t="box">{E(lab)}</div>'
            '<div style="font-size:14px">DECEMBER 12 · 7 PM</div><div style="position:absolute;bottom:20px;left:0;right:0;font-size:24px">❄ ✦ ❄</div></div></div>')
    body = (f'<div class="h1">Manage customization: CPI-SAMPLE-017</div><div style="display:flex;gap:10px;margin-bottom:14px"><span class="ab b">Surface 1: Front</span><span class="ab">Surface 2: Back</span>'
            f'<span class="ab">Options</span></div><div style="display:flex;gap:16px;height:640px">{form}{prev}</div>')
    return desk(st["clock"], f"<style>{SC_CSS}</style>" + sc_page("Amazon", "sellercentral.amazon.com/gestalt/managecustomization/index.html?sku=CPI-SAMPLE-017", body))


@screen
def amazon_popup(st):
    f = st.get("fields", {})
    rows = "".join(f'<div style="margin-top:12px;font-size:14px"><b>{k}</b><div style="border:1px solid #888c8c;border-radius:6px;padding:9px;margin-top:5px;min-height:38px" data-t="pf{i}">{E(f.get(k, ""))}</div></div>'
                   for i, k in enumerate(("Name of Host", "Date", "Time", "RSVP Info and/or Additional Text to Print")))
    modal = (f'<div style="position:absolute;inset:0;background:rgba(0,0,0,.45)"></div><div style="position:absolute;left:170px;top:60px;width:940px;height:1060px;background:#fff;border-radius:8px;'
             f'font-family:Inter;display:flex;overflow:hidden"><div style="flex:1;background:#f7f7f7;display:flex;align-items:center;justify-content:center">'
             f'<div style="width:330px;height:460px;background:#fff;border:10px solid #f6eaea;box-shadow:0 4px 16px rgba(0,0,0,.2);text-align:center;padding-top:50px;font-family:Serif4;color:#9b1c1c">'
             f'<div style="font-size:14px;letter-spacing:3px">YOU\'RE INVITED TO A</div><div style="font-size:34px;font-style:italic;margin:8px 0">Holiday Cocktail Party</div>'
             f'<div style="font:15px Inter;color:#333;margin-top:16px">HOSTED BY {E(f.get("Name of Host", "").upper())}</div><div style="font:13px Inter;color:#333;margin-top:8px">{E(f.get("Time", "").upper())}</div>'
             f'<div style="font:13px Inter;color:#333;margin:10px 30px">{E(f.get("RSVP Info and/or Additional Text to Print", "").upper())}</div></div></div>'
             f'<div style="width:420px;padding:24px;border-left:1px solid #ddd"><div style="font:600 20px Inter">Customize your item</div>'
             f'<div style="font-size:13px;color:#565959;margin-top:4px">Option: Holiday Cocktail Party</div>{rows}'
             f'<div style="margin-top:22px;background:#ffd814;border-radius:20px;height:38px;display:flex;align-items:center;justify-content:center">Add to Cart</div></div></div>')
    page = amazon_listing(st).split('<div class="taskbar">')[0]
    return page + modal + taskbar(st["clock"], ("chrome",)) if False else desk(st["clock"], chrome([(("#ff9900", "a"), "Amazon.com: Personalized Christmas Party Invitations")], 0,
                                                                                                   "amazon.com/dp/B0SAMPLE17", f'<div style="position:relative;height:100%;background:#fff">{modal}</div>'))


WF_CSS = """
.wf{display:flex;gap:16px;height:100%}
.wf .chat{width:440px;display:flex;flex-direction:column}
.bub{border-radius:12px;padding:10px 13px;font-size:13.5px;line-height:1.45;margin-bottom:10px;max-width:92%}
.bub.u{align-self:flex-end;background:#e3f2f5}.bub.a{background:#fff;border:1px solid #d5d9d9}
"""


@screen
def workflow(st):
    msgs = st.get("msgs", [])
    bub = "".join(f'<div class="bub {w}">{E(t)}</div>' for w, t in msgs)
    stage = st.get("stage", "preview0")
    if stage == "preview0":
        right = ('<div style="font:600 16px Inter">Preview results</div><div style="color:#565959;font-size:13px;margin:4px 0 14px">Sample run on 5 unshipped orders</div>'
                 '<table class="t"><tr><th>Order ID</th><th>SKU</th><th>Customization</th></tr>'
                 + "".join(f'<tr><td>112-555{i}019-77810{i}4</td><td>WI-SAMPLE-0{i}</td><td style="color:#b12704">— none returned —</td></tr>' for i in range(5)) + '</table>')
    elif stage == "setup":
        right = (f'<div style="font:600 16px Inter">Workflow details</div><div style="margin-top:12px;font-size:13px">Name</div>'
                 f'<div style="border:1px solid #888c8c;border-radius:6px;padding:9px;margin-top:4px" data-t="wfname">{E(st.get("name", ""))}</div>'
                 f'<div style="margin-top:12px;font-size:13px">Schedule</div><div style="border:1px solid #888c8c;border-radius:6px;padding:9px;margin-top:4px">Every day at 7:00 AM ▾</div>'
                 f'<div style="margin-top:12px;font-size:13px">Output</div><div style="border:1px solid #888c8c;border-radius:6px;padding:9px;margin-top:4px">CSV file + email me</div>'
                 f'<div style="margin-top:12px;display:flex;align-items:center;gap:10px;font-size:13px"><span style="width:40px;height:22px;border-radius:11px;background:{"#007185" if st.get("on") else "#bbb"};'
                 f'position:relative;display:inline-block" data-t="toggle"><span style="position:absolute;top:2px;{"right:2px" if st.get("on") else "left:2px"};width:18px;height:18px;border-radius:50%;background:#fff"></span></span>'
                 f'{"Active" if st.get("on") else "Off"}</div><div style="margin-top:22px;display:flex;gap:10px"><span class="ab o" data-t="runnow">▶ Run now</span><span class="ab">Save draft</span></div>'
                 + (f'<div style="margin-top:18px;background:#e7f4f5;border-radius:8px;padding:12px;font-size:13px" data-t="ran">✅ Run complete · 72 orders · <span class="lnk">Download CSV</span></div>' if st.get("ran") else ""))
    else:
        right = ""
    body = (f'<style>{WF_CSS}</style><div class="h1">Create workflow <span class="pill" style="background:#e7f4f5;color:#007185;font-size:12px;vertical-align:middle">Seller Assistant · Beta</span></div>'
            f'<div class="wf"><div class="card chat"><div style="font:600 14px Inter;margin-bottom:10px">✦ Seller Assistant</div><div style="flex:1;display:flex;flex-direction:column;justify-content:flex-end">{bub}</div>'
            f'<div style="border:1px solid #888c8c;border-radius:10px;padding:10px;color:{"#0f1111" if st.get("typing") else "#6f7373"};font-size:13px;min-height:60px" data-t="wfin">{E(st.get("typing") or "Describe your workflow...")}</div></div>'
            f'<div class="card" style="flex:1">{right}</div></div>')
    return desk(st["clock"], f"<style>{SC_CSS}</style>" + sc_page("Create Workflow", "sellercentral.amazon.com/myworkflows/agents/create", body))


@screen
def csv_view(st):
    data = [("order-id", "purchase-date", "sku", "ship-to-name", "customization: Name(s)", "customization: Date", "customization: Notes")]
    names = [("Sarah Miller", "Sarah & Ben Miller"), ("J. Thompson", "In loving memory of Rose Thompson"), ("Amy Chen", "Amy & Dev"),
             ("Lauren Park", "Holiday Cocktail Party - Lauren"), ("Mike Rivera", "Mike's 40th"), ("Kim Nguyen", "Kim + Tom"), ("Pat Doyle", "Celebrating Ruth Ellis"),
             ("Grace Hall", "Grace & Owen"), ("Dan Webb", "Webb Family Christmas"), ("Rosa Ortiz", "Rosa's Baby Shower")]
    for i, (a, b) in enumerate(names):
        data.append((f"112-55{i}0193-77{i}1024", "2026-10-0" + str(1 + i % 2), f"WI-SAMPLE-{10 + i}", a, b, f"{(i % 12) + 1}/{(i * 3) % 28 + 1}/2027", "uppercase as shown" if i % 3 == 0 else ""))
    if st.get("match"):
        data[0] = data[0] + ("name match",)
        pcts = [92, 18, 85, 81, 74, 88, 12, 90, 70, 83]
        data = [data[0]] + [r + (f"{p}%",) for r, p in zip(data[1:], pcts)]
    rows = ""
    for r in range(1, 30):
        cells = data[r - 1] if r - 1 < len(data) else [""] * len(data[0])
        sty = ' style="font-weight:700;background:#f8f9fa"' if r == 1 else ""
        tds = ""
        for j, c in enumerate(cells):
            col = ""
            if st.get("match") and j == 7 and r > 1 and c:
                col = ' style="background:#e6f4ea;color:#137333;font-weight:600"' if int(c[:-1]) >= 80 else ' style="background:#fce8e6;color:#c5221f;font-weight:600"'
            tds += f"<td{col}>{E(c)}</td>"
        rows += f'<tr{sty}><td class="rh">{r}</td>{tds}</tr>'
    w = [160, 100, 120, 130, 250, 100, 150] + ([100] if st.get("match") else [])
    body = sheets_frame("Unshipped Orders Customization Export", rows, "E2", data[1][4], ["unshipped_customizations_2026-10-02"], cols="ABCDEFGH"[:len(w)], widths=w)
    return desk(st["clock"], chrome([(("#0f9d58", "▦"), "Unshipped Orders Customization Export - Google Sheets")], 0, "docs.google.com/spreadsheets/d/1sAmPLe-export/edit", body))


@screen
def zipview(st):
    files = [("customization_data.xml", "10/2/2026 1:34 PM", "XML Document", "6 KB"), ("surface_1_front.svg", "10/2/2026 1:34 PM", "SVG Document", "48 KB"),
             ("surface_2_back.svg", "10/2/2026 1:34 PM", "SVG Document", "22 KB"), ("preview.jpg", "10/2/2026 1:34 PM", "JPG File", "212 KB")]
    w = window("112-5550193-7781024.zip - File Explorer", explorer(["Downloads", "112-5550193-7781024.zip"], files, sel=st.get("sel")), 60, 120, 1160, 420, "explorer")
    if st.get("xml"):
        xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<customizationData>', '  <surface name="Front">', '    <area label="Name(s)">',
               '      <text>SARAH & BEN MILLER</text>', '      <font>Playfair Display</font>', '    </area>', '    <area label="Date">', '      <text>JUNE 6, 2027</text>',
               '    </area>', '  </surface>', '</customizationData>']
        xmlhtml = "".join("<div>" + E(l).replace(" ", "&nbsp;") + "</div>" for l in xml)
        w += window("customization_data.xml - Notepad", f'<div style="padding:12px 16px;font:15px Mono;line-height:1.55;background:#fff;height:100%">{xmlhtml}</div>',
                    200, 580, 860, 440, "notepad")
    return desk(st["clock"], w, on=("explorer",))


@screen
def github_md(st):
    md = ("<h1 style='font-size:28px;border-bottom:1px solid #d1d9e0;padding-bottom:8px'>Printing log analysis rules</h1><p>How to read print jobs in MT Log.</p>"
          "<h2 style='font-size:21px;margin-top:20px'>1. A print is only real if it finished</h2><ul style='margin-left:22px;line-height:1.8'><li>Match <code>print_job</code> to <code>print_job_finished</code>.</li>"
          "<li>If the status says <b>Paused</b>, nothing came out.</li><li>Count pages printed, not pages sent.</li></ul>"
          "<h2 style='font-size:21px;margin-top:20px'>2. Labels</h2><ul style='margin-left:22px;line-height:1.8'><li>A DYMO print within 45 s of the shipping page = label bought.</li></ul>")
    body = ('<div style="font-family:Inter;background:#fff;height:100%"><div style="height:62px;background:#f6f8fa;border-bottom:1px solid #d1d9e0;display:flex;align-items:center;gap:12px;padding:0 20px">'
            '<span style="font-size:26px">◯</span><b>sample-user / shop-tools</b></div><div style="padding:24px 40px"><div style="border:1px solid #d1d9e0;border-radius:6px">'
            '<div style="background:#f6f8fa;padding:10px 16px;border-bottom:1px solid #d1d9e0;font-size:14px">docs / PRINTING_LOG_ANALYSIS_RULES.md</div>'
            f'<div style="padding:24px 32px;font-size:15px;line-height:1.6">{md}</div></div></div></div>')
    return desk(st["clock"], chrome([(("#24292f", "◯"), "PRINTING_LOG_ANALYSIS_RULES.md")], 0, "github.com/sample-user/shop-tools/blob/main/docs/PRINTING_LOG_ANALYSIS_RULES.md", body))


DOCS_CSS = """
.gd{height:100%;display:flex;flex-direction:column;font-family:Roboto;background:#f9fbfd}
.gd .paper{width:816px;margin:16px auto 0;background:#fff;box-shadow:0 1px 3px rgba(60,64,67,.3);flex:1;padding:72px 90px;font-family:Arial;font-size:15px;line-height:1.5;color:#000}
"""


@screen
def gdoc(st):
    title = st.get("title", "Untitled document")
    content = st.get("content", "")
    top = (f'<div class="top" style="height:64px;display:flex;align-items:center;gap:12px;padding:0 14px"><div style="width:28px;height:38px;background:#4285f4;border-radius:3px;color:#fff;'
           f'display:flex;align-items:center;justify-content:center">≡</div><div><div style="font-size:18px">{E(title)} ☆</div><div style="font-size:14px;color:#444;display:flex;gap:14px">'
           f'<span>File</span><span>Edit</span><span>View</span><span>Insert</span><span>Format</span><span>Tools</span><span>Extensions</span><span>Help</span></div></div>'
           f'<div style="margin-left:auto;background:#c2e7ff;border-radius:18px;height:40px;padding:0 22px;display:flex;align-items:center;font:500 14px Roboto">🔒 Share</div></div>'
           f'<div style="height:40px;margin:0 10px;border-radius:24px;background:#edf2fa;display:flex;align-items:center;gap:18px;padding:0 16px;color:#444;font-size:14px">'
           f'<span>🔍</span><span>↶</span><span>↷</span><span data-t="print">🖨</span><span>100% ▾</span><span>Normal text ▾</span><span>Arial ▾</span><span>— 11 +</span><span><b>B</b></span><span><i>I</i></span></div>')
    body = f'<style>{DOCS_CSS}</style><div class="gd">{top}<div class="paper" data-t="paper">{content}</div></div>'
    tabs = st.get("tabs", [(("#4285f4", "≡"), title + " - Google Docs")])
    page = chrome(tabs, st.get("active", 0), "docs.google.com/document/d/1sAmPLe-doc/edit", body)
    if st.get("print"):
        page += ('<div style="position:absolute;inset:0 0 48px 0;background:rgba(0,0,0,.5);z-index:20"></div><div style="position:absolute;left:90px;top:120px;width:1100px;height:900px;'
                 'background:#fff;border-radius:8px;z-index:21;display:flex;font-family:Roboto;overflow:hidden"><div style="flex:1;background:#525659;display:flex;justify-content:center;padding-top:30px">'
                 f'<div style="width:420px;height:544px;background:#fff;padding:40px;font:7px Arial">{content}</div></div><div style="width:380px;padding:24px;font-size:14px">'
                 '<div style="font-size:22px;margin-bottom:6px">Print</div><div style="color:#5f6368;margin-bottom:22px">2 sheets of paper</div>'
                 '<div style="display:flex;justify-content:space-between;margin-bottom:18px"><span>Destination</span><span style="border:1px solid #dadce0;border-radius:4px;padding:6px 10px" data-t="dest">🖨 Office Printer ▾</span></div>'
                 '<div style="display:flex;justify-content:space-between;margin-bottom:18px"><span>Pages</span><span>All ▾</span></div><div style="display:flex;justify-content:space-between;margin-bottom:18px"><span>Copies</span><span>1</span></div>'
                 '<div style="display:flex;justify-content:space-between"><span>Color</span><span>Color ▾</span></div>'
                 '<div style="position:absolute;right:24px;bottom:24px;display:flex;gap:10px"><span style="background:#1a73e8;color:#fff;border-radius:4px;padding:9px 22px" data-t="printbtn">Print</span>'
                 '<span style="border:1px solid #dadce0;border-radius:4px;padding:9px 18px;color:#1a73e8">Cancel</span></div></div></div>')
    return desk(st["clock"], page)


@screen
def sc_home(st):
    tiles = [("Pending", "10", "#0f1111"), ("Unshipped", "72", "#0f1111"), ("Late shipment risk", "1", "#b12704"), ("Buyer messages", "4", "#c45500"), ("Returns", "0", "#0f1111")]
    t = "".join(f'<div class="card" style="flex:1" data-t="tile{i}"><div style="font-size:13px;color:#565959">{a}</div><div style="font:600 40px Inter;color:{c};margin-top:4px">{b}</div>'
                f'<div class="lnk" style="font-size:12px;margin-top:4px">View ›</div></div>' for i, (a, b, c) in enumerate(tiles))
    body = (f'<div class="h1">Good afternoon</div><div style="display:flex;gap:12px">{t}</div><div style="display:flex;gap:12px;margin-top:14px">'
            f'<div class="card" style="flex:2;height:320px"><b>Today\'s sales</b><div style="font:600 30px Inter;margin:8px 0">$1,284.50</div>'
            f'<div style="display:flex;align-items:flex-end;gap:8px;height:200px">' + "".join(f'<div style="flex:1;height:{h}%;background:#7fc2cc;border-radius:3px 3px 0 0"></div>' for h in (10, 4, 8, 3, 6, 12, 25, 40, 52, 61, 44, 58, 70)) +
            '</div></div><div class="card" style="flex:1;height:320px"><b>Account Health</b><div style="font:600 30px Inter;color:#067d62;margin-top:8px">Healthy</div></div></div>')
    return desk(st["clock"], f"<style>{SC_CSS}</style>" + sc_page("Seller Central", "sellercentral.amazon.com/home", body))


@screen
def mail_msg(st):
    body = ('<div class="h1">Buyer-Seller Messages</div><div class="card" style="max-width:900px"><div style="font:600 18px Inter">Question about my invitations</div>'
            '<div style="font-size:12px;color:#565959;margin:6px 0 16px">Order 112-5559821-0045110 · Buyer: Lauren M.</div>'
            '<div style="background:#f0f2f2;border-radius:8px;padding:16px;font-size:15px;line-height:1.6" data-t="msg">Hi! I attached my guest list with all 50 addresses. '
            'Will you be addressing and mailing the invitations to each guest directly? I need them to arrive by the 15th. Thank you!!</div>'
            '<div style="margin-top:10px;font-size:13px">📎 guest_list_50_addresses.xlsx</div></div>')
    return desk(st["clock"], f"<style>{SC_CSS}</style>" + sc_page("Amazon", "sellercentral.amazon.com/messaging/thread/sample", body))


@screen
def indesign(st):
    m = st.get("mins", 0)
    body = (f'<div style="height:100%;background:#323232;color:#ddd;display:flex;flex-direction:column;font-family:Noto">'
            f'<div style="height:34px;background:#2b2b2b;display:flex;align-items:center;gap:16px;padding:0 12px;font-size:12px"><b style="background:#49021f;color:#ff3366;padding:2px 6px;border-radius:3px">Id</b>'
            f'File &nbsp; Edit &nbsp; Layout &nbsp; Type &nbsp; Object &nbsp; Table &nbsp; View &nbsp; Window &nbsp; Help</div>'
            f'<div style="height:30px;background:#2b2b2b;border-top:1px solid #222;display:flex;align-items:flex-end;padding-left:44px">'
            f'<div style="background:#323232;padding:6px 14px;font-size:12px;color:#eee" data-t="doctab">{"*" if st.get("dirty") else ""}7614 - SAMPLE ORDER B - 10 - FLD.indd @ 75% ✕</div></div>'
            f'<div style="flex:1;display:flex"><div style="width:44px;background:#2b2b2b;display:flex;flex-direction:column;align-items:center;gap:14px;padding-top:12px;font-size:15px">➤<br>▷<br>T<br>✎<br>▭<br>✂<br>✋<br>🔍</div>'
            f'<div style="flex:1;background:#535353;display:flex;align-items:center;justify-content:center"><div style="width:520px;height:720px;background:#fff;color:#7a5c3e;text-align:center;font-family:Serif4;padding-top:120px;position:relative">'
            f'<div style="font-size:14px;letter-spacing:4px">THE PLEASURE OF YOUR COMPANY</div><div style="font-size:52px;font-style:italic;margin:24px 0">Sarah &amp; Ben</div>'
            f'<div style="font-size:14px;letter-spacing:3px">SATURDAY, JUNE 6, 2027</div><div style="position:absolute;inset:30px;border:1px solid #c9a96e"></div></div></div>'
            f'<div style="width:240px;background:#2b2b2b;padding:10px;font-size:12px;line-height:2">Properties<br>Pages<br>Layers<br>Swatches<br>Character Styles</div></div></div>')
    w = '<div class="w" style="left:0;top:0;right:0;bottom:48px;border-radius:0">' + body + '</div>'
    if m:
        w += (f'<div style="position:absolute;right:30px;top:120px;background:#ff3b7f;color:#fff;border-radius:10px;padding:10px 16px;font:700 22px Inter;z-index:30" data-t="timer">'
              f'⚠ unsaved for {m} min</div>')
    return desk(st["clock"], w, on=("id",))


@screen
def sc_order(st):
    note = st.get("note", "")
    body = (f'<div class="h1">Order details</div><div style="font-size:13px;margin-bottom:14px">Order ID: <b>112-5550777-3300118</b> &nbsp;·&nbsp; Ship by: Oct 8, 2026</div>'
            f'<div style="display:flex;gap:14px"><div class="card" style="flex:1"><b>Ship to</b><div style="margin-top:6px;font-size:14px;line-height:1.5">Sample Customer<br>123 Example St<br>Springfield, IL 62701</div></div>'
            f'<div class="card" style="flex:1"><b>Order summary</b><div style="margin-top:6px;font-size:14px;line-height:1.7">Items total: $279.50<br>Shipping: $0.00<br><b>Grand total: $279.50</b></div></div></div>'
            f'<div class="card" style="margin-top:14px"><b>Seller notes</b><div style="border:1px solid #888c8c;border-radius:6px;padding:10px;margin-top:8px;min-height:60px;font-size:14px;'
            f'{"background:#fff8e1;font-weight:600" if note else "color:#6f7373"}" data-t="note">{E(note) or "Add a note"}</div><div style="font-size:12px;color:#565959;margin-top:6px">Seller notes are for your records only and will not be displayed to the buyer.</div><div style="margin-top:10px"><span class="ab y" data-t="savenote">Save note</span></div></div>'
            f'<div class="card" style="margin-top:14px"><table class="t"><tr><th>Product</th><th>Qty</th><th>Customization</th><th>Price</th></tr>'
            f'<tr><td>Custom Wedding Invitations, Set of 150 (WI-SAMPLE-22)</td><td>1</td><td><span class="lnk">View customization</span></td><td>$279.50</td></tr></table></div>')
    return desk(st["clock"], f"<style>{SC_CSS}</style>" + sc_page("Order details", "sellercentral.amazon.com/orders-v3/order/112-5550777-3300118", body))


GMAIL_CSS = """
.gm{height:100%;display:flex;flex-direction:column;font-family:Roboto;background:#f6f8fc}
.gm .top{height:64px;display:flex;align-items:center;gap:16px;padding:0 16px}
.gm .s{flex:1;max-width:720px;height:48px;border-radius:24px;background:#eaf1fb;display:flex;align-items:center;padding:0 18px;color:#444;font-size:16px}
.gm .nav{width:250px;padding:8px 10px;font-size:14px;color:#202124;flex:none}
.gm .nav div{height:32px;border-radius:0 16px 16px 0;display:flex;align-items:center;padding-left:24px}
.gm .nav .on{background:#d3e3fd;font-weight:700}
.gm .compose{width:140px;height:56px;border-radius:16px;background:#c2e7ff;display:flex;align-items:center;justify-content:center;font:500 14px Roboto;margin:8px 0 16px 0}
.gm .box{flex:1;background:#fff;border-radius:16px;margin-right:16px;overflow:hidden}
.gm .row{height:40px;display:flex;align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid #f1f3f4;font-size:14px;color:#202124}
.gm .row.u{font-weight:700;background:#fff}.gm .row.r{background:#f2f6fc}
.gm .row.sel{background:#c2dbff}
.gm .snack{position:absolute;left:24px;bottom:72px;background:#202124;color:#fff;border-radius:4px;padding:14px 20px;font-size:14px;z-index:30;display:flex;gap:30px}
"""


@screen
def gmail(st):
    rows = [("Etsy", "You made a sale!", "Order #3812 from sample shop…", 1), ("Shopify", "Payout sent", "$412.80 is on the way…", 0),
            ("Lauren M.", "Re: Proof for my invitations", "Can you change the font to…", 1), ("DYMO", "Your label order shipped", "Track your package…", 0),
            ("Google Drive", "1 file was shared with you", "Sample sheet…", 0), ("Amazon Seller", "Your weekly business update", "See what changed…", 0),
            ("Canva", "New templates for fall", "Get inspired…", 0), ("Sam B.", "Quick question about envelopes", "Hi! Do the envelopes come…", 1),
            ("UPS", "Delivery update", "Your package was delivered…", 0), ("PayPal", "Receipt for your payment", "You sent a payment…", 0)]
    gone = st.get("archived", 0)
    sel = st.get("sel", set())
    out = ""
    for i, (a, b, c, u) in enumerate(rows):
        if i in (1, 3, 4, 6, 8, 9)[:gone]:
            continue
        unread = u or (i == 2 and st.get("unread"))
        cls = "sel" if i in sel else ("u" if unread else "r")
        out += (f'<div class="row {cls}" data-t="r{i}"><span>☐ ☆</span><span style="width:180px">{a}</span><span>{b}</span>'
                f'<span style="color:#5f6368;font-weight:400">&nbsp;- {c}</span><span style="margin-left:auto;font-size:12px">Oct 2</span></div>')
    tb = ('<div style="height:48px;display:flex;align-items:center;gap:22px;padding:0 16px;color:#444;font-size:16px">☐ ▾ <span data-t="archive">🗃</span><span>⚠</span><span>🗑</span>'
          '<span data-t="markunread">✉</span><span>⏱</span><span style="margin-left:auto;font-size:13px">1–50 of 2,416</span></div>')
    body = (f'<style>{GMAIL_CSS}</style><div class="gm"><div class="top"><span style="font-size:20px">☰</span><b style="font:400 22px Roboto;color:#444">'
            f'<span style="color:#ea4335">M</span> Gmail</b><div class="s">🔍&nbsp; Search mail</div></div><div style="display:flex;flex:1"><div class="nav">'
            f'<div class="compose">✎ Compose</div><div class="on">📥 Inbox <span style="margin-left:auto;margin-right:12px">{38 - gone}</span></div><div>☆ Starred</div><div>⏱ Snoozed</div>'
            f'<div>➤ Sent</div><div>📄 Drafts</div></div><div class="box">{tb}{out}</div></div></div>')
    sn = f'<div class="snack">{st["snack"]}<span style="color:#8ab4f8">Undo</span></div>' if st.get("snack") else ""
    return desk(st["clock"], chrome([(("#ea4335", "M"), "Inbox (38) - shop@example.com - Gmail")], 0, "mail.google.com/mail/u/0/#inbox", body) + sn)


@screen
def spapi(st):
    body = ('<div class="h1">Develop Apps</div><div style="font-size:14px;color:#565959;margin-bottom:14px">Selling Partner API · Private developer</div>'
            '<div class="card"><table class="t"><tr><th>App name</th><th>App ID</th><th>Status</th><th>LWA credentials</th><th></th></tr>'
            '<tr><td><b>Shop Order Helper</b></td><td style="font-family:Mono;font-size:12px">amzn1.sp.solution.SAMPLE-0000</td><td><span class="pill" style="background:#e7f4f5;color:#007185">Draft</span></td>'
            '<td class="lnk">View</td><td><span class="ab y" data-t="saveapp">Save and exit</span></td></tr></table></div>'
            '<div class="card" style="margin-top:14px"><b>Your support cases</b><table class="t" style="margin-top:8px"><tr><th>Case ID</th><th>Subject</th><th>Status</th></tr>'
            '<tr data-t="case"><td>18877000000</td><td>Developer registration: role access</td><td><span class="pill" style="background:#fff3cd;color:#8a6d00">Pending Amazon action</span></td></tr></table></div>')
    return desk(st["clock"], f"<style>{SC_CSS}</style>" + sc_page("Developer Central", "sellercentral.amazon.com/sellingpartner/developerconsole", body))


@screen
def health(st):
    v = st.get("v", 770)
    ring = (f'<div style="width:260px;height:260px;border-radius:50%;background:conic-gradient(#067d62 0 {v / 10}%,#e3e6e6 0);display:flex;align-items:center;justify-content:center" data-t="ring">'
            f'<div style="width:200px;height:200px;border-radius:50%;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center">'
            f'<div style="font:700 54px Inter">{v}</div><div style="color:#565959;font-size:14px">out of 1,000</div></div></div>')
    body = (f'<div class="h1">Account Health</div><div style="display:flex;gap:16px"><div class="card" style="width:420px;display:flex;flex-direction:column;align-items:center;gap:14px">'
            f'<b style="align-self:flex-start">Supply chain performance</b>{ring}<span class="pill" style="background:#e7f4f5;color:#067d62">Good</span></div>'
            f'<div class="card" style="flex:1"><b>Shipping performance</b><table class="t" style="margin-top:10px"><tr><th>Metric</th><th>Target</th><th>Yours</th></tr>'
            f'<tr><td>Late shipment rate</td><td>&lt; 4%</td><td>0.6%</td></tr><tr><td>Pre-fulfillment cancel rate</td><td>&lt; 2.5%</td><td>0%</td></tr>'
            f'<tr><td>Valid tracking rate</td><td>&gt; 95%</td><td>99.4%</td></tr></table></div></div>')
    return desk(st["clock"], f"<style>{SC_CSS}</style>" + sc_page("Account Health", "sellercentral.amazon.com/performance/dashboard", body))


@screen
def lunch(st):
    bowl = ('<div style="width:360px;height:360px;border-radius:50%;background:radial-gradient(circle at 50% 50%,#fff 0 58%,#e9e4da 59% 64%,transparent 65%);position:relative">'
            + "".join(f'<div style="position:absolute;left:{x}px;top:{y}px;width:{s}px;height:{s}px;border-radius:50%;background:{c}"></div>'
                      for x, y, s, c in ((80, 90, 90, "#e9d7a8"), (170, 70, 100, "#7aa95c"), (110, 180, 90, "#c6463a"), (200, 170, 80, "#f1e3c2"), (150, 140, 60, "#8b5a3c"), (90, 140, 40, "#f7f2e6")))
            + '</div>')
    if st.get("cake"):
        inner = ('<div style="display:flex;gap:40px;padding:40px 60px;font-family:Inter"><div style="width:420px;height:420px;background:#fdf1f4;border-radius:12px;display:flex;align-items:center;justify-content:center">'
                 '<div style="width:280px;height:170px;border-radius:50%/30%;background:linear-gradient(#f7d4df,#e9a8bd);box-shadow:inset 0 -30px 0 #d98aa4;position:relative">'
                 '<div style="position:absolute;left:30px;right:30px;top:-6px;height:40px;border-radius:50%;background:#fff"></div></div></div>'
                 '<div><div style="font:600 30px Serif4">Birthday Bundt Cake</div><div style="color:#666;margin:8px 0">Strawberries &amp; Cream · 8" serves 8-10</div>'
                 '<div style="font:600 24px Inter;margin:14px 0">$38.95</div><div style="display:flex;gap:10px;margin-top:10px"><span style="border:2px solid #b21f4b;border-radius:24px;padding:10px 22px;color:#b21f4b">Add to cart</span></div>'
                 '<div style="margin-top:20px;color:#999">(she did not add it to cart)</div></div></div>')
        tab = "Birthday Cakes | Bakery"
        url = "bakery.example.com/birthday"
    else:
        inner = (f'<div style="display:flex;gap:40px;padding:40px 60px;font-family:Inter;align-items:center">{bowl}<div><div style="font:600 30px Inter">Your order is ready!</div>'
                 '<div style="color:#666;margin:10px 0;line-height:1.6">Greens + Grains bowl<br>Spicy hummus · chicken · pickled onions · feta</div><div style="font:600 22px Inter">$14.25</div></div></div>')
        tab = "Order status | Bowl"
        url = "order.example.com/status"
    return desk(st["clock"], chrome([(("#2e7d32", "🥗"), tab)], 0, url, inner))


@screen
def stats(st):
    return ""


# ------------------------------------------------------------------ render
def page_html(name, st):
    body = S[name](st)
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{font_css()}{BASE}</style></head><body>{body}</body></html>')


def render(out_dir, jobs):
    """jobs: [(key, screen_name, state)]. Writes key.png and key.json (data-t boxes in CSS px)."""
    from playwright.sync_api import sync_playwright
    os.makedirs(out_dir, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": VW, "height": VH}, device_scale_factor=DPR)
        for key, name, st in jobs:
            png = os.path.join(out_dir, key + ".png")
            if os.path.exists(png) and not os.environ.get("FORCE"):
                continue
            pg.set_content(page_html(name, st), wait_until="load")
            pg.evaluate("document.fonts.ready")
            boxes = pg.evaluate("""() => Object.fromEntries([...document.querySelectorAll('[data-t]')].map(e => {
                const r = e.getBoundingClientRect(); return [e.dataset.t, [r.x, r.y, r.width, r.height]]; }))""")
            boxes["_content"] = pg.evaluate("""() => { let a = [1e9, 1e9, -1e9, -1e9];
                for (const e of document.querySelectorAll('.w,.ch,.as,.toast,.tip')) { const r = e.getBoundingClientRect();
                  a = [Math.min(a[0], r.x), Math.min(a[1], r.y), Math.max(a[2], r.right), Math.max(a[3], r.bottom)]; }
                return [a[0], a[1], a[2] - a[0], a[3] - a[1]]; }""")
            pg.screenshot(path=png)
            json.dump(boxes, open(os.path.join(out_dir, key + ".json"), "w"))
        b.close()


if __name__ == "__main__":
    from oct2_long_plan import screen_jobs
    jobs = screen_jobs()
    if len(sys.argv) > 2:
        jobs = [j for j in jobs if j[0] in sys.argv[2:] or j[1] in sys.argv[2:]]
    render(sys.argv[1], jobs)
