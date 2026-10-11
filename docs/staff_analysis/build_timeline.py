"""Turn one PC's MT Log JSONL files into a readable timeline, one event per line.

    python build_timeline.py <LOG_FOLDER> <PCID> timeline.txt

Reads every <LOG_FOLDER>/*_<PCID>.jsonl, drops duplicate events, sorts by time and writes lines like
APP / WEB / CLK / FLD / PRINT / PRINTDONE / FILE_* / IDLE_* / WATCHER_*. See STAFF_DAILY_ANALYSIS.md.
"""
import sys,json,glob
U=sys.argv.pop(1).rstrip('/')+'/'
ev=[]
for f in glob.glob(U+'*_%s.jsonl'%sys.argv[1]):
    for l in open(f):
        try: ev.append(json.loads(l))
        except: pass
ev.sort(key=lambda e:(e['timestamp_utc'],e.get('sequence') or 0))
seen=set(); out=[]
for e in ev:
    if e['event_id'] in seen: continue
    seen.add(e['event_id'])
    t=e['timestamp_local'][11:19]; ty=e['event_type']; m=e.get('metadata') or {}
    s=None
    if ty=='app_session_end':
        s=f"APP {e.get('application')} | {e.get('window_title')} | {m.get('duration_seconds',m.get('active_seconds'))}s act{m.get('active_seconds')}"
        t=(m.get('session_start') or e['timestamp_local'])[11:19]
    elif ty=='browser_page':
        s=f"WEB {m.get('site')}/{m.get('page_type')} | {e.get('page_title')} | {(e.get('url') or '')[:110]} | {m.get('order_ids') or ''} {m.get('headings') or ''} {m.get('search_term') or ''}"
    elif ty=='ui_action':
        s=f"CLK '{m.get('name')}' {m.get('action')} @ {(e.get('window_title') or '')[:60]}"
    elif ty=='ui_field_value':
        s=f"FLD '{m.get('label')}' = '{m.get('value')}' @ {(e.get('window_title') or '')[:50]}"
    elif ty=='print_job':
        s=f"PRINT {m.get('document_name')} | {m.get('printer')} | pages {m.get('total_pages')} | {m.get('job_status')} {m.get('status')}"
    elif ty=='print_job_finished':
        s=f"PRINTDONE {m.get('document_name')} | {m.get('printer')} | printed {m.get('pages_printed')} | {m.get('status')} {m.get('job_status')} {m.get('error') or ''}"
    elif ty.startswith('file_') or ty=='upload_file_selected':
        s=f"{ty.upper()} {m.get('path') or m.get('files')}"
    elif ty in ('idle_start','idle_end','watcher_stopped','watcher_started','system_resume','workstation_unlocked','workstation_locked','system_suspend'):
        s=f"{ty.upper()} {json.dumps(m)[:160]}"
    elif ty in ('process_started',) and m.get('has_window'):
        s=f"PROC+ {e.get('process_name')} {e.get('application')}"
    if s: out.append((t,s))
out.sort(key=lambda x:x[0])
open(sys.argv[2],'w').write('\n'.join(f"{a} {b}"[:260] for a,b in out))
print(len(out))
