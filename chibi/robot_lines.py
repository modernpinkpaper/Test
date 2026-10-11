"""Script for "build day: my customer-service robot", a talk-to-camera vlog from her real workday log (her Amazon
message drafter: three times a day it reads each buyer message, pulls up the order and tracking, picks the matching
answer from her Bot Brain sheet, fills it in and leaves a draft; she reads it and sends it herself).
Written in her own speaking style (from her voice memos): thinking out loud, "like", "right?", "first of all",
"and I mean that for real", "boom", "anyway... okay, bye".
(key, who, line); "her" = her own cloned voice (private reference, never committed).
"""
VOICE = "her"

LINES = [
    ("hook", "her", "[calm] Okay so. I'm a forty year old mom, I run a seven figure paper business, and I don't answer my own customer messages anymore. Like, at all."),
    ("show", "her", "[sassy] And I know how that sounds. So let me show you, because I'm actually really proud of this one."),
    ("problem", "her", "[annoyed] So if you sell on Amazon, you know. Where's my order? Can you change the font? Will it be here by Saturday? It's literally all day."),
    ("me", "her", "[calm] And for the longest time, it was me. Answering every single one. Which, first of all, is not the best use of my time, right?"),
    ("built", "her", "[excited] So here's what I did. I built this thing. Three times a day, it goes into my Amazon messages and reads every new one."),
    ("order", "her", "[neutral] It pulls up the order, it checks the tracking, so it already knows. Okay, this one shipped Tuesday, it says delivered, whatever."),
    ("brain", "her", "[calm] And then it goes to this Google Sheet, which is basically my brain. Every answer I've ever given, the way I actually say it."),
    ("example", "her", "[sassy] Like, if tracking says delivered, but it's only been a couple days, it knows to tell them, hey, the carrier marks it delivered early sometimes. Check your mailbox."),
    ("draft", "her", "[neutral] It picks the right one, fills in the name, the tracking, the dates, and boom. There's a draft sitting in the reply box."),
    ("send", "her", "[calm] And I just read it. If it's good, I hit send. If it's off, I fix it."),
    ("trust", "her", "[sassy] It does not send anything on its own. Period. I'm not there yet. I don't trust it that much, and I mean that for real."),
    ("memory", "her", "[calm] Today I was testing giving it a memory. So every time I fix a reply, it learns from that, and next time it's closer."),
    ("honest", "her", "[calm] Is it a hundred percent? No. But I went from typing all day, to just, you know, checking its homework."),
    ("cta", "her", "[sassy] Anyway. If you sell online and you're drowning in messages, comment the word robot, and I'll show you how I set it up. Okay. Bye."),
]
