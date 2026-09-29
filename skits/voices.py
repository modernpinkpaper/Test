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


_cb = _kp = None


def say(who, line):
    """who: 'her' or a Kokoro voice name. Returns float32 audio at 24 kHz."""
    global _cb, _kp
    tone, text = split_tag(line)
    ex, cfg, speed = TONES[tone]
    os.makedirs(CACHE, exist_ok=True)
    tag = f"{who}|{tone}|{text}|{os.path.getsize(HER_REF) if who == 'her' else ''}"
    path = os.path.join(CACHE, hashlib.md5(tag.encode()).hexdigest() + ".wav")
    if not os.path.exists(path):
        if who == "her":
            import torchaudio
            if _cb is None:
                from chatterbox.tts import ChatterboxTTS
                _cb = ChatterboxTTS.from_pretrained(device="cpu")
            w = _cb.generate(text, audio_prompt_path=HER_REF, exaggeration=ex, cfg_weight=cfg)
            a = torchaudio.functional.resample(w, _cb.sr, SR).squeeze(0).numpy()
        else:
            if _kp is None:
                from kokoro import KPipeline
                _kp = KPipeline(lang_code="a")
            a = np.concatenate([x.numpy() for _, _, x in _kp(text, voice=who, speed=speed)])
            if tone == "whisper":
                a = a * 0.6
        a = a.astype(np.float32)
        nz = np.where(np.abs(a) > 0.01)[0]
        a = a[max(nz[0] - 240, 0):nz[-1] + 2400] if len(nz) else a
        sf.write(path, a, SR)
    return sf.read(path, dtype="float32")[0]


def room(a, amount=0.12):
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
    a = np.concatenate(out)
    a += np.random.default_rng(1).normal(0, 0.002, len(a)).astype(np.float32)
    return a / max(np.abs(a).max(), 1e-6) * 0.9


if __name__ == "__main__":
    demo = [("her", "[sassy] Mmhmm. Where are you?"),
            ("am_michael", "[fake] Heyyy! I'm literally five minutes away!"),
            ("her", "[sassy] Five minutes. Okay. 'Cause I can hear your fan."),
            ("am_michael", "[sheepish] That's... the car. It's a very windy car."),
            ("her", "[annoyed] Babe. You're brushing your teeth."),
            ("am_michael", "[sheepish] Hmm... I'm chewing gum."),
            ("her", "[shocked] Ooooh. Okay. So we're lying now!")]
    sf.write(sys.argv[1] if len(sys.argv) > 1 else "conversation.wav", conversation(demo), SR)
