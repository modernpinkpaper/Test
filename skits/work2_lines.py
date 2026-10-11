"""Script v2 of "things to say at work": 8 jokes from the comments on @careeralbert's post, each with a setup, the
line, a reaction (never laughing) and a button. (key, who, line); voices are Kokoro voices used as Chatterbox
references (synthetic, no real person).
"""
WORKER, COWORKER, COWORKER2, BOSS = "af_sarah", "am_eric", "af_nicole", "am_michael"
VOICE = WORKER

LINES = [
    ("friday", WORKER, "[excited] Morning, everyone! Nearly Friday!"),
    ("huh", COWORKER, "[neutral] Huh?"),
    ("monday", COWORKER2, "[annoyed] It's Monday."),
    ("fanmail", WORKER, "[sassy] Just gonna check my fan mail."),
    ("trip", WORKER, "[annoyed] Have that removed. Immediately."),
    ("sneeze", COWORKER, "[neutral] Achoo! Achoo!"),
    ("sneeze_a", WORKER, "[calm] You're still coming to work tomorrow."),
    ("tiny", COWORKER, "[sheepish] achoo."),
    ("wifi", WORKER, "[neutral] Does anyone know the Wi-Fi password?"),
    ("secrets", WORKER, "[sassy] Okay. Keep your secrets."),
    ("comeon", COWORKER, "[annoyed] Come on, come on!"),
    ("bucks", WORKER, "[sassy] That's why they pay me the medium bucks."),
    ("deadline", BOSS, "[neutral] We're moving your deadline up to tomorrow."),
    ("allow", WORKER, "[calm] Hmm. I'll allow it."),
    ("fun", WORKER, "[calm] The important thing is, we're having fun."),
]
