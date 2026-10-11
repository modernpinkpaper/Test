"""Dialogue for the "I'm 5 minutes away" skit (original script). HER = her cloned voice; JAY = a Chatterbox voice
made from a Kokoro built-in voice (no real person)."""
HER, JAY = "her", "am_michael"
LINES = [
    (HER, "[sassy] Mmhmm. Okay. So where are you?"),
    (JAY, "[fake] Heyyy! I'm literally five minutes away!"),
    (HER, "[sassy] Five minutes. Okay. 'Cause I can hear your fan."),
    (JAY, "[sheepish] That's... the car. It's a very windy car."),
    (HER, "[annoyed] Babe. Why does it sound like you're brushing your teeth?"),
    (JAY, "[sheepish] Hmm... I'm chewing gum."),
    (HER, "[annoyed] Ugh. Twenty-five minutes. Unbelievable."),
    (JAY, "[excited] Okay, okay! I'm pulling in!"),
    (HER, "[sassy] Pulling in... to what? Your driveway?"),
    (JAY, "[excited] Traffic was insane!"),
    (HER, "[sassy] Mmm. Your shirt's inside out. And you have one shoe on."),
    (JAY, "[sheepish] It's... a trend."),
    (HER, "[annoyed] Sit. You're paying."),
    (JAY, "[sheepish] Hmm. About that... my wallet's five minutes away."),
    (HER, "[shocked] Oh my God!"),
]

if __name__ == "__main__":
    import voices
    for who, line in LINES:
        a = voices.say(who, line)
        print(who, round(len(a) / voices.SR, 2), line, flush=True)
