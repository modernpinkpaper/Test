"""Transcribe every generated line and compare with the script; lines that lost words are re-generated.

    python money/check_lines.py                  # treats_lines, her voice
    python money/check_lines.py roth_lines       # any *_lines module (uses its VOICE if it has one)
"""
import hashlib, os, re, sys, difflib, importlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skits"))
import voices
mod = importlib.import_module(sys.argv[1] if len(sys.argv) > 1 else "treats_lines")
WHO = getattr(mod, "VOICE", "her")
LINES = [x[1] if isinstance(x, tuple) else x for x in mod.LINES]
from faster_whisper import WhisperModel
import soundfile as sf
CHK = os.path.join(voices.CACHE, "_chk.wav")
m = WhisperModel("small", device="cpu", compute_type="int8")
from num2words import num2words


def norm(s):
    """Lower-case words only; digits spelled out (Whisper writes 183,000 where the script says the words)."""
    s = re.sub(r"(\d),(\d)", r"\1\2", s.replace("$", ""))
    s = re.sub(r"\d+", lambda m: " " + num2words(int(m.group())) + " ", s)
    return re.sub(r"[^a-z ]", " ", s.lower().replace("-", " ").replace(" and ", " "))
for attempt in range(3):
    bad = []
    for line in LINES:
        tone, text = voices.split_tag(line)
        a = voices.say(WHO, line)
        sf.write(CHK, a, voices.SR)
        heard = " ".join(s.text for s in m.transcribe(CHK)[0])
        r = difflib.SequenceMatcher(None, norm(text).split(), norm(heard).split()).ratio()
        print(f"{r:.2f} | {text[:50]} | heard: {heard.strip()[:60]}", flush=True)
        if r < 0.8:
            bad.append(line)
    if not bad:
        break
    for line in bad:               # delete the cached take so it's generated again
        tone, text = voices.split_tag(line)
        ex, cfg, _ = voices.TONES[tone]
        tag = f"cb3|{WHO}|{tone}|{ex}|{cfg}|{text}|{os.path.getsize(voices.ref_for(WHO))}"
        os.remove(os.path.join(voices.CACHE, hashlib.md5(tag.encode()).hexdigest() + ".wav"))
        print("retry:", text[:50], flush=True)
