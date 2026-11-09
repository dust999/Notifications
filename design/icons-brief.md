# Icon brief: Notify icon set

Draw a new icon set for Notify, a Windows 11 tray reminder app, in the visual style of `mockup.html`
in this folder (open it and study its inline SVG icons, colors and mood). The attached images and the
`old-icons/` folder are the current icons: they show which icons exist and what each one means.
Redraw them in the new style; don't copy their look.

## Deliverables (write only inside this folder)

- `icons/` with one SVG file per icon, listed below.
- `icons.html`: a preview sheet showing every icon on dark (#1c1f1f) and light (#f3f3f3) backgrounds
  at 16, 20, 24 and 32 px, with file names. Self-contained, no network.
- A short summary in your final reply.

Do not read or write anything outside this folder.

## Style rules

- 24×24 viewBox, 1.5 px stroke, round caps and joins, no fills except where noted.
- `stroke="currentColor"` (and `fill="currentColor"` for small filled details), so the app can tint
  each icon for dark and light themes. No hardcoded colors, except in the app icon.
- Must stay crisp at 16 px: align to the pixel grid, keep 2 px padding, avoid tiny details.
- Consistent optical size and corner radius across the set. Calm and friendly, matching the mockup.
- Clean minimal SVG: no editor metadata, no embedded raster images, no scripts, under 2 KB each.

## Icons

App and tray:
- `app.svg`: the app icon, full color. A rounded-square tile in the mockup's teal with a bell symbol.
  Must read at 16 px in the taskbar and look good at 256 px.
- `tray.svg`: monochrome bell for the tray, `currentColor`.
- `tray-paused.svg`: the same bell with a pause mark or slash (reminders paused).
- `tray-due.svg`: the same bell with a small dot (a reminder fired / attention).

Categories (shown in muted tinted squares in the list, and large on the fullscreen reminder):
- `cat-work.svg` (briefcase), `cat-personal.svg` (person or home), `cat-health.svg` (heart with pulse),
  `cat-shopping.svg` (bag or cart), `cat-none.svg` (a simple dot or tag).
  They must be clearly different from each other at 20 px, by shape, not only by detail.

Actions and UI:
- `add.svg`, `edit.svg`, `delete.svg`, `settings.svg`, `exit.svg`, `open-list.svg`, `repeat.svg`,
  `check.svg`, `clock.svg`, `calendar.svg`, `close.svg`, `chevron-down.svg`, `chevron-up.svg`, `pause.svg`.
