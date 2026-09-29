"""Voices for the skits.

    her  = Chatterbox clone of her own voice (demo_videos/voices/my-voice-ref.wav, private)
    other people = Kokoro built-in voices (belong to no real person), e.g. "am_michael", "af_heart"

Tone tags at the start of a line pick the delivery, e.g. "[sassy] Mmhmm. Where are you?".
Without a tag the tone is guessed from punctuation (!, ?, ...). Each tone maps to Chatterbox settings
(exaggeration = how dramatic, cfg = steadiness/pace) or to a Kokoro speed.
Every line is cached on disk, so re-renders are instant.
"""
import hashlib
import os
import re
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "chibi", ".cache", "voices")
HER_REF = os.path.join(HERE, "..", "demo_videos", "voices", "my-voice-ref.wav")
SR = 24000

TONES = {           # tone: (chatterbox exaggeration, cfg_weight, kokoro speed)
    "calm":     (0.45, 0.55, 0.95),
    "neutral":  (0.55, 0.50, 1.00),
    "sassy":    (0.85, 0.35, 1.00),     # = the settings of her favourite test (my_voice_test)
    "annoyed":  (0.80, 0.40, 1.05),
    "excited":  (0.95, 0.32, 1.12),
    "shocked":  (0.90, 0.30, 1.10),
    "whisper":  (0.40, 0.60, 0.90),
    "sheepish": (0.50, 0.50, 0.92),
    "fake":     (0.95, 0.35, 1.10),     # over-the-top fake cheerful
}


def split_tag(line):
    m = re.match(r"\s*\[(\w+)\]\s*(.*)", line)
    if m and m.group(1).lower() in TONES:
        return m.group(1).lower(), m.group(2)
    t = line.strip()
    if t.count("!") >= 1:
        return "excited", t
    if "..." in t or "…" in t:
        return "sassy", t
    return "neutral", t


_cb = _kp = None  # loaded on first use


REF_TEXT = ("So I was thinking about it on the way over here, and honestly, it's been a really long week. "
            "Work was crazy, the car's making that noise again, and I still haven't called my mom back. "
            "Anyway, I'm here now. What did I miss? Did you order already? Because I am starving.")


def ref_for(who):
    """Reference recording for a speaker: hers, or ~20 s of a Kokoro built-in voice (a synthetic voice that
    belongs to no real person), so Chatterbox can give every character the same emotion controls."""
    global _kp
    if who == "her":
        return HER_REF
    path = os.path.join(CACHE, f"ref_{who}.wav")
    if not os.path.exists(path):
        if _kp is None:
            from kokoro import KPipeline
            _kp = KPipeline(lang_code="a")
        a = np.concatenate([x.numpy() for _, _, x in _kp(REF_TEXT, voice=who, speed=1.0)])
        sf.write(path, a.astype(np.float32), SR)
    return path


def say(who, line):
    """who: 'her' or a Kokoro voice name (used as a synthetic reference). Returns float32 audio at 24 kHz."""
    global _cb
    tone, text = split_tag(line)
    ex, cfg, speed = TONES[tone]
    os.makedirs(CACHE, exist_ok=True)
    ref = ref_for(who)
    tag = f"cb3|{who}|{tone}|{ex}|{cfg}|{text}|{os.path.getsize(ref)}"
    path = os.path.join(CACHE, hashlib.md5(tag.encode()).hexdigest() + ".wav")
    if not os.path.exists(path):
        import torchaudio
        if _cb is None:
            from chatterbox.tts import ChatterboxTTS
            _cb = ChatterboxTTS.from_pretrained(device="cpu")
        w = _cb.generate(text, audio_prompt_path=ref, exaggeration=ex, cfg_weight=cfg)
        a = torchaudio.functional.resample(w, _cb.sr, SR).squeeze(0).numpy()
        if tone == "whisper":
            a = a * 0.6
        a = a.astype(np.float32)
        nz = np.where(np.abs(a) > 0.01)[0]
        a = a[max(nz[0] - 240, 0):nz[-1] + 2400] if len(nz) else a
        sf.write(path, a, SR)
    return sf.read(path, dtype="float32")[0]


def clarity(a):
    """Keep the voice untouched (her favourite test had no processing): only remove rumble and level the whole
    track to about -16 dBFS speech loudness, with a peak ceiling. No compression, EQ or limiter colour."""
    import scipy.signal as ss
    b, c = ss.butter(2, 60 / (SR / 2), "high")
    a = ss.filtfilt(b, c, a)
    speech = np.abs(a) > 0.02 * np.abs(a).max()
    rms = np.sqrt(np.mean(a[speech] ** 2)) if speech.any() else 1e-6
    a = a * (10 ** (-16 / 20) / rms)
    peak = np.abs(a).max()
    return (a * (0.97 / peak) if peak > 0.97 else a).astype(np.float32)


def gate(a, floor_db=-20.0):
    """Quiet the gaps between words (where the voice model leaves faint noise) before anything boosts them."""
    env = np.sqrt(np.convolve(a ** 2, np.ones(720) / 720, "same"))                # 30 ms loudness
    thr = 0.06 * np.percentile(env, 98)
    g = np.where(env > thr, 1.0, 10 ** (floor_db / 20))
    g = np.convolve(g, np.ones(480) / 480, "same")                                  # 20 ms fades, no clicks
    return (a * g).astype(np.float32)


def room(a, amount=0.03):
    """A little room echo (a few soft early reflections, no noise), so lines don't sound studio-dry."""
    ir = np.zeros(int(0.09 * SR), np.float32)
    ir[0] = 1.0
    for d, k in ((0.011, .5), (0.019, .35), (0.031, .25), (0.047, .15), (0.071, .08)):
        ir[int(d * SR)] += k * amount / .05 * .3
    return np.convolve(a, ir)[:len(a) + len(ir) // 2].astype(np.float32)


def conversation(lines, gap=0.25, overlap=None):
    """lines: [(who, text), ...] -> one clean, level track (the skit adds its own room sound per scene)."""
    out = []
    for who, text in lines:
        out += [room(gate(say(who, text))), np.zeros(int(gap * SR), np.float32)]
    return clarity(np.concatenate(out))


if __name__ == "__main__":
    demo = [("her", "[sassy] Mmhmm. Where are you?"),
            ("am_michael", "[fake] Heyyy! I'm literally five minutes away!"),
            ("her", "[sassy] Five minutes. Okay. 'Cause I can hear your fan."),
            ("am_michael", "[sheepish] That's... the car. It's a very windy car."),
            ("her", "[annoyed] Babe. You're brushing your teeth."),
            ("am_michael", "[sheepish] Hmm... I'm chewing gum."),
            ("her", "[shocked] Ooooh. Okay. So we're lying now!")]
    sf.write(sys.argv[1] if len(sys.argv) > 1 else "conversation.wav", conversation(demo), SR)
