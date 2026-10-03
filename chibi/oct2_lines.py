"""Script for "what did I even do today" (Oct 2), a talk-to-myself productivity vlog made from her MT Log for the day.
Every beat is something the log shows: reinstalling MT Log and the InDesign logger, the MPP Assistant (instant
recommendations, the shortcut she never used, the API key / env variable / Apps Script / PowerShell setup, then
deciding she'd rather just ask her Claude chat), the long review with the team (Shopify screen recording, auto proofs,
the new collapsing Shopify script), Amazon's Seller Assistant workflow (Run Now -> a CSV with every unshipped
order's customizations), the name-match idea, the "mail it to each person" customer, the staff timing look and her
apology, the paused printer, and the end of the day.
Her speaking style (from her voice memos): thinking out loud, "okay so", "like", "honestly", "for real", "anyway".
Staff and customers are not named. (key, who, line); "her" = her own cloned voice (private reference, never committed).
"""
VOICE = "her"

LINES = [
    ("hook", "her", "[calm] Okay. So what did I actually do today. Because it felt like a lot, and also like nothing. Let me think."),
    ("install", "her", "[neutral] So first thing, I uninstalled the old MT Log, put the new one on, and dropped the little InDesign logger in my startup scripts. That part was easy."),
    ("cards", "her", "[excited] Then I opened the new assistant, and the second I started it, it gave me tons of recommendations. Like, I barely did anything. How?"),
    ("shortcut", "her", "[sassy] And one of them was like, nice job using this shortcut. I did no such thing. I didn't even know that was a shortcut."),
    ("setup", "her", "[annoyed] Then it was API keys, environment variables, Apps Script, PowerShell. And I'm like, why do I gotta use PowerShell? Do I really need Google Cloud? Come on."),
    ("honest", "her", "[calm] And honestly? By lunch I decided I don't even like it. I'd rather just ask my Claude chat that's connected to my logs, when I feel like it. So. That's that."),
    ("team", "her", "[neutral] Most of my morning was really with the team though. Going through the screen recording of the orders, the auto proofs, the new Shopify script that collapses everything."),
    ("workflow", "her", "[excited] Okay, but the win today. Amazon has these seller assistant workflows now. I told it, get me the customizations for every unshipped order, hit run now, and it gave me a spreadsheet. With the customizations. I was so happy."),
    ("match", "her", "[calm] So now I want it to check if the name on the customization kind of matches the ship to name. Like eighty percent. We'll see."),
    ("mail", "her", "[annoyed] Oh, and a customer thought we were gonna mail the invitations to every single person on her list. Like. No."),
    ("sorry", "her", "[calm] And then I looked at the timing for the girls, and I realized I didn't communicate something right. So I told her sorry. That one was on me. For real."),
    ("printer", "her", "[sassy] Also, my printer was paused the whole day. So nothing I printed today actually printed. Cool."),
    ("bye", "her", "[calm] Anyway. Tomorrow. Printer, my emails, and that Amazon workflow. Okay. Bye."),
]
