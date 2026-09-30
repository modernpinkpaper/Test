"""Script: "things to say at work (from the comments)" - lines from the comments under @careeralbert's TikTok about
funny things to say at work, each acted out as a short office scene: something happens -> the line -> a (non-laughing)
reaction. (key, who, line); who = a Kokoro voice used as the Chatterbox reference (synthetic voices, no real person).
"""
WORKER, COWORKER, BOSS = "af_sarah", "am_eric", "am_michael"
VOICE = WORKER
CREDIT = "lines from the comments on @careeralbert"

LINES = [
    # 1. Monday, 8:45 AM
    ("friday", WORKER, "[excited] Morning, everyone! Nearly Friday!"),
    # 2. 347 unread emails
    ("fanmail", WORKER, "[sassy] Just gonna check my fan mail."),
    # 3. sign this form
    ("sign_q", COWORKER, "[neutral] Can you sign this real quick?"),
    ("sign_a", WORKER, "[sassy] Anything for a fan."),
    # 4. trips over a cable
    ("trip", WORKER, "[annoyed] Have that removed. Immediately."),
    # 5. coworker sneezes twice
    ("sneeze", COWORKER, "[neutral] Achoo! Achoo!"),
    ("sneeze_a", WORKER, "[calm] You're still coming to work tomorrow."),
    # 6. nobody answers
    ("wifi", WORKER, "[neutral] Does anyone know the Wi-Fi password?"),
    ("secrets", WORKER, "[sassy] Okay. Keep your secrets."),
    # 7. fixes the printer
    ("bucks", WORKER, "[sassy] That's why they pay me the medium bucks."),
    # 8. deadline moved
    ("deadline", BOSS, "[neutral] We're moving your deadline up to tomorrow."),
    ("allow", WORKER, "[calm] Hmm. I'll allow it."),
    # 9. total chaos
    ("fun", WORKER, "[calm] The important thing is, we're having fun."),
    # 10. end of the day
    ("thanks", WORKER, "[fake] Thank you all for coming!"),
]
