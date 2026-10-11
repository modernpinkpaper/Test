"""Script for "your little treats vs. your retirement" (money data reveal). Her voice (skits/voices.py tone tags).

Each item: (label, monthly $, quip line). The 30-year value is computed in treats.py
(monthly amount invested at 7%/yr, compounded monthly, 30 years).
"""
HOOK = "[sassy] You're not broke, you're just really generous. To DoorDash."
SETUP = "[neutral] Here's what your little treats are worth in thirty years if you invested them instead, so guess number one before I show it."
ITEMS = [   # rank 10 -> 1
    ("Streaming apps you forgot", 45, "[sassy] Number ten, the streaming apps you forgot you have. That's fifty-five thousand dollars."),
    ("The gym you \"go to\"", 50, "[sassy] Nine, the gym you 'go to', sixty-one thousand."),
    ("New phone every year", 100, "[annoyed] Eight, a new phone every year. A hundred and twenty-two thousand, for a slightly better camera."),
    ("Lashes every 2 weeks", 120, "[sassy] Seven, lashes every two weeks. A hundred and forty-six thousand, blink twice if you're okay."),
    ("\"I deserve this\" carts", 150, "[sassy] Six, the online 'I deserve this' cart, a hundred and eighty-three thousand."),
    ("$6 iced coffee, daily", 180, "[sassy] Five, your daily six dollar iced coffee. Two hundred and twenty thousand, oat milk extra."),
    ("Brunch every weekend", 200, "[excited] Four, brunch every weekend. Two hundred and forty-four thousand, mimosas included!"),
    ("Target run \"for toothpaste\"", 300, "[annoyed] Three, the Target run 'just for toothpaste', three hundred and sixty-six thousand."),
    ("DoorDash twice a week", 560, "[sassy] Two, DoorDash twice a week. Six hundred and eighty-three thousand, and the driver thanks you."),
    ("Your car payment", 750, "[shocked] And number one? Your car payment. Nine hundred and fifteen thousand dollars, you're driving a house!"),
]
OUTRO = "[sassy] Invest the difference, not the whole vibe. So which one hurt? Tell me in the comments."
LINES = [HOOK, SETUP] + [q for _, _, q in ITEMS] + [OUTRO]

if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skits"))
    import voices
    for line in LINES:
        a = voices.say("her", line)
        print(round(len(a) / voices.SR, 2), line[:60], flush=True)
