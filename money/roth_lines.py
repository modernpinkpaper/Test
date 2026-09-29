"""Script for "Roth IRA or Traditional IRA?" (money explainer). Voice: VOICE (skits/voices.py tone tags).

Each line: (key, line). The key picks the graphic in roth.py. Numbers are for 2026 (IRS): IRA limit $7,500 a year
across all your IRAs ($1,100 extra at 50+); Roth income phase-out starts at $153,000 single / $242,000 married.
"""
VOICE = "af_bella"      # a Kokoro built-in voice (belongs to no real person), used as the Chatterbox reference

LINES = [
    ("hook", "[sassy] Roth IRA or traditional IRA? Pick wrong and you're basically tipping the IRS. For thirty years."),
    ("one", "[calm] Okay, here's the whole thing in one sentence. You pay the tax now, or you pay it later."),
    ("trad", "[sassy] Traditional gives you a tax break today. Cute. But when you retire, the IRS is waiting with its hand out."),
    ("roth", "[excited] Roth, you pay the tax now, and everything you take out later is tax free. Even the growth!"),
    ("secret", "[sassy] And here's what nobody tells you. If your tax rate is the same now and later, they come out exactly the same."),
    ("math", "[neutral] Ten thousand dollars grows eight times. Tax it now or tax it later, you keep sixty two thousand four hundred either way."),
    ("question", "[calm] So the only real question is, will your tax rate be higher now, or later?"),
    ("roth_win", "[excited] Young, just starting out, or not making big money yet? Roth is usually your girl. Your tax rate is probably the lowest it'll ever be."),
    ("trad_win", "[calm] Making the most you'll ever make, and expecting less in retirement? Traditional can win. Take the break while your bracket is high."),
    ("perks", "[sassy] Bonus Roth perks. You can take out what you put in, anytime, no penalty. Just not the growth. And nobody forces you to withdraw when you're old."),
    ("catch", "[annoyed] The catch? If you earn too much, around a hundred and fifty thousand if you're single, you can't put money straight into a Roth."),
    ("limit", "[neutral] And for twenty twenty six, you can put in up to seven thousand five hundred dollars a year, total, across both."),
    ("outro", "[sassy] Still can't pick? Split it and do a little of both. Follow for more money stuff your parents never explained. Not financial advice, I'm literally a cartoon."),
]

if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skits"))
    import voices
    for _, line in LINES:
        a = voices.say(VOICE, line)
        print(round(len(a) / voices.SR, 2), line[:60], flush=True)
