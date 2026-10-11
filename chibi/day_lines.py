"""Script for "a day in my life (as a cartoon)": her chibi girl does normal day stuff. (key, who, line).

who: "her" = VOICE (a Kokoro built-in voice, belongs to no real person) or another Kokoro voice for the caller.
"""
VOICE = "af_bella"
CALLER = "af_nicole"

LINES = [
    ("wake", "her", "[annoyed] Ugh. Seven AM. Who approved this?"),
    ("stretch", "her", "[calm] Okay. Stretch. Pretend you're a morning person."),
    ("brush", "her", "[sassy] Brushing my teeth like the dentist is watching."),
    ("coffee", "her", "[sassy] Coffee first. Personality later."),
    ("donut", "her", "[sassy] Breakfast of champions. It's a donut. Don't judge me."),
    ("caller", CALLER, "[excited] Girl! Check your bank app. Payday hit!"),
    ("wait", "her", "[shocked] Wait. Payday?"),
    ("payday", "her", "[excited] It's payday!"),
    ("walk", "her", "[sassy] Walking to work like I'm in a music video."),
    ("meeting", "her", "[annoyed] This meeting could have been an email."),
    ("love", "her", "[fake] Love that for us."),
    ("where", "her", "[shocked] Wait. Where did my paycheck go?"),
    ("target", "her", "[sassy] Oh. Right. Target."),
    ("bed", "her", "[calm] Okay. In bed by ten. Very responsible."),
    ("twoam", "her", "[sheepish] It's two AM."),
    ("outro", "her", "[sassy] Same time tomorrow. Follow for more of my very real cartoon life."),
]

if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skits"))
    import voices
    for _, who, line in LINES:
        a = voices.say(VOICE if who == "her" else who, line)
        print(round(len(a) / voices.SR, 2), line[:60], flush=True)
