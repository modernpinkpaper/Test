"""Script for "build day: my customer-service robot", a talk-to-camera vlog from her real workday log (her Amazon
message drafter: it reads each buyer message, checks the answer sheet, drafts a reply, and she sends it).
(key, who, line); "her" = her own cloned voice (private reference, never committed).
"""
VOICE = "her"

LINES = [
    ("intro", "her", "[calm] Hi, I'm a mom who made seven figures selling paper on the internet, and here's what running that business actually looked like today."),
    ("hook", "her", "[sassy] I haven't typed a single customer reply in weeks. Let me show you why."),
    ("eight", "her", "[sassy] Eight AM. My sales report was already done before I even sat down."),
    ("problem", "her", "[annoyed] Here's the problem. If you sell on Amazon, this is your inbox."),
    ("pain", "her", "[annoyed] Where's my order? Can you change the font? Will it ship by Friday? All day long."),
    ("built", "her", "[excited] So I built a robot."),
    ("reads", "her", "[sassy] It reads every message."),
    ("brain", "her", "[sassy] Then it checks its brain. That's a Google Sheet full of my best answers."),
    ("writes", "her", "[excited] And it writes the reply for me."),
    ("send", "her", "[sassy] I read it. I hit send. Done."),
    ("nicer", "her", "[sassy] It even sounds like me. Just nicer before coffee."),
    ("memory", "her", "[calm] Today I tested giving it a real memory, so it learns from every reply I send."),
    ("boss", "her", "[sassy] And no, it never sends anything without me. I'm the boss. It's the intern."),
    ("result", "her", "[excited] Hours of typing replies. Now it's a few clicks."),
    ("cta", "her", "[sassy] Want a robot like this for your shop? Comment the word robot, and I'll show you how it works."),
]
