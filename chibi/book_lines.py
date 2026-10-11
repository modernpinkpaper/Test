"""Script: book review of "The Psychology of Money" (Morgan Housel, 2020). Lessons are summarized in our own words.

(key, who, line); who "her" = VOICE. The Buffett figure is the one the book gives ($81.5B of his $84.5B net worth
came after his 65th birthday).
"""
VOICE = "af_bella"
TITLE, AUTHOR = "The Psychology of Money", "Morgan Housel"
COVER_ISBN = "9780857197689"

LINES = [
    ("hook", "her", "[sassy] This book made me feel personally attacked. In a good way."),
    ("intro", "her", "[neutral] The Psychology of Money, by Morgan Housel. Here are five lessons that live in my head rent free."),
    ("l1", "her", "[calm] One. Nobody's crazy with money. We all just learned it differently, from what we lived through."),
    ("l2", "her", "[shocked] Two. Almost all of Warren Buffett's fortune came after his sixty fifth birthday. The secret isn't genius. It's time."),
    ("l3", "her", "[sassy] Three. Wealth is what you don't see. That fancy car only proves you have less money now."),
    ("l4", "her", "[annoyed] Four. Enough is a real number. If you keep moving the goalpost, you never get to win."),
    ("l5", "her", "[excited] Five. Save for no reason at all. Savings is your freedom fund, for the stuff nobody can predict."),
    ("verdict", "her", "[sassy] My rating? Ten out of ten. Read it before you buy another car."),
    ("outro", "her", "[sassy] Follow for more books I read so you don't have to. And tell me what I should read next."),
]
CARDS = {   # key: (big label, title, small line)
    "intro": ("5", "lessons that live in my head rent free", "The Psychology of Money · Morgan Housel"),
    "l1": ("1", "Nobody's crazy with money", "we all learned it from what we lived through"),
    "l2": ("2", "$81.5B of Buffett's $84.5B came after age 65", "(the book's numbers) · compounding needs TIME"),
    "l3": ("3", "Wealth is what you DON'T see", "the fancy car = money that's gone"),
    "l4": ("4", "\"Enough\" is a real number", "stop moving the goalpost"),
    "l5": ("5", "Save for no reason at all", "savings = your freedom fund"),
    "verdict": ("10/10", "read it before you buy another car", ""),
}
