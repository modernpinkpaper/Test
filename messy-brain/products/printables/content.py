"""Page content for The Tidy Brain Printable Pack.

Every page is a dict. `kind` picks the template in templates/pages/<kind>.j2.
Voice: short, warm, zero shame (see content/FORMATS.md).
"""

# ---------------------------------------------------------------- icons
# Simple line icons, viewBox 0 0 48 48. Stroke = ink, fills use soft brand
# colours through classes (.f1 accent-soft, .f2 butter, .f3 lilac, .f4 coral, .fw white).
ICONS = {
    "pot": '<path class="f1" d="M9 22h30v11a8 8 0 0 1-8 8H17a8 8 0 0 1-8-8z"/><path d="M5 22h38"/>'
           '<path d="M18 16c0-3 2-3 2-6M24 16c0-3 2-3 2-6M30 16c0-3 2-3 2-6"/>',
    "bath": '<path class="f1" d="M6 25h36v5a10 10 0 0 1-10 10H16A10 10 0 0 1 6 30z"/><path d="M12 25V12a4 4 0 0 1 8 0"/>'
            '<path d="M14 40l-2 4M34 40l2 4"/><circle class="fw" cx="29" cy="18" r="2.2"/><circle class="fw" cx="35" cy="13" r="3"/>',
    "couch": '<rect class="f2" x="11" y="13" width="26" height="14" rx="4"/><path class="f1" d="M6 22a4 4 0 0 1 8 0v6h20v-6a4 4 0 0 1 8 0v12H6z"/>'
             '<path d="M10 34v5M38 34v5"/>',
    "bed": '<path d="M6 11v29M42 25v15M6 34h36"/><path class="f1" d="M6 25h36v9H6z"/><rect class="f2" x="10" y="18" width="11" height="7" rx="3"/>',
    "door": '<rect class="f1" x="13" y="6" width="22" height="36" rx="2"/><path d="M6 42h36"/><circle class="fi" cx="30" cy="25" r="1.8"/>'
            '<path d="M18 13h12v10H18z" class="fw"/>',
    "washer": '<rect class="f1" x="9" y="6" width="30" height="36" rx="4"/><path d="M9 14h30"/><circle class="fw" cx="24" cy="28" r="9"/>'
              '<path d="M17 29c3-3 5 2 8-1s5 1 6 0"/><circle class="fi" cx="15" cy="10" r="1.3"/><circle class="fi" cx="20" cy="10" r="1.3"/>',
    "blocks": '<rect class="f1" x="6" y="26" width="16" height="16" rx="2"/><rect class="f2" x="26" y="26" width="16" height="16" rx="2"/>'
              '<rect class="f3" x="16" y="8" width="16" height="16" rx="2" transform="rotate(8 24 16)"/>',
    "laptop": '<rect class="f1" x="10" y="10" width="28" height="20" rx="2"/><path class="fw" d="M5 34h38l-3 5H8z"/><path d="M20 20h8"/>',
    "toothbrush": '<g transform="rotate(-35 24 24)"><rect class="f1" x="4" y="23" width="28" height="6" rx="3"/>'
                  '<rect class="f2" x="31" y="22" width="12" height="7" rx="2"/><path d="M33 22v-6M37 22v-6M41 22v-6"/></g>',
    "basket": '<path d="M16 18c0-7 16-7 16 0"/><path class="f1" d="M8 18h32l-4 22H12z"/><path d="M14 26h20M15 33h18"/>',
    "plate": '<circle class="f1" cx="29" cy="25" r="13"/><circle class="fw" cx="29" cy="25" r="7"/><path d="M7 9v9a3 3 0 0 0 6 0V9M10 9v31"/>',
    "dishes": '<ellipse class="f1" cx="21" cy="35" rx="15" ry="5"/><ellipse class="f2" cx="21" cy="28" rx="15" ry="5"/>'
              '<circle cx="36" cy="14" r="4"/><circle cx="28" cy="10" r="2.5"/><circle cx="41" cy="22" r="2"/>',
    "paw": '<path class="f1" d="M6 32h36l-4 10H10z"/><ellipse class="f2" cx="24" cy="20" rx="6" ry="5"/>'
           '<circle class="f2" cx="16" cy="13" r="2.6"/><circle class="f2" cx="21" cy="8" r="2.6"/><circle class="f2" cx="27" cy="8" r="2.6"/><circle class="f2" cx="32" cy="13" r="2.6"/>',
    "plant": '<path class="f4" d="M14 28h20l-3 14H17z"/><path d="M24 28V16"/><path class="f1" d="M24 21c-8 0-11-5-11-11 6 0 11 4 11 11z"/>'
             '<path class="f1" d="M24 18c0-7 4-12 12-12 0 7-4 12-12 12z"/>',
    "backpack": '<path d="M18 12V9a6 6 0 0 1 12 0v3"/><rect class="f1" x="11" y="12" width="26" height="30" rx="7"/>'
                '<rect class="fw" x="16" y="27" width="16" height="10" rx="2"/><path d="M16 31h16"/>',
    "trash": '<path class="f1" d="M12 14h24l-2 28H14z"/><path d="M8 14h32M19 14V9h10v5M20 21v14M28 21v14"/>',
    "spray": '<path class="f1" d="M16 21h14v19a2 2 0 0 1-2 2H18a2 2 0 0 1-2-2z"/><path class="fw" d="M18 21v-6h10v6z"/>'
             '<path d="M17 15V9h12l5 4h-5"/><circle cx="39" cy="9" r="1"/><circle cx="41" cy="14" r="1"/><circle cx="38" cy="18" r="1"/>',
    "book": '<path class="f1" d="M6 12c6-2 12-2 18 2v27c-6-4-12-4-18-2z"/><path class="f2" d="M42 12c-6-2-12-2-18 2v27c6-4 12-4 18-2z"/>',
    "star": '<path class="f2" d="M24 5l5.9 12 13.1 1.9-9.5 9.3 2.2 13.1L24 35.1l-11.7 6.2 2.2-13.1L5 18.9l13.1-1.9z"/>',
    "heart": '<path class="f4" d="M24 40S8 30 8 19a8 8 0 0 1 16-3 8 8 0 0 1 16 3c0 11-16 21-16 21z"/>',
    "box": '<path class="f2" d="M8 17l16-8 16 8v21l-16 8-16-8z"/><path d="M8 17l16 8 16-8M24 25v21"/>',
    "arrow": '<circle class="f3" cx="24" cy="24" r="17"/><path d="M14 24h19M26 16l8 8-8 8"/>',
    "clock": '<circle class="f1" cx="24" cy="24" r="17"/><path d="M24 14v10l7 5"/>',
    "brain": '<path class="f3" d="M24 10c-3-4-11-3-12 3-5 1-7 7-4 11-2 5 2 10 7 10 1 4 7 6 9 2 2 4 8 2 9-2 5 0 9-5 7-10 3-4 1-10-4-11-1-6-9-7-12-3z"/>'
             '<path d="M24 10v26M17 20c3 0 5 2 5 5M31 20c-3 0-5 2-5 5"/>',
    "sun": '<circle class="f2" cx="24" cy="24" r="9"/><path d="M24 5v5M24 38v5M5 24h5M38 24h5M10.6 10.6l3.5 3.5M33.9 33.9l3.5 3.5M10.6 37.4l3.5-3.5M33.9 14.1l3.5-3.5"/>',
    "moon": '<path class="f3" d="M34 33A15 15 0 0 1 20 9a15 15 0 1 0 14 24z"/><path d="M34 10v6M31 13h6"/>',
    "timer": '<circle class="f4" cx="24" cy="27" r="15"/><path d="M20 6h8M24 6v6M24 27l6-6M37 12l3-3"/>',
    "calendar": '<rect class="f1" x="7" y="10" width="34" height="31" rx="4"/><path d="M7 18h34M15 6v8M33 6v8"/><path class="fw" d="M13 24h6v5h-6zM21 24h6v5h-6zM29 24h6v5h-6zM13 31h6v5h-6z"/>',
    "cart": '<path d="M5 8h6l5 22h21l4-15H13"/><path class="f1" d="M13 15h28l-4 15H16z"/><circle class="fw" cx="19" cy="38" r="3"/><circle class="fw" cx="34" cy="38" r="3"/>',
    "jar": '<rect class="f2" x="15" y="6" width="18" height="6" rx="2"/><path class="f1" d="M13 12h22v26a4 4 0 0 1-4 4H17a4 4 0 0 1-4-4z"/><path d="M13 22h22"/>',
    "fridge": '<rect class="f1" x="12" y="5" width="24" height="38" rx="4"/><path d="M12 18h24M17 10v4M17 23v7"/>',
    "house": '<path class="f1" d="M8 22L24 9l16 13v19H8z"/><path class="fw" d="M20 41V29h8v12z"/>',
    "wrench": '<path class="f1" d="M30 6a10 10 0 0 0-9 14L7 34a4 4 0 0 0 6 6l14-14a10 10 0 0 0 14-9l-6 6-6-2-2-6z"/>',
    "paper": '<path class="f1" d="M12 5h17l8 8v30H12z"/><path class="fw" d="M29 5v8h8"/><path d="M17 21h14M17 27h14M17 33h9"/>',
    "gift": '<rect class="f4" x="8" y="18" width="32" height="24" rx="2"/><rect class="f2" x="6" y="12" width="36" height="8" rx="2"/>'
            '<path d="M24 12v30M24 12c-4-8-12-6-9-1 1 1 5 1 9 1zM24 12c4-8 12-6 9-1-1 1-5 1-9 1z"/>',
    "check": '<circle class="f1" cx="24" cy="24" r="17"/><path d="M16 24l6 6 11-12"/>',
    "loop": '<path class="f1" d="M24 8a16 16 0 1 1-15 10"/><path d="M5 10l4 8 8-4"/>',
    "flow": '<rect class="f2" x="16" y="5" width="16" height="10" rx="3"/><path class="f1" d="M24 20l8 6-8 6-8-6z"/><rect class="f3" x="5" y="36" width="14" height="8" rx="3"/><rect class="f4" x="29" y="36" width="14" height="8" rx="3"/><path d="M24 15v5M16 26H12v10M32 26h4v10"/>',
    "grid": '<rect class="f1" x="7" y="7" width="34" height="34" rx="4"/><path d="M7 18h34M7 29h34M18 7v34M29 7v34"/>',
    "pile": '<rect class="f1" x="8" y="32" width="32" height="8" rx="2"/><rect class="f2" x="11" y="24" width="26" height="8" rx="2" transform="rotate(-4 24 28)"/><rect class="f3" x="13" y="16" width="22" height="8" rx="2" transform="rotate(5 24 20)"/><rect class="f4" x="16" y="8" width="16" height="8" rx="2" transform="rotate(-6 24 12)"/>',
}


def battery(level):
    bars = "".join(f'<rect class="f1" x="{10 + i * 9}" y="17" width="6" height="14" rx="1.5"/>' for i in range(level))
    return f'<rect class="fw" x="5" y="12" width="34" height="24" rx="5"/><path d="M41 20v8"/>{bars}'


for _n in (1, 2, 3):
    ICONS[f"bat{_n}"] = battery(_n)


# ---------------------------------------------------------------- pages
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def zone(id, title, sub, icon, theme, five, daily, weekly, monthly, seasonal):
    return dict(kind="zone", id=id, toc="Room by room", theme=theme, icon=icon,
                kicker="Zone checklist", title=title, sub=sub, fields=["Week of"],
                five=five, daily=daily, weekly=weekly, monthly=monthly, seasonal=seasonal)


PAGES = [
    dict(kind="cover", id="cover", header=False, nofoot=True),
    dict(kind="welcome", id="welcome", toc="Start here", theme="lilac", kicker="Start here",
         title="Hi friend. Start here.", toc_title="How to use this pack", sub="Pick one page. That's the whole first step."),
    dict(kind="license", id="license", toc="Start here", theme="butter", kicker="Before you print",
         title="Printing &amp; house rules", toc_title="Printing tips & personal use", sub="A few small things that make this pack easier."),

    # ---- daily rhythm
    dict(kind="daily3", id="daily3", toc="Daily rhythm", theme="sage", kicker="Every day", icon="check",
         title="The Daily 3", sub="Three tiny things a day. That's the trick.", fields=["Week of"],
         ideas=[("Home", ["Clear one surface", "Start a load of laundry"]),
                ("Future me", ["Set out tomorrow's clothes", "Fill the water bottle"]),
                ("Kind to me", ["5 minutes outside", "Text a friend"])]),
    dict(kind="routine", id="morning", toc="Daily rhythm", theme="butter", kicker="Routine", icon="sun",
         title="Morning Reset", sub="Get the day rolling, one small step at a time.",
         steps=[("Drink a glass of water", 1), ("Meds or vitamins, if you take them", 1), ("Open the blinds, let the light in", 1),
                ("Pull up the covers (messy-made counts)", 2), ("Get dressed, shoes on", 5), ("Quick wipe of the bathroom sink", 1),
                ("Empty or load the dishwasher", 5), ("Check today's calendar", 2), ("Grab keys, bag and phone from the launch pad", 1)],
         blanks=3,
         prompts=["If I only do one thing, it's", "What makes mornings easier"]),
    dict(kind="routine", id="evening", toc="Daily rhythm", theme="lilac", kicker="Routine", icon="moon",
         title="Evening Reset", sub="A gift for tomorrow-you. Ten minutes, tops.",
         steps=[("Clear and wipe the kitchen counter", 3), ("Dishes in the dishwasher or soaking", 3), ("Start the dishwasher", 1),
                ("Five-minute sweep of the main room", 5), ("Launch pad ready: keys, bag, shoes", 2), ("Set out tomorrow's clothes", 2),
                ("Peek at tomorrow's calendar", 1), ("Phone on the charger", 1), ("Teeth, face, meds", 5)],
         blanks=3,
         prompts=["If I only do one thing, it's", "Tomorrow-me will thank me for"]),
    dict(kind="emergency", id="emergency", toc="Daily rhythm", theme="coral", kicker="Emergency reset", icon="timer",
         title="15-Minute Emergency Reset", sub="Guests coming? Brain overloaded? Set a timer. Go.",
         blocks=[("0–1", "Grab your tools", ["Laundry basket", "Trash bag", "Wipes or spray", "Timer on"]),
                 ("1–4", "Trash sweep", ["Every room, trash only", "Cups and plates to the sink"]),
                 ("4–8", "Basket sweep", ["Out-of-place stuff in the basket", "No sorting yet!"]),
                 ("8–11", "Surfaces", ["Clear the kitchen counter", "Wipe the bathroom sink", "Clear the coffee table"]),
                 ("11–13", "Floors", ["Middle of the main room", "Shoes into a line"]),
                 ("13–15", "Finishing touches", ["Fluff pillows, fold the blanket", "Close doors you didn't get to", "Open a window"])]),
    dict(kind="sunday", id="sunday", toc="Daily rhythm", theme="sage", kicker="Once a week", icon="calendar",
         title="Sunday Reset", sub="Set up the week so it's a little kinder to you.", fields=["Week of"],
         house=["Wash sheets and towels", "All trash and recycling out", "Toss old food from the fridge", "10-minute tidy of the main room",
                "Restock toilet paper and soap", "Empty the basket from the week"],
         week=["Look at the next 7 days", "Plan easy dinners (meal plan page)", "Make the grocery list", "Check bills and papers",
               "Pack bags for Monday", "Put appointments in the calendar"],
         me=["Charge all the devices", "Pick one fun thing for this week", "Clothes ready for Monday", "Early-ish night"]),

    # ---- zones
    zone("kitchen", "Kitchen", "The heart of the home (and the crumbs).", "pot", "coral",
         ["Clear and wipe one counter", "Dishes in the dishwasher or soaking", "Trash out if it's full"],
         ["Load or unload the dishwasher", "Wipe counters and stovetop", "Clear the sink", "Sweep crumb hot spots"],
         ["Toss old leftovers", "Wipe fridge handles and front", "Mop or spot-clean the floor", "Wipe the microwave inside",
          "Swap dish towels and sponge", "Scrub the sink"],
         ["Wipe the fridge shelves", "Degrease the stove knobs and hood", "Clean the dishwasher filter", "Wipe cabinet fronts",
          "Descale the kettle or coffee maker"],
         ["Clean the oven", "Declutter one cupboard", "Check pantry dates", "Vacuum the fridge coils"]),
    zone("bathroom", "Bathroom", "Small room, quick wins.", "bath", "lilac",
         ["Wipe the sink and faucet", "Towels hung up", "Quick toilet swish"],
         ["Wipe the shower walls", "Products back in their bin", "Hang towels to dry", "Wipe toothpaste off the sink"],
         ["Clean the toilet, inside and out", "Scrub the sink and counter", "Clean the mirror", "Swap towels and bath mat",
          "Empty the trash", "Quick floor wipe"],
         ["Scrub the shower and tub", "Wash the shower curtain liner", "Wipe drawer and cabinet fronts", "Clean behind the toilet",
          "Restock paper, soap, toothpaste"],
         ["Toss old products", "Descale the shower head", "Scrub the grout", "Dust the fan cover"]),
    zone("living", "Living Room", "Where everything ends up. Let's help it leave.", "couch", "sage",
         ["Basket sweep: stray stuff in", "Fluff pillows, fold the blanket", "Clear the coffee table"],
         ["Cups and plates to the kitchen", "Remotes and chargers home", "Blanket folded on the couch", "Toys back in their bins"],
         ["Vacuum floors and rugs", "Dust surfaces you can see", "Wipe the coffee table", "Crumbs out of the cushions",
          "Water the plants", "Recycle old mail and magazines"],
         ["Dust the TV and electronics", "Wipe switches and door handles", "Wash throws and pillow covers", "Dust the blinds or sills",
          "Declutter one shelf"],
         ["Wash the windows", "Vacuum under the couch", "Rotate cushions and rugs", "Refresh the decor you love"]),
    zone("bedroom", "Bedroom", "A calm place to land at night.", "bed", "lilac",
         ["Pull up the covers", "Clean clothes away, dirty in the hamper", "Cups off the nightstand"],
         ["Make the bed (messy-made counts)", "Clothes off the floor and chair", "Cups and plates out", "Phone on the charger"],
         ["Wash sheets and pillowcases", "Vacuum the floor", "Dust nightstand and dresser", "Reset the clothes chair",
          "Put away clean laundry", "Empty the trash"],
         ["Vacuum under the bed", "Wash the duvet cover", "Declutter the nightstand drawer", "Wipe mirrors and switches"],
         ["Rotate the mattress", "Wash pillows and duvet", "Swap seasonal clothes", "Donate clothes that don't fit"]),
    zone("entry", "Entryway &amp; Launch Pad", "One spot for everything you need to leave the house.", "door", "butter",
         ["Shoes in the bin or rack", "Keys, wallet, bag to the launch pad", "Mail to the paper tray"],
         ["Keys on the hook", "Bag packed for tomorrow", "Shoes lined up", "Coats hung up"],
         ["Sort the mail pile", "Sweep or vacuum the floor", "Wipe the door handle and switch", "Clear receipts out of your bag",
          "Return stuff that lives elsewhere"],
         ["Shake out or wash the doormat", "Declutter shoes and coats", "Refill the launch pad kit", "Wipe the front door"],
         ["Swap seasonal gear", "Donate outgrown shoes", "Check hooks and bins still work", "Wash the outside light"]),
    zone("laundry", "Laundry", "Wash, dry, fold, away. The loop, not the mountain.", "washer", "sage",
         ["Move the wet load (alarm set!)", "Fold one basket during a show", "Clean the lint trap"],
         ["One load, start to finish", "Clean the lint trap", "Put clean clothes away (roughly is fine)", "Check the hampers"],
         ["Wash the towels", "Wash the sheets", "Wipe the washer and dryer tops", "Match lonely socks (or don't)", "Restock detergent"],
         ["Wipe the washer door seal", "Run a washer cleaning cycle", "Wipe the laundry shelf", "Return the pocket treasures"],
         ["Check the dryer vent hose", "Declutter worn-out clothes", "Wash the laundry baskets", "Vacuum behind the machines"]),
    zone("kids", "Kids' Room", "Teamwork makes it stick. Pictures on bins help.", "blocks", "coral",
         ["Toy sweep: everything in bins", "Clothes in the hamper", "Books back on the shelf"],
         ["10-minute tidy together", "Dirty clothes in the hamper", "Make the bed (their way counts)", "Cups and snacks out"],
         ["Wash the sheets", "Vacuum the floor", "Empty the trash", "Clear the desk or play table", "Put away laundry together"],
         ["Rotate toys (store some away)", "Sort art and school papers", "Wipe handles and switches", "Check what doesn't fit"],
         ["Donate outgrown toys and clothes", "Vacuum under the bed", "Wash the stuffed animals", "Picture labels on bins"]),
    zone("office", "Home Office", "A clear desk means an easier start tomorrow.", "laptop", "lilac",
         ["Clear the desk surface", "Cups and plates to the kitchen", "Papers in the inbox tray"],
         ["End-of-day desk clear", "Write tomorrow's top 3", "Cables and chargers home", "Trash in the bin"],
         ["Empty the paper inbox", "Wipe desk, keyboard, mouse", "Back up your files", "Empty trash and recycling",
          "Refill pens and sticky notes"],
         ["Clear your desktop and downloads", "Shred papers you don't need", "Dust the screen and shelves", "Check the supply stash"],
         ["Clear out old files", "Label your cables", "Review subscriptions", "Declutter the drawers"]),
    dict(kind="calendar", id="calendar", toc="Room by room", theme="sage", kicker="Monthly", icon="grid",
         title="Monthly Cleaning Calendar", sub="Write in your dates. Use any month, any year.", fields=["Month"],
         rotation=[("Week 1", "Kitchen & fridge"), ("Week 2", "Bathrooms"), ("Week 3", "Bedrooms & laundry"),
                   ("Week 4", "Living room & entry"), ("Week 5", "Catch-up or rest")],
         once=["Check or change the HVAC filter", "Clean the dishwasher filter", "Wash the duvet cover", "Test the smoke alarms",
               "Clear out the car"]),

    # ---- energy & motivation
    dict(kind="menu", id="low", toc="Energy & wins", theme="sage", kicker="Energy menu", icon="bat1",
         title="Low Energy Menu", sub="Tank almost empty? Pick one. That's a win.",
         sections=[("From the couch", [("Fold laundry during a show", "10 min"), ("Sort the mail: keep or toss", "5 min"),
                                       ("Make the grocery list", "5 min"), ("Unsubscribe from 5 emails", "3 min"), ("Match socks", "5 min")]),
                   ("Tiny moves", [("Throw away 10 things", "3 min"), ("Carry cups to the kitchen", "2 min"),
                                   ("Wipe the bathroom sink", "1 min"), ("Put 5 things back home", "2 min"), ("Start a load of laundry", "2 min")]),
                   ("Kind to me", [("Drink a glass of water", "1 min"), ("Open a window", "1 min"),
                                   ("Put on music or a podcast", "1 min"), ("Order groceries for pickup", "10 min")])],
         blanks=3, footnote="Resting counts too. Tomorrow is a new menu."),
    dict(kind="menu", id="medium", toc="Energy & wins", theme="butter", kicker="Energy menu", icon="bat2",
         title="Medium Energy Menu", sub="Some fuel in the tank. Pick two or three.",
         sections=[("Quick wins", [("Empty the dishwasher", "5 min"), ("Clear and wipe the counters", "10 min"),
                                   ("Take out all trash and recycling", "5 min"), ("Change the sheets", "10 min"), ("Wipe down the bathroom", "10 min")]),
                   ("One spot, done", [("Clear one doom pile", "15 min"), ("Tidy the launch pad", "10 min"),
                                       ("Vacuum the main room", "10 min"), ("Clear out the fridge", "15 min")]),
                   ("Set up the week", [("Plan 3 easy dinners", "10 min"), ("Prep a snack box", "10 min"),
                                        ("Pay one bill", "5 min"), ("Fill up the car", "15 min")])],
         blanks=3, footnote="Stop while you still feel okay. That's how we come back tomorrow."),
    dict(kind="menu", id="high", toc="Energy & wins", theme="coral", kicker="Energy menu", icon="bat3",
         title="High Energy Menu", sub="Feeling it? Ride the wave (and stop before the crash).",
         sections=[("Deep clean", [("Scrub the shower and tub", "20 min"), ("Mop all the floors", "25 min"),
                                   ("Clean the oven or microwave", "20 min"), ("Wash windows in one room", "20 min")]),
                   ("Declutter", [("Fill one donation bag", "20 min"), ("Clear one drawer or cupboard", "15 min"),
                                  ("Clear the closet floor", "25 min"), ("Doom pile + the sorter page", "30 min")]),
                   ("Big-ish projects", [("Prep food for 3 days", "45 min"), ("Fix one problem spot", "30 min"),
                                         ("Drop off donations", "20 min"), ("Deep clean the fridge", "30 min")])],
         blanks=3, footnote="Set a timer for the break too. Water, snack, sit down."),

    # ---- kitchen & food
    dict(kind="laundry", id="laundryloop", toc="Kitchen, food & laundry", theme="sage", kicker="Tracker", icon="loop",
         title="Laundry Loop Tracker", sub="It's only done when it's put away. Tick each step.",
         steps=["Wash", "Dry", "Fold", "Away"], rows=13),
    dict(kind="mealplan", id="mealplan", toc="Kitchen, food & laundry", theme="coral", kicker="Food", icon="plate",
         title="Weekly Meal Plan", sub="Easy meals count. Cereal for dinner counts.", fields=["Week of"]),
    dict(kind="grocery", id="grocery", toc="Kitchen, food & laundry", theme="sage", kicker="Food", icon="cart",
         title="Grocery List", sub="Sorted by aisle, so you're in and out.", fields=["Store"],
         cats=["Produce", "Dairy & eggs", "Meat & protein", "Bread & bakery", "Pantry", "Frozen", "Snacks & drinks",
               "Household", "Don't forget!"]),
    dict(kind="pantry", id="pantry", toc="Kitchen, food & laundry", theme="butter", kicker="Inventory", icon="jar",
         title="Pantry Inventory", sub="If we can see it, we won't buy it twice.", fields=["Updated"],
         cats=["Staples", "Cans & jars", "Baking", "Breakfast", "Snacks", "Spices & sauces"]),
    dict(kind="fridge", id="fridge", toc="Kitchen, food & laundry", theme="lilac", kicker="Inventory", icon="fridge",
         title="Fridge &amp; Freezer", sub="Out of sight, out of mind? Not anymore.", fields=["Updated"]),

    # ---- declutter
    dict(kind="flowchart", id="flowchart", toc="Declutter", theme="lilac", kicker="Declutter", icon="flow",
         title="The 5-Bin Decision Flow", sub="One item at a time. Follow the arrows.",
         steps=[("Is it trash, broken, or expired?", "trash", "Trash", "Bag it. Out it goes today."),
                ("Does it live in another room?", "arrow", "Relocate", "Basket it. Walk it home at the end."),
                ("Do I use it, or truly love it?", "heart", "Keep", "Give it a home it can go back to."),
                ("Could I let it go with no big pang?", "box", "Donate / Sell", "Bag it, car it, drop it this week.")],
         maybe=("clock", "Maybe", "Box it, write today's date, check again in 30 days.")),
    dict(kind="declutter", id="declutter", toc="Declutter", theme="sage", kicker="Declutter", icon="trash",
         title="Declutter Tracker", sub="Every bag out the door counts.", rows=12, bags=40),
    dict(kind="doompile", id="doompile", toc="Declutter", theme="coral", kicker="Declutter", icon="pile",
         title="Doom Pile Sorter", sub="Didn't Organize, Only Moved. We all have one.",
         sorts=[("trash", "Trash & recycle", "Straight to the bin."), ("arrow", "Lives elsewhere", "Basket it, walk it home."),
                ("paper", "Needs action", "Write it below. Then it can wait."), ("heart", "Stays here", "Give it a real spot.")]),
    dict(kind="challenge", id="challenge", toc="Declutter", theme="butter", kicker="Declutter", icon="calendar",
         title="30-Day Declutter Challenge", sub="One tiny spot a day. Circle the day when it's done.", fields=["Start date"],
         days=["Your wallet or bag", "Old food in the fridge", "5 mugs you never use", "Receipts and junk mail", "Socks with no match",
               "Old products and expired meds", "One kitchen drawer", "Pens that don't work", "Cables with no device", "Rest day! You earned it",
               "Containers with no lids", "Clothes that don't fit today", "Shoes you don't wear", "The bathroom counter", "Freebies you never use",
               "Old magazines and catalogs", "Rest day! Look how far", "Your nightstand", "Old makeup and skincare", "Spare towels and sheets",
               "Outgrown kid stuff", "20 phone screenshots", "The junk drawer (yes, that one)", "Rest day + donation drop-off", "Books you won't reread",
               "Decor you don't love", "Under the kitchen sink", "The car: trash and strays", "One shelf, anywhere", "Victory lap: 30 things!"]),

    # ---- brain & paper
    dict(kind="braindump", id="braindump", toc="Brain & paper", theme="lilac", kicker="Brain", icon="brain",
         title="Brain Dump", sub="Get it out of your head. No order needed.", fields=["Date"],
         buckets=[("Today", "max 3!"), ("This week", ""), ("Someday / maybe", ""), ("Not mine to do", "ask or drop")]),
    dict(kind="habits", id="habits", toc="Brain & paper", theme="sage", kicker="Tracker", icon="check",
         title="Habit Tracker", sub="Color a dot each day you do it. Gaps are allowed.", fields=["Month"], rows=11,
         ideas=["Daily 3", "Evening reset", "Launch pad", "Dishes before bed", "One load of laundry", "Water plants", "10 minutes outside", "Meds with breakfast", "Phone away at 10pm", "Make the bed"]),
    dict(kind="bills", id="bills", toc="Brain & paper", theme="butter", kicker="Paper", icon="paper",
         title="Bill &amp; Paper Tracker", sub="Tick the month when it's paid. No more surprise late fees.", fields=["Year"], rows=12),

    # ---- family & home
    dict(kind="homemap", id="homemap", toc="Family & home", theme="coral", kicker="Home", icon="house",
         title="Where Things Live", sub="If it has a home, it can go home.",
         things=["Keys", "Wallet and bag", "Phone chargers", "Mail and papers", "Scissors and tape", "Batteries", "Medicine",
                 "First aid kit", "Spare light bulbs", "Tools", "Flashlight", "Spare keys", "Documents", "Gift wrap",
                 "Pet supplies", "Reusable bags", "Sunglasses", "Extension cords", "", "", "", ""]),
    dict(kind="chores", id="chores", toc="Family & home", theme="sage", kicker="Family", icon="star",
         title="Family Chore Chart", sub="Teamwork makes the house work.", fields=["Week of"],
         chores=[("bed", "Make the bed"), ("toothbrush", "Brush teeth"), ("basket", "Clothes in the hamper"), ("plate", "Set the table"),
                 ("dishes", "Clear the dishes"), ("spray", "Wipe the table"), ("blocks", "Toys away"), ("backpack", "Pack the school bag"),
                 ("paw", "Feed the pet"), ("plant", "Water the plants"), ("trash", "Take out the trash"), ("book", "Read for 15 minutes")]),
    dict(kind="maintenance", id="maintenance", toc="Family & home", theme="lilac", kicker="Home", icon="wrench",
         title="Home Maintenance Log", sub="Future-you will love knowing when you last did it.",
         checks=[("Test smoke & CO alarms", "Monthly"), ("Alarm batteries", "Yearly"), ("HVAC / furnace filter", "1–3 months"),
                 ("Clean the dryer vent", "Yearly"), ("Fridge coils", "Yearly"), ("Range hood filter", "3 months"),
                 ("Fire extinguisher check", "Yearly"), ("Gutters", "Spring & fall"), ("Water heater check", "Yearly")],
         repairs=7),

    dict(kind="done", id="done", toc="Energy & wins", theme="butter", kicker="Wins", icon="star",
         title="The “I Did It” List", sub="To-do lists show what's left. This one shows what you did.", rows=16),
    dict(kind="reward", id="reward", toc="Energy & wins", theme="coral", kicker="Wins", icon="gift",
         title="Reward Menu", sub="Our brains love a treat. Plan it ahead.",
         sections=[("Tiny treats", "after one task", ["Favorite snack", "Fancy coffee at home", "One episode, guilt-free"]),
                   ("Medium treats", "after a reset", ["Takeout night", "A new plant", "Bath and a face mask"]),
                   ("Big treats", "after a week or a challenge", ["A day trip", "A new book or game", "Something from the wishlist"])],
         earn=["Daily 3s in a row", "Sunday resets", "Doom piles cleared"]),
]

TOC_ORDER = ["Start here", "Daily rhythm", "Room by room", "Energy & wins", "Kitchen, food & laundry",
             "Declutter", "Brain & paper", "Family & home"]
