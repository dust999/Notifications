# Notify mockup

Open `mockup.html` directly in Chrome or Edge. It is one offline file: system fonts, inline CSS, JavaScript, and SVG. The content security policy blocks network connections and external resources. All changes last for the current page session.

The design uses a quiet landscape, a compact tray flyout, and one teal accent. Hierarchy comes from typography, spacing, dividers, and muted category symbols. Only the next reminder has an accent glow. Lists remain lists, rather than stacks of cards. The desktop and toolbar are a presentation harness, not part of the shipped app.

## Design tokens

| Token | Dark | Light |
| --- | --- | --- |
| Accent | `#79ded0` | `#09655d` |
| Accent hover | `#99e8dd` | `#07554e` |
| Text on accent | `#083c36` | `#ffffff` |
| Main text | `#f1f5f4` | `#172c29` |
| Secondary text | `#b0bfbd` | `#4b625e` |
| Muted text | `#96a8a5` | `#495f58` |
| Acrylic tint | `rgba(24,36,36,.88)` | `rgba(240,247,243,.89)` |
| Solid popup surface | `#202e2e` | `#f1f7f3` |
| Selected segment | `#2b3c3a` | `#ffffff` |
| Hover | `rgba(206,236,231,.065)` | `rgba(24,71,59,.055)` |
| Divider | `rgba(220,245,238,.10)` | `rgba(26,68,56,.12)` |
| Window edge | `rgba(224,255,247,.16)` | `rgba(255,255,255,.85)` |
| Input surface | `rgba(7,18,18,.40)` | `rgba(255,255,255,.65)` |
| Chip surface | `rgba(211,236,229,.055)` | `rgba(22,70,56,.045)` |
| Work symbol / tint | `#b3b4ce` / `#aaa8d11a` | `#666183` / `#73638f12` |
| Personal symbol / tint | `#c8b79f` / `#c9ae8c1a` | `#806449` / `#a37b4814` |
| Health symbol / tint | `#9dbeb3` / `#9cc6b31a` | `#4c7161` / `#50796012` |
| Shopping symbol / tint | `#a9baca` / `#9ab7d11a` | `#526e88` / `#557b9c14` |
| Error | `#ffb4ab` | `#ad2525` |
| Fullscreen acrylic tint | `rgba(12,24,25,.88)` | `rgba(232,241,237,.92)` |
| Modal scrim | `rgba(5,13,15,.34)` | `rgba(12,32,33,.20)` |
| Taskbar tint | `rgba(21,31,34,.84)` | `rgba(229,240,237,.88)` |

The lighter dark-theme accent keeps text and small icons readable. Both themes use the same teal hue family and identical geometry. Category colors communicate type quietly; they do not change the primary button color.

- Font family: `"Segoe UI Variable", "Segoe UI", system-ui, sans-serif`.
- Type: 11 px section labels, counts, row metadata, and compact chips; 12 px field labels and utility text; 13 px row titles and buttons; 14 px base; 16 px fullscreen metadata; 21 px dialog heading; 23 px flyout heading; 24 px next reminder; 64 px fullscreen title (52 px on shorter desktops).
- Weights: 400 body, 500 quiet labels, 600 action and row titles, 650 main headings. Use Segoe UI Semibold where variable weights are unavailable.
- Spacing: 4 px base; 4, 8, 12, 16, 20, 24, 32, 40, 48 px. Optical 1–3 px adjustments are limited to borders, icon alignment, and control insets.
- Geometry: flyout 408 × 644 px, 16 px from the right and 12 px above the 48 px taskbar; scrollable body. At short desktop heights, height is capped to keep the toolbar and footer visible. Editor 440 px wide; confirmation 360 px. No mobile layout.
- Radii: 4 px menu items; 6 px inputs, weekday chips, and icon buttons; 7 px list hover; 8 px buttons, segmented groups, and menus; 9 px category icons; 12 px flyout and app mark; 13 px editor and toolbar; 18 px fullscreen category icon; pill switch.
- Icons: 13–20 px inline stroke symbols, 1.65 px stroke; 32 px fullscreen symbol. Main buttons 36 px high, compact buttons 32 px, fullscreen buttons 44 px. Standard icon targets 32 × 32 px; row actions 30 × 30 px.
- Motion: 150 ms row-action opacity, switch thumb position, and pressed scale; 200 ms flyout/dialog opacity and 8 px entrance translation; 240 ms fullscreen opacity and scale from .97 to 1, once per appearance. No loops. `prefers-reduced-motion` disables all transitions and animations.
- Elevation: one window shadow (`0 24px 72px #0005, 0 4px 16px #0003` dark; reduced opacity in light), smaller menu shadow, 1 px edge. No shadows on reminder rows. Native Windows composition should supply real window elevation.
- Acrylic simulation: 32 px CSS backdrop blur for windows, 24 px for the desktop harness, 40 px for fullscreen. The real app uses OS composition, never an application-rendered blur. The sole UI accent glow is a static radial tint behind “Next up”.

## Interaction and scheduling

- The initial nine reminders use the supplied rules and the computer's current local date/time. The dentist date is five local calendar days from opening the page. The clock and countdown update at minute boundaries. No fabricated fixed dates or countdowns.
- Each upcoming row represents that reminder's next unhandled notification. Recurring reminders can appear in both tabs: shown today, scheduled again tomorrow. The list sorts by scheduled notification time. Today, Tomorrow, This week (through Sunday), and Later are always rendered. An empty group receives a quiet explanation: the supplied rules cannot guarantee every group contains a reminder at every possible date/time.
- Scheduled notifications earlier today are seeded into Done today with their scheduled time as the fictional time shown. Dismissed and snoozed reminders record the actual interaction time. Done today lists only the current local calendar date.
- Earlier reminders are additional notifications, not replacements for the original event. Anna's birthday notifies June 9 and June 16 at 09:00. The next notification drives grouping and preview. Monthly dates clamp to the last day of shorter months. A yearly Feb 29 rule uses Feb 28 in other years; the editor explains this when selected.
- Once, Daily, Weekly, Monthly, and Yearly reveal only their relevant inputs. Weekday chips allow multiple selections. Time and date inputs use browser-native controls to approximate Qt pickers. Title suggestions filter previously used titles while typing; arrows, Enter, and Escape work. Saved titles join the suggestion history.
- Save validates a nonempty title, valid time and calendar fields, at least one weekly day, and a future occurrence. Empty title displays exactly “Enter a title”. Cancel discards edits. Save updates the in-memory list and returns to Upcoming.
- Hover or keyboard focus inside a row reveals Edit and Delete buttons. Deletion requires confirmation. Removing all reminders exposes the empty state and its New reminder action. The empty-state action is secondary so the header remains the only accent-filled button on this screen.
- Pause holds due notifications for one hour, shows the resume time, and resumes automatically. Due reminders queue while paused or while another dialog/reminder is open, then appear one at a time on minute checks. Manual previews remain available during a pause.
- Fullscreen preview uses the next scheduled reminder. Done, background click, and Escape mark that occurrence as shown, then return to the flyout. The centered title and icon also dismiss when clicked; the action area is excluded. Snooze creates a notification in 5, 10, 30, or 60 minutes. Snoozing records the current showing in Done today and reschedules its follow-up. Changing screens with the preview toolbar exits a fullscreen preview without marking it done.
- Theme changes preserve the current form and data. Settings offers appearance controls and a fullscreen preview. The tray button toggles the flyout; the desktop/taskbar Notify buttons open it. Other taskbar graphics are scenery.
- Visible keyboard focus, proper labels, tab/radio arrow navigation, dialog focus trapping, restored focus, live preview/status messages, and a keyboard-operated snooze menu are included. All text is at least 11 px. Scroll the reminder list to inspect later groups.

## Native implementation map

Use PyQt6 with PyQt-Fluent-Widgets. Names below describe the standard public component families; exact constructor details should follow the chosen package version. No browser engine is needed.

| Visible element | PyQt-Fluent-Widgets / Qt implementation |
| --- | --- |
| Tray icon and flyout toggle | `QSystemTrayIcon`, an `QIcon` assembled from the supplied simple line artwork, and its activation signal |
| Flyout shell, border, backdrop, shadow | `AcrylicFlyoutViewBase` / `Flyout` shell or a small frameless `QWidget`; Windows DWM backdrop and native shadow; custom `QPainter` 1 px border |
| Tray anchor and taskbar clearance | `QScreen.availableGeometry()`, screen/taskbar geometry, and flyout positioning; support DPI scaling and multiple monitors |
| Notify brand, main heading | `IconWidget`, `CaptionLabel`, `SubtitleLabel`; `QHBoxLayout` / `QVBoxLayout` |
| New reminder button | `PrimaryPushButton` with a Fluent add icon |
| Next up label, title, schedule, countdown | `CaptionLabel`, `SubtitleLabel`, `BodyLabel` / `QLabel`, clock `IconWidget`; `QTimer` updates minute text |
| Next up static tint | Cache a small `QRadialGradient` or paint it directly in this widget's `paintEvent`; no blur effect |
| Upcoming and Done today tabs | `Pivot` / `SegmentedWidget`, with custom count `CaptionLabel` or small `QLabel` badges; selected underline in palette accent |
| Scrollable grouped list | `ScrollArea` with a layout for nine rows; `QListView` + `QAbstractListModel` and a delegate if counts grow |
| Group headings and empty-group copy | `CaptionLabel` widgets, with spacing and optional section header delegate |
| Reminder row and hover surface | Lightweight custom `QWidget` with `QHBoxLayout`, or `QStyledItemDelegate`; handle enter/leave/focus events |
| Category square and line symbol | `IconWidget` inside a fixed-size tinted `QWidget`, or paint both in the row delegate; use `QIcon` / small SVG assets |
| Row title, ellipsis, metadata, relative time | `BodyLabel` / `CaptionLabel`; use `QFontMetrics.elidedText()` and full-title tooltip |
| Edit and Delete row actions | `TransparentToolButton` and Fluent edit/delete icons; reveal on hover or keyboard focus |
| Done row dimming, check, time shown | Muted text/icon palette in the row widget or delegate; `IconWidget` check and `CaptionLabel` |
| No-reminders / no-done empty states | `IconWidget`, `BodyLabel`, and `PushButton` with standard layouts |
| Footer divider and tint | `QFrame` / `HorizontalSeparator`, a simple palette fill, and `QHBoxLayout` |
| Settings icon and popup | `TransparentToolButton`; small `FlyoutViewBase` / `Flyout` with appearance `SegmentedWidget` and `PushButton` |
| Pause switch and resume-time label | `SwitchButton`, `CaptionLabel`, and a single-shot `QTimer`; keep scheduling active while suppressing delivery |
| New / Edit dialog shell and close icon | `MessageBoxBase` / `MaskDialogBase`, `SubtitleLabel`, `TransparentToolButton`, and `QFormLayout` / nested layouts |
| Title input and error line | `LineEdit`, `CaptionLabel`, invalid border palette; focus input when invalid |
| Title suggestion dropdown | `QCompleter` backed by `QStringListModel`, or a small anchored `Flyout` with a `ListView` to match the visual style |
| Time input and calendar inputs | `TimePicker` / `QTimeEdit`, `CalendarPicker` / `QDateEdit`; use 24-hour display |
| Repeat and earlier-reminder selectors | `SegmentedWidget` or custom `QButtonGroup` of checkable `PushButton` controls; exclusive radio semantics |
| Weekly weekday chips | Seven checkable `PushButton` controls in a nonexclusive `QButtonGroup`; accessible full weekday labels |
| Monthly day input and shorter-month note | `SpinBox` / `QSpinBox` range 1–31 and `CaptionLabel` |
| Yearly month and day | `ComboBox`, `SpinBox`, date-dependent maximum and explanatory `CaptionLabel` |
| Category chips | Exclusive `QButtonGroup` of compact checkable `PushButton` controls with `QIcon`; accent outline for selection |
| Live next-occurrence preview | `IconWidget` and `CaptionLabel`; recompute on form signals, announce via Qt accessibility |
| Save and Cancel | `PrimaryPushButton`, `PushButton`; connect accepted/rejected signals and form validation |
| Delete confirmation | `MessageBox` / `MessageBoxBase` with title, reminder-specific text, Cancel, and Delete reminder |
| Fullscreen backdrop | Borderless topmost `QWidget` per target screen with native Windows backdrop and translucent tint; fill the screen rather than available work area |
| Fullscreen category, eyebrow, title, scheduled time | `IconWidget`, `CaptionLabel`, large `QLabel` / `LargeTitleLabel`, and `BodyLabel`; center with stretch layouts and wrap long titles |
| Fullscreen Done and Snooze | `PrimaryPushButton`; `DropDownPushButton` / `PushButton` with `RoundMenu` and `Action` objects for four durations |
| Background dismissal and Escape hint | Parent widget `mousePressEvent`, `QShortcut` for Escape, and `CaptionLabel`; exempt buttons and their menu |
| Reminder entrance and dialog motion | `QPropertyAnimation` / `QParallelAnimationGroup` on opacity and position; optional widget-geometry scale approximation for the fullscreen content only |
| Save/delete/snooze/pause status toast | Small timed `InfoBar` or `StateToolTip`; no persistent animation |
| Focus rings, screen reader names, modal tab loop | Qt focus policy, accessible names/descriptions, `QDialog` modality, `QButtonGroup` keyboard handling, `QAccessible` updates |
| Theme switch | `setTheme(Theme.DARK / Theme.LIGHT)` and `setThemeColor()` plus matching custom surface palette |
| Scheduling and fictional history | Python `datetime` / calendar arithmetic, data model, `QTimer`, notification queue; persistence belongs in a small JSON or SQLite store in production |
| Preview toolbar, desktop shortcut, SVG landscape, fake taskbar/clock/tray | Presentation only. If a native design-review harness is wanted: ordinary `QWidget`, `QPainter` paths/gradients or `QSvgRenderer`, `QToolButton`, and `QTimer`. The shipped app uses the real Windows desktop and tray. |

## Cost and platform simplifications

CSS `backdrop-filter` is the only visual here without a direct lightweight Qt widget equivalent. Use Windows 11 DWM Mica/Acrylic through the native window integration provided by the selected Fluent/frameless-window package. Do not recreate the CSS blur with `QGraphicsBlurEffect`, screenshot the desktop continuously, or render through a browser. If a fullscreen native backdrop is unavailable, use a uniform translucent dark/light tint over the desktop; maintain text contrast. Mica samples the wallpaper and Acrylic samples behind the window, so the precise result will vary with the native backdrop mode.

The CSS wallpaper is painted once as inline SVG. It is presentation scenery and must not ship as a running background layer. Static gradients and 1 px highlights are cheap to paint. Prefer native window shadows over large `QGraphicsDropShadowEffect` surfaces. Cache small decorative paints when useful.

Qt Widgets does not directly scale a layout as a compositor transform. The fullscreen entrance can use opacity plus a 6–8 px translation instead of scale; both communicate the same arrival within 240 ms. Use native-window opacity animation when supported and avoid a large offscreen `QGraphicsOpacityEffect` on an acrylic window. Respect the Windows animation setting as well as an app reduced-motion setting.

For nine reminders, ordinary widgets are sufficient and avoid a web runtime. For larger lists, a model and delegate reduce widget count. Schedule the next deadline with a single-shot timer and use one lightweight minute timer for visible countdowns. Recompute after wake, local-clock changes, and timezone changes. The mockup stays active only while its browser page is open; the production tray process owns persistent scheduling, startup integration, and OS-level fullscreen behavior.

The mockup's native HTML time/date popups vary slightly between Chrome and Edge; their final appearance will be the Qt controls. JS state is intentionally in memory, and no browser permission, network, external package, storage service, or animation engine is required.

## Verification

Checked in the installed Microsoft Edge at 1920 × 1080 and 1366 × 768, with both themes, all three views, and reduced motion. The browser reported no JavaScript errors or external resource requests. Verified empty-title validation, title completion with the keyboard, saving, editing, canceling and confirming deletion, the all-reminders-deleted state, modal focus wrapping, and Escape dismissal.

Clock-controlled checks verified a due reminder, queued delivery during a one-hour pause, automatic resume, sequential delivery, and a five-minute snooze firing. Recurrence checks covered weekday selection, monthly day 31 in February, yearly Feb 29 in a non-leap year, and both the early and birthday notifications. These are browser mockup checks; no Python application or native Windows backdrop was built.
