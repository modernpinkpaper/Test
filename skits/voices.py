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
    "sassy":    (0.85, 0.35, 1.00),
    "annoyed":  (0.80, 0.40, 1.05),
    "excited":  (1.00, 0.30, 1.12),
    "shocked":  (1.10, 0.30, 1.10),
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
    tag = f"cb2|{who}|{tone}|{text}|{os.path.getsize(ref)}"
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
    """Easier to understand on a phone: cut rumble, lift the 'presence' range (2-5 kHz) a little,
    even out loud and quiet syllables (gentle compression), then level to about -14 LUFS (TikTok loudness)."""
    import scipy.signal as ss
    b, c = ss.butter(2, 90 / (SR / 2), "high")
    a = ss.filtfilt(b, c, a)
    b, c = ss.butter(2, [2000 / (SR / 2), 5000 / (SR / 2)], "band")
    a = a + 0.35 * ss.filtfilt(b, c, a)
    env = np.sqrt(np.convolve(a ** 2, np.ones(480) / 480, "same")) + 1e-6       # 20 ms loudness
    thr = np.percentile(env, 70)
    gain = np.where(env > thr, (thr / env) ** 0.45, 1.0)                        # ~ 1.8:1 above the threshold
    a = a * np.convolve(gain, np.ones(240) / 240, "same")
    speech = np.abs(a) > 0.02 * np.abs(a).max()
    rms = np.sqrt(np.mean(a[speech] ** 2)) if speech.any() else 1e-6
    a = a * (10 ** (-14 / 20) / rms) * 0.95                                     # speech RMS ~ -14 dBFS
    return np.tanh(a * 1.1).astype(np.float32) / np.tanh(1.1)                   # soft limiter, no clipping


def room(a, amount=0.06):
    """A little room echo so lines sound recorded in the same place, not studio-dry."""
    ir = np.zeros(int(0.25 * SR), np.float32)
    rng = np.random.default_rng(3)
    t = np.arange(len(ir)) / SR
    ir[:] = rng.normal(0, 1, len(ir)) * np.exp(-t / 0.05) * amount
    ir[0] = 1.0
    return np.convolve(a, ir)[:len(a) + len(ir) // 2].astype(np.float32)


def conversation(lines, gap=0.25, overlap=None):
    """lines: [(who, text), ...] -> one track; small gaps, room tone, a faint background hiss."""
    out = []
    for who, text in lines:
        out += [room(say(who, text)), np.zeros(int(gap * SR), np.float32)]
    a = clarity(np.concatenate(out))
    return a + np.random.default_rng(1).normal(0, 0.0015, len(a)).astype(np.float32)


if __name__ == "__main__":
    demo = [("her", "[sassy] Mmhmm. Where are you?"),
            ("am_michael", "[fake] Heyyy! I'm literally five minutes away!"),
            ("her", "[sassy] Five minutes. Okay. 'Cause I can hear your fan."),
            ("am_michael", "[sheepish] That's... the car. It's a very windy car."),
            ("her", "[annoyed] Babe. You're brushing your teeth."),
            ("am_michael", "[sheepish] Hmm... I'm chewing gum."),
            ("her", "[shocked] Ooooh. Okay. So we're lying now!")]
    sf.write(sys.argv[1] if len(sys.argv) > 1 else "conversation.wav", conversation(demo), SR)
