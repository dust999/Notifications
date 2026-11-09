# Design brief: Notify calendar window

You are the design lead. Build a high-fidelity, interactive HTML mockup of a new **Calendar** window
for Notify, in the app's existing style (see the attached screenshots).

## Deliverables (write only these two files, in the current folder)

1. `calendar.html`: one self-contained file with inline CSS, JS and SVG. No network requests, no external
   fonts, images or libraries. It must open by double-click in Chrome or Edge.
2. `CALENDAR-NOTES.md`: layout sizes, spacing, colors used, interaction rules, and for every view how
   it would be built in plain PyQt6 (see "Target implementation").

Do not read or write anything outside the current folder.

## The product

Notify is a small Windows 11 tray app that shows reminders. When a reminder is due it covers the screen
with a fullscreen message. Reminders are one-time (a date and time) or recurring: daily, weekly on chosen
weekdays, monthly on a day, or yearly on a date (birthdays). Each has a title, a time, a category
(Work, Personal, Health, Shopping or None) and a repeat rule.

Today a reminder is created in a form: type a title, pick a time, pick a date. The owner finds picking
dates and times in fields slow. He wants a calendar window like Google Calendar, **but much simpler and
smaller**: switch the scale between year, month and day, see what is planned, and click a day or a time
to create a reminder there.

## Look: match the current app

The screenshots show the tray list window (dark and light) and the reminder editor. The calendar must
look like part of the same app: same colors, radii, type, buttons, segmented control and category badges.

Slate theme tokens:
- Dark: window #1b1e27 (88% opaque over Mica), popups #23262f, text #eef1f6, secondary text #aeb5c2,
  muted #8e96a4, accent #86a8f4 (hover #a3bdf7, text on accent #0c1a38), dividers rgba(214,226,255,0.10),
  hover rgba(214,226,255,0.065), chips and inactive buttons rgba(214,226,255,0.05).
- Light: window #e4e8f0, raised controls #eceff7, text #1d222b, secondary #4b5363, muted #5d6576,
  accent #2f5fcf (hover #244db0, white text on it), dividers rgba(30,50,100,0.13).
- Category colors (symbol color, tint behind it), dark: Work #b8b6d6, Personal #c9b8a3, Health #a3c2b8,
  Shopping #a9bcd2, None #9aa3b0, each on a ~10% tint of itself. Light: Work #5f5a8a, Personal #7a6047,
  Health #4a6e62, Shopping #4d6a8c, None #5b6473 on ~8% tints. Keep them muted: the accent is the only
  loud color.
- Radii: 6 to 10 px for controls, 12 px for the window. Font: "Segoe UI", system-ui. Text sizes from the
  screenshots (the owner wants text on the large side; nothing below 12 px).
- Dark theme first; a mockup toggle switches to light.

## The window

A normal resizable desktop window, about 960×680 at first, minimum about 720×520, with a standard
Windows 11 title bar ("Notify calendar") and a Mica backdrop (imitate it with a subtle gradient).
Opened from the tray menu ("Calendar") and from a calendar icon button in the list window's header,
next to the settings button.

Toolbar, one row:
- "Today" button, previous and next arrow buttons, and the current period as a title
  ("November 2026", "2026", "Monday, November 9").
- Segmented control on the right: **Day / Month / Year**. Month is the default.
- "New reminder" accent button (opens the editor for today).

Keyboard: Left and Right go to the previous and next period, T goes to today, D, M and Y switch views,
Esc closes the window.

### Month view (default)

- A 6×7 grid, weeks starting on Monday, weekday names on top. Days outside the month are muted.
  Today's date number sits in an accent circle. Past days are slightly dimmed.
- Each day cell lists that day's reminders as compact one-line items: a small category-colored mark,
  the time and the title ("09:00 Pay the bills"), elided to fit. When they don't fit, a "+2 more" line.
- Everyday reminders (daily and weekly) would fill every cell and hide the important ones. Keep cells
  readable: show date-specific reminders (one-time, monthly, yearly) as items first, and decide how to
  show the repeating ones quietly (for example, one muted line like "3 repeating", or small dots).
  Do not design a filter panel: the owner will decide on filters later.
- Click empty space in a cell: opens the reminder editor with that date filled in (repeat: Once,
  time 09:00). Hovering a cell shows a faint "+" so this is discoverable.
- Click a reminder item: opens the editor for that reminder.
- Click the day number or "+2 more": switches to Day view for that date.

### Day view (the time scale)

- A vertical timeline for one day, hours 00:00 to 23:00 down the left, scrolled so 07:00 is at the top
  when opened. One hour is about 48 px tall; quarter-hour lines are not drawn, only hours (and a fainter
  half-hour line).
- Every reminder of that day (including daily and weekly ones) is a block at its time, 30 minutes tall,
  with the category badge, the title and the repeat rule in plain words ("Weekdays at 13:00").
  Reminders at the same time sit side by side.
- A thin accent line marks the current time on today.
- This is the fast way to plan the day: hovering the timeline shows a ghost block snapped to 15 minutes
  with its time ("14:30"); clicking opens the editor with that date and time filled in (repeat: Once;
  the user can switch to Daily in the editor).
- Click a block: opens the editor for that reminder.

### Year view

- 12 small month calendars in a 4×3 grid (3×4 when the window is narrow). Today in an accent circle.
- Days with date-specific reminders (one-time, monthly, yearly: birthdays, bills) get a small dot in the
  category color. Daily and weekly reminders are left out here (they would mark every day).
- Hovering a marked day shows a small tooltip with its reminders. Clicking a day opens Day view;
  clicking a month name opens Month view.

### Editor (only as a stand-in)

The real editor already exists (see the screenshot). In the mockup, clicking to create or edit opens a
simplified copy of it as a modal dialog, with the clicked date and time already filled in, so the flow
can be tried. Saving adds the reminder to the in-memory data and redraws the view.

## Target implementation and weight

- Plain PyQt6 on Windows 11, no extra UI library, no browser engine. The app runs all day in the tray,
  so it must stay light: the window is created when opened and destroyed when closed.
- Each view should be drawable as one custom-painted widget (QPainter) with mouse hit-testing, not
  hundreds of child widgets. Design with that in mind: flat shapes, text, lines, rounded rectangles.
- Effects: only short (150–200 ms) opacity or position transitions answering a user action, such as
  switching views. No looping animation, no blur computed by the app, no heavy shadows.
- Respect `prefers-reduced-motion` in the mockup.

## Mockup data (fictional)

Use the real current date and time so today is always visible.
- Drink a glass of water: Health, daily 11:00
- Team call: Work, weekly Mon, Wed, Fri 10:30
- Lunch break: Personal, weekdays 13:00
- Buy groceries: Shopping, weekly Sat 18:00
- Pay the bills: Personal, monthly on the 10th 09:00
- Renew the website domain: Work, yearly Mar 1 09:00
- Anna's birthday: Personal, yearly Jun 16 09:00
- Mom's birthday: Personal, yearly, 12 days from today, 10:00
- Dentist appointment: Health, once, 5 days from today at 15:30
- Car service: None, once, 18 days from today at 08:30

## Copy and quality

- English, sentence case, plain verbs. No "please", no exclamation marks, no ALL-CAPS labels.
- Visible keyboard focus, readable contrast in both themes, 4 px spacing grid.
- When finished, reply with a short summary of the design decisions, including how repeating
  reminders are shown in Month view.
