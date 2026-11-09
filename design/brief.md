# Design brief: Notify redesign mockup

You are the design lead for this redesign. Build a high-fidelity, interactive HTML mockup.

## Deliverables (write only these two files, in the current folder)

1. `mockup.html` — one self-contained file: inline CSS and JS, inline SVG icons, no network requests,
   no external fonts, images or libraries. It must open by double-click in Chrome/Edge.
2. `NOTES.md` — design tokens (colors for dark and light, radii, spacing, type scale, motion timings)
   and, for every UI element, which PyQt-Fluent-Widgets / Qt component would implement it.

Do not read or write anything outside the current folder.

## The product

Notify is a small Windows 11 tray app that shows reminders. It sits in the tray all day.
When a reminder is due it covers the screen with a fullscreen message; the user clicks to dismiss it.
Its jobs, in order:
1. Never let the user miss a reminder.
2. Answer "what's next?" at a glance.
3. Add or edit a reminder in a few seconds.

Reminders are recurring (daily, weekly on chosen weekdays, monthly on a day, yearly on a date) or one-time.
Each has a title, a time, an optional category (Work, Personal, Health, Shopping) and a repeat rule.
Today the app looks like a plain dark Qt form. The owner finds it ugly and wants a beautiful UI with effects.

## Hard constraints

- Target implementation: Python, PyQt6 and PyQt-Fluent-Widgets on Windows 11. Every element in the mockup
  must be buildable with them without a browser engine.
- The app must stay lightweight: small download and low memory, because it runs all day.
  So effects must be cheap:
  - Translucency comes from Windows itself (Mica or Acrylic window backdrop), not from blur computed by the app.
    In the mockup, imitate it with `backdrop-filter` over a desktop wallpaper.
  - Motion: short opacity, position and scale transitions only (150–250 ms) that answer a user action,
    plus one entrance animation for the fullscreen reminder. No looping or ambient animations,
    no particles, no canvas or video backgrounds.
  - Glows are static: a soft radial gradient or a 1 px highlight, not animated.
  - Fonts: system only, `"Segoe UI Variable", "Segoe UI", system-ui, sans-serif`.
- Dark theme is the primary theme. Also provide a light theme with the same layout (a toggle switches them).
- Desktop only. Window sizes as on a real 1920×1080 Windows desktop.
- Respect `prefers-reduced-motion`.
- UI copy in English, sentence case, plain verbs ("Save", "Snooze", "Delete reminder").
  No "please", no exclamation marks, no Title Case.

## Visual references (Dribbble, desktop notification UIs)

Use these as direction only. Do not copy any specific shot.
- Compact notification panels: a header with title and one secondary action, tabs with count badges,
  rows grouped under quiet section labels (Today, Yesterday), a leading icon per row, a bold title with a muted
  meta line, an unread dot, and action buttons right inside a row.
- The same layout shown in dark and light themes side by side.
- Dark, slightly translucent windows stacked with depth, over a strong colored glow.
- A dark card with a soft colored glow along its edge, toggles, and a rounded primary button.
- A dark glass notification panel floating over a nature photo, the photo showing through.

Make it feel like a native, premium Windows 11 utility with its own identity, not a generic SaaS dashboard.
Avoid: identical rounded cards for everything, the same grey drop shadow under everything,
ALL-CAPS labels, middle dots joining every meta string, arrows appended to button labels.
Use one accent color. The current app's accent is teal (#0d7377); you may keep a refined teal or justify another.
Category colors must be muted so the accent stays the only loud color.

## Screens to show

Put a fake Windows 11 desktop as the page background: a wallpaper (CSS gradients or an inline SVG landscape
are fine) and a taskbar at the bottom with a tray area showing the Notify tray icon.
Above the desktop, outside the app chrome, add a small mockup toolbar to switch between screens and themes:
"Reminders", "New reminder", "Fullscreen reminder", "Dark / Light".

### 1. Reminders (tray flyout, the main window)

Opens from the tray icon, anchored above the tray like a Windows 11 flyout, about 400×620 px, acrylic background.
- Header: "Reminders" and a "New reminder" button (the only accent-filled button on this screen).
- "Next up" area: the next reminder, large, with a live countdown ("in 2 h 40 min") that updates every minute,
  plus its time and repeat rule. This is the one place where a static accent glow is allowed.
- Tabs or a segmented control with counts: "Upcoming" and "Done today".
- Upcoming list grouped under: Today, Tomorrow, This week, Later. Each row: category icon in a muted tinted
  square, title, a meta line in plain words ("Weekdays at 13:00", "Every month on the 10th", "Mar 1 every year"),
  and the relative time on the right ("in 3 h", "Tue 10:30", "Mar 1").
- Hovering a row reveals Edit and Delete icon buttons. Delete asks "Delete reminder?" before removing it.
- Done today: rows dimmed, with a check and the time it was shown.
- Empty state for when there are no reminders: one line of direction and a "New reminder" button.
- Footer: settings icon button and a small "Pause reminders" toggle (pauses popups for 1 hour).

### 2. New reminder / Edit reminder (dialog)

About 440 px wide, compact, no empty space.
- Title field with suggestions from previously used titles (a dropdown appears while typing).
- Time picker.
- Repeat: segmented control Once / Daily / Weekly / Monthly / Yearly. Show only the fields the choice needs:
  date (Once), weekday chips (Weekly), day of month (Monthly; note "On shorter months: last day"),
  month and day (Yearly).
- Category chips with icons: Work, Personal, Health, Shopping, None.
- "Remind me earlier": Off / 1 day / 3 days / 1 week before. Owners use this for birthdays.
- A live preview line under the form: "Next: Mon, Nov 16 at 13:00".
- Buttons: "Save" (accent) and "Cancel". Empty title shows an inline error "Enter a title" and does not save.
- Saving adds the reminder to the list in the mockup (in memory) and returns to the Reminders screen.

### 3. Fullscreen reminder

Covers the whole desktop: dark acrylic over the wallpaper. Centered: category icon, the reminder title very large,
the scheduled time, and one "Done" button (accent). No Snooze here: the owner wants one click to close
(decided after the first mockup; Snooze may live in the app later).
Clicking anywhere on the background also dismisses it, and a quiet hint says so ("Click anywhere or press Esc to close").
One entrance animation (fade and slight scale), nothing looping.

## Mockup data (fictional)

Compute next occurrences from the rules using the real current date and time, so the groups are always filled.
- Drink a glass of water — Health — daily 11:00
- Team call — Work — weekly Mon, Wed, Fri 10:30
- Lunch break — Personal — weekdays 13:00
- Evening walk — Health — daily 20:00
- Buy groceries — Shopping — weekly Sat 18:00
- Pay the bills — Personal — monthly on the 10th 09:00
- Renew the website domain — Work — yearly Mar 1 09:00
- Anna's birthday — Personal — yearly Jun 16 09:00, remind 1 week earlier
- Dentist appointment — Health — once, 5 days from today at 15:30
Mark the reminders whose time today has already passed as "Done today".

## Quality bar

- Visible keyboard focus, readable contrast in both themes, no text below 11 px.
- Pixel-careful spacing on a 4 px grid. Clear type hierarchy (title, row title, meta).
- In NOTES.md, list anything in the mockup that would be expensive or impossible in PyQt and how you would simplify it.
- When finished, reply with a short summary of the design decisions.
