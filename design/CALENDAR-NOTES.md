# Notify calendar

Open `calendar.html` directly in Chrome or Edge. It is one offline file: inline CSS, JavaScript, SVG symbols and fictional data. No installation, server, fonts, libraries, network calls or storage are needed. A content security policy also blocks network connections. Reloading resets reminders and starts in dark Month view.

## Design decisions

The calendar keeps Notify's slate surfaces, Segoe UI, muted category symbols, outlined controls and blue primary action. The title bar, one-row toolbar, calendar and small category legend form the entire window. There is no filter panel or sidebar.

Month is for spotting bills, appointments and birthdays. One-time, monthly and yearly reminders get the available item rows first. Daily and weekly reminders appear together as a muted repeat symbol and **“3 repeating”** line. Clicking it opens that day's full timeline. When a cell is short, or date-specific items need the space, the repeating count moves beside the date as a small repeat symbol and number. Overflow becomes **“+N more”**, which opens Day view. The count covers hidden date-specific reminders; repeating reminders have their own count.

Day is the fast creation surface. Year is an overview of date-specific commitments. All three use the same date selection and data model.

## Dimensions and typography

All measurements are logical CSS pixels, intended to map to Qt logical pixels rather than physical display pixels.

| Element | Size / spacing |
| --- | --- |
| Initial window | 960 × 680 when the browser has room |
| Minimum desktop window | 720 × 520; resize using the bottom-right corner |
| Window edge | 1 px border, 12 px radius |
| Windows-style title bar | 32 px high; 44 px caption buttons |
| Main horizontal inset | 20 px; 16 px in a narrow window |
| Toolbar | 20 px top, 16 px bottom; 8 px gaps |
| Toolbar at minimum width | 16 px top, 12 px bottom; 4 px gaps |
| Buttons | 36 px high, 8 px radius; editor buttons 40 px high |
| View segment | 36 px total height; selected inner button 28 px high |
| Period heading | 22 px, semibold; 20 / 18 px at narrower widths |
| Body and toolbar text | 14 px |
| Month items, date labels, legend, tooltips | 12–13 px; no text below 12 px |
| Weekday header | 28 px high |
| Month grid | Seven equal columns, six equal rows, Monday first |
| Month cell | 4 px padding; 24 px date circle; 18 px item rows |
| Month density change | Below 70 px cell height, or when specific items need more rows |
| Footer | 44 px minimum height |
| Day timeline | 48 px/hour, 1,152 px/day; half-hour lines at 24 px |
| Day gutter | Hour labels in 48 px; rules begin at x = 64 px; blocks at x = 72 px |
| Reminder / ghost block | 24 px high = 30 minutes; 6 px radius |
| Timeline snap | 15 minutes = 12 px |
| Year layout | Four columns × three rows; three columns × four rows at window content width ≤ 880 px |
| Mini month | 24 px month heading, 4 px gap, 18 px weekday row, six 20 px date rows |
| Year gaps | 20 px horizontally / 12 px vertically; narrow: 24 / 16 px |
| Editor | 560 px wide, 24 px padding, 12 px radius; scrolls on short screens |
| Editor heading / labels / values | 28 / 16 / 16 px |
| Editor fields | 44 px high, 8 px radius; 16 px between groups |

The primary spacing rhythm is 4 px, with 8, 12, 16, 20 and 24 px steps. Small border offsets and symbol gaps are optical adjustments. On a desktop the toolbar stays on one row; a long Day heading elides and retains its full title tooltip. Narrow Year view scrolls vertically. The year layout responds to the mock window's width, including manual resizing, through a CSS container query. Below desktop minimum width the page also provides a compact browser fallback.

## Palette

| Role | Dark | Light |
| --- | --- | --- |
| Window | `#1b1e27` | `#e4e8f0` |
| Raised surfaces / popups | `#23262f` | `#eceff7` |
| Editor inputs | `#11151c` | `#f6f8fc` |
| Primary text | `#eef1f6` | `#1d222b` |
| Secondary text | `#aeb5c2` | `#4b5363` |
| Muted text | `#8e96a4` | `#5d6576` |
| Accent | `#86a8f4` | `#2f5fcf` |
| Accent hover | `#a3bdf7` | `#244db0` |
| Text on accent | `#0c1a38` | `#ffffff` |
| Divider | `rgba(214,226,255,.10)` | `rgba(30,50,100,.13)` |
| Hover | `rgba(214,226,255,.065)` | `rgba(30,50,100,.055)` |
| Inactive control | `rgba(214,226,255,.05)` | `rgba(30,50,100,.045)` |
| Selected segment | `#30343f` | `#d5dbe8` |
| Window border | `#505765` | `#b8c1d1` |
| Surrounding preview canvas | `#12151d` | `#cbd2df` |

| Category | Dark symbol | Light symbol | Symbol |
| --- | --- | --- | --- |
| Work | `#b8b6d6` | `#5f5a8a` | Briefcase |
| Personal | `#c9b8a3` | `#7a6047` | Person |
| Health | `#a3c2b8` | `#4a6e62` | Heart / pulse |
| Shopping | `#a9bcd2` | `#4d6a8c` | Shopping bag |
| None | `#9aa3b0` | `#5b6473` | Neutral circle |

Category backgrounds mix the symbol color at 10% in dark and 8% in light. Timeline borders use a 25% category tint and a solid category edge. Blue remains the dominant action color. A static, very faint accent gradient over the window approximates Mica; no application blur is computed. The HTML window is an opaque approximation, not actual Windows composition. The reference's 88% dark Mica treatment belongs to the native backdrop integration.

## Interaction rules

### Navigation and window

- The operating system's local date and time determine today, the initial period and relative seed dates. Nothing is pinned to November 2026. A 30-second timer refreshes the current-time line and date state at midnight.
- Today returns to today's date within the current scale. Previous / next move by one day, month or year. Month/year changes clamp dates such as January 31 or February 29 to the last valid day.
- D, M and Y switch scales; Left / Right change the period; T returns to today. Shortcuts ignore editor input and modifier combinations.
- Esc dismisses the editor first, then an open shortcuts popover, then the calendar. The title-bar close button has the same window-close result.
- Since a standalone page cannot reliably close its browser tab, close/minimize show a small reopen state. Reopen returns to today's Month view and retains in-memory edits. Maximize/restore and title-bar double-click change the mock window size.
- The footer theme button switches the whole interface, including the editor. The question-mark button lists shortcuts.
- Focus has a visible accent outline. Native dialog focus containment, labeled fields, pressed segment states, accessible date names and save announcements are included. Focus returns to an appropriate control after editing or replacing a view.
- View switches have a 160 ms fade / 3 px position response. Reduced-motion preference disables it. There are no ambient or looping animations and no heavy shadows.

### Month

- The fixed 42-day grid includes muted adjacent-month days. Today is an accent circle; past dates and their specific items are slightly dimmer.
- Items are sorted by time. Category marks, a 24-hour time and an elided title share one line; the full description is in the item tooltip.
- Empty cell space opens a new reminder at that date, 09:00, Once, None. A faint plus appears on hover or cell keyboard focus. Enter / Space on the cell creates at the same default.
- Clicking an item edits its reminder. Clicking the date, repeat summary or overflow count opens Day view for that date, including adjacent-month dates.
- The repeat summary tooltip names its daily and weekly reminders. At compact density the small repeat count is informational; the date remains the Day-view target.

### Day

- All occurrences are present, including daily and weekly reminders. The scroll position initially puts 07:00 at the top; the hour scale extends from 00:00 through 23:00.
- A block occupies exactly 30 minutes. Its category badge, title and plain repeat rule use a single row to fit the 24 px geometry. Long text elides; the full title, time, category and rule remain in the tooltip and accessible label.
- Simultaneous and other overlapping half-hour blocks occupy separate columns. Non-overlapping groups regain the full width. These are reminders, not editable-duration events.
- Hovering empty timeline space shows a ghost snapped down to the preceding quarter hour. Clicking creates Once at that local date/time. The last selectable snapped time is 23:45. Clicking a reminder opens its editor instead.
- Today has a thin accent current-time line, dot and time label. Other dates have no current-time line.

### Year

- All 12 months use Monday-first mini grids. The current date has the same accent circle.
- Only one-time, monthly and yearly occurrences produce dots. When several occur on one date, the first by time supplies the dot color; the tooltip lists all date-specific occurrences. Daily and weekly reminders do not create dots or appear in that tooltip.
- Hovering or focusing a marked date opens its tooltip. Clicking any date opens Day view, where every occurrence is included. Clicking a month name opens Month view.
- When vertical scrolling is needed, entering the current year brings today into view. Today also explicitly scrolls today's mini date into view.

### Stand-in editor and recurrence

- New reminder in the toolbar always starts at today, 09:00, Once. Cell/time clicks override that date/time. Existing items open with their clicked occurrence date and existing recurrence/category.
- Once, Daily, Weekly, Monthly and Yearly are real selections. Weekly exposes Monday-first weekday buttons and requires at least one. Monthly uses the selected date's day number; Yearly uses its month/day. Category controls use the same symbols as Notify.
- Title, date and time are required; whitespace-only titles are rejected. The title is limited to 160 characters. The preview shows the next matching future occurrence, or marks a past one-time date as past.
- Save appends a reminder or updates the existing series by ID, redraws the current scale around the chosen date, and shows a brief confirmation. Cancel, outside click and Esc discard changes. An edit applies to the entire series; occurrence exceptions are outside this mockup.
- Daily/weekly recurrence is treated as an ongoing rule, with no start/end bounds. Monthly 29/30/31 skips months without that day; February 29 yearly recurrence skips non-leap years. These policies are explicit prototype choices for the real implementation to retain or revise.
- One-time reminders appear only on their exact local date. Dates use local calendar components and midday for calendar arithmetic, avoiding UTC date conversion. Reminder times remain local wall-clock times.
- All ten requested fictional seed reminders are included. Mom's birthday is anchored 12 days after opening, the dentist 5 days after opening and car service 18 days after opening. Their anchors remain stable until the page reloads.

## Plain PyQt6 implementation

### Window shell and shared model

Use a normal `QMainWindow` with its native Windows title bar and `setMinimumSize(720, 520)`. Give it the title “Notify calendar” and an initial 960 × 680 size. The HTML caption controls are presentation stand-ins; use the real operating-system controls in Qt. Reuse Notify's existing Windows backdrop integration, with the solid slate palette as fallback. Do not add blur, a web engine or a UI library.

Create the window on demand from the tray's Calendar action or a calendar icon beside settings in the list header. Keep one reference while it is open; activate the existing instance on a second request. On close, stop timers, discard painting caches and destroy the window using `WA_DeleteOnClose`; clear the owner's reference from the destroyed signal. Reminder data belongs to the existing application model and survives window destruction. The HTML reopen behavior only simulates this lifecycle.

A horizontal layout can contain ordinary `QPushButton` controls for Today, navigation and New reminder, a stretchable period label, and an exclusive `QButtonGroup` for the three view segments. Style these with the existing Notify palette. Use a small footer for the painted legend and mock theme toggle; in production use the application's existing theme setting.

Use **one `CalendarCanvas(QAbstractScrollArea)`** for all three modes. Paint into its viewport with `QPainter`; show its native vertical scrollbar only in Day mode or overflowing Year mode. Month fits the viewport. Each mode calculates rectangles and a compact hit-region list. Neither days nor reminders need individual child widgets.

Keep reminder records with ID, title, local time, category, repeat type, anchor date and weekly weekday set. Generate occurrences only for the displayed range: 42 dates in Month, one in Day, and date-specific rules for the visible year. Cache these until the range or model changes. Daily and weekly rules remain compact records. Do not pre-expand years of recurring events.

Draw using logical coordinates and Segoe UI, with antialiasing for circles and paths. Use `QFontMetrics.elidedText` for constrained text. Category symbols can be small reusable `QPainterPath` drawings; fills, borders and lines are flat. Share palette and geometry functions across all modes. Give the canvas keyboard focus, paint a focus rectangle for the selected date/reminder, and update its accessible name/description when selection changes. Keep toolbar and dialog controls as standard accessible Qt widgets.

### Month painting and hit-testing

Calculate the Monday preceding the first of the displayed month. Divide the available width into seven columns and the height below the 28 px weekday band into six rows. Use shared floating-point boundaries for painting and hit-testing to avoid cumulative rounding errors.

Paint cell fills, grid rules, date numbers, today's circle, sorted specific item rows, overflow and the repeating summary. Use the same height/capacity calculation as the HTML. At short heights or with more specific items, put the repeating indicator in the date row. Clip every cell's text and highlight to its rectangle.

Hit-test in this order: reminder item, date number / overflow / repeat summary, cell background. Route item hits to the existing editor with reminder ID and occurrence date; route date/summary hits to Day mode; route background hits to a new Once reminder at 09:00. Track the hovered cell and invalidate only its previous/current rectangles for the faint plus.

### Day painting and hit-testing

Set the scrollbar range from the 1,152 px timeline extent and viewport height. Set the initial scroll value to 336 px after arranging the viewport; the HTML has an extra 8 px top inset, so its equivalent scroll value is 344 px. Paint only visible hour/half-hour rules, labels and reminder rectangles.

Use `y = minutes_since_midnight × 0.8 - scroll_offset` and a fixed block height of 24 px. Partition overlapping 30-minute intervals into column groups, then calculate each block's rectangle from its column and group width. Draw the category edge/badge, title and rule clipped inside the block.

Hit-test reminder rectangles before timeline background. Convert the mouse y-coordinate back to minutes, floor to a 15-minute boundary and clamp to 00:00–23:45. Store one hovered snapped time and repaint only the previous/new ghost area. Click passes that local date/time to the existing editor.

A low-frequency `QTimer`, active only while this window exists, updates the current-time marker on today. Repaint the old/new marker strips instead of the entire timeline. Recompute the date state at midnight. No continuous paint loop or per-reminder timer is needed.

### Year painting and hit-testing

Choose four columns above 880 px of content width and three at or below it. Position 12 mini-month rectangles using the dimensions above. Their total height determines whether the canvas scrollbar is needed. Build each Monday-first grid directly from calendar dates; no `QCalendarWidget` per month is required.

Draw only visible month rectangles and their headings/date labels. Generate dot data from Once, Monthly and Yearly records. Store heading/date hit regions. Month-heading hits switch to Month; date hits switch to Day. `QToolTip.showText` can display all date-specific reminders for a hovered marked day, with plain escaped text and the shared palette. Hide it on scroll, view changes and leaving the target.

### Editor, focus and lifecycle

Reuse the existing `QDialog` reminder editor. Pass the clicked date/time and Once when creating; pass ID and clicked occurrence date when editing. The mockup's stand-in maps to `QLineEdit`, `QDateEdit`, `QTimeEdit` and exclusive `QButtonGroup` controls, plus weekday toggles. Standard dialog widgets are acceptable: the requirement to avoid hundreds of children applies to calendar views.

Keep modifications in a draft until Save. Validate, commit through the application model, invalidate occurrence caches and redraw. Cancel discards the draft. Refresh the existing editor's next-occurrence preview from the same recurrence function used by the calendar.

Handle window shortcuts only when an editor/input does not own the key. Esc closes the modal before the calendar. Preserve useful focus after redraw. If transitions are retained, use one short opacity/position response, stop it when finished, and disable it for reduced motion; immediate painting is also suitable for this lightweight native window.

## Verification and limits

- JavaScript syntax check passed with Node.
- Eighteen source-level behavior checks passed using the actual inline script with a minimal DOM stub: seed offsets, recurrence and leap/missing-date rules, Monday-first 42-cell grid, overlap columns, clamped navigation, 12-month/leap-year rendering, 07:00 scroll setup, quarter-hour snapping, editor prefills, add/edit and escaping.
- Static checks confirmed no external resource URLs or network APIs, the connection-blocking policy and the 12 px text minimum.
- Palette calculations give muted text a 5.59:1 contrast ratio in dark and 4.77:1 in light against the base window. Past item opacity is 90%, keeping secondary time text at 6.80:1 / 5.00:1. Hovered cells restore item opacity and strengthen date/summary colors so dimming does not undermine hover contrast. These are source color calculations, not sampled browser pixels.
- A browser preview could not be completed: the browser access host was unavailable and native Opera access was denied. Actual rendering, pointer behavior, native date/time controls and visual contrast were not browser-verified. Geometry and interaction checks above are source-level evidence, not a substitute for that visual pass.
- The mockup does not trigger Notify's fullscreen alerts, write to the real reminder database, implement occurrence exceptions or persist data. It exercises calendar navigation and the creation/editing flow requested in the brief.
