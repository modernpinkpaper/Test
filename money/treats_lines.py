"""Script for "your little treats vs. your retirement" (money data reveal). Her voice (skits/voices.py tone tags).

Each item: (label, monthly $, quip line). The 30-year value is computed in treats.py
(monthly amount invested at 7%/yr, compounded monthly, 30 years).
"""
HOOK = "[sassy] You're not broke. You're just... really generous. To DoorDash."
SETUP = ("[neutral] Here's what your little treats would be worth in thirty years, if you invested them instead. "
         "Guess number one before I show it.")
ITEMS = [   # rank 10 -> 1
    ("Streaming apps you forgot", 45, "[sassy] Number ten. Streaming apps you forgot you have. Fifty-five thousand dollars."),
    ("The gym you \"go to\"", 50, "[sassy] Nine. The gym you 'go to'. Sixty-one thousand."),
    ("New phone every year", 100, "[annoyed] Eight. A new phone every year. A hundred and twenty-two thousand. For a slightly better camera."),
    ("Lashes every 2 weeks", 120, "[sassy] Seven. Lashes every two weeks. A hundred and forty-six thousand. Blink twice if you're okay."),
    ("\"I deserve this\" carts", 150, "[sassy] Six. The online 'I deserve this' cart. A hundred and eighty-three thousand."),
    ("$6 iced coffee, daily", 180, "[sassy] Five. Your daily six dollar iced coffee. Two hundred and twenty thousand. Oat milk extra."),
    ("Brunch every weekend", 200, "[excited] Four. Brunch every weekend. Two hundred and forty-four thousand. Mimosas included!"),
    ("Target run \"for toothpaste\"", 300, "[annoyed] Three. The Target run 'just for toothpaste'. Three hundred and sixty-six thousand."),
    ("DoorDash twice a week", 560, "[sassy] Two. DoorDash, twice a week. Six hundred and eighty-three thousand. The driver thanks you."),
    ("Your car payment", 750, "[shocked] And number one... your car payment. Nine hundred and fifteen thousand dollars. You're driving a house!"),
]
OUTRO = "[sassy] Invest the difference, not the whole vibe. Which one hurt? Tell me in the comments."
LINES = [HOOK, SETUP] + [q for _, _, q in ITEMS] + [OUTRO]

if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skits"))
    import voices
    for line in LINES:
        a = voices.say("her", line)
        print(round(len(a) / voices.SR, 2), line[:60], flush=True)
