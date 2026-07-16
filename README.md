# Hekal Work Tracker

### Track sessions. Know your hours. Own your pay.

A clean desktop work-hours tracker for freelancers, contractors, and anyone paid by the hour — with overtime, payroll periods, Excel backup, and full data ownership.

**Version 1.1.1** · macOS app · Arabic-first UI · 100% local · Open source

---

## Why Hekal Work Tracker?

Most people lose money in the gaps: forgotten sessions, messy notes, unclear overtime, and Excel sheets that never stay up to date.

Hekal Work Tracker turns work time into clear numbers:

- Start / stop sessions with one click
- See today and the current payroll month at a glance
- Split **regular** vs **overtime** hours automatically
- Export everything when you need it
- Adjust hours manually when real life doesn’t match the timer

No cloud. No account. Your data stays on your Mac.

---

## Features

| Feature | What you get |
|--------|---------------|
| **Live timer** | Start and end sessions instantly |
| **Daily summary** | Hours, overtime, earnings, session count |
| **Custom payroll month** | Default period: day 17 → day 16 (fully configurable) |
| **Day details** | Per-session start/end times + regular/OT breakdown |
| **Manual adjustments** | Add or deduct **regular** or **overtime** hours with date + reason |
| **Excel sync** | Automatic daily backup + restore |
| **Full export** | One-click export of all history (Excel + JSON) |
| **Local privacy** | JSON + Excel on your machine only |

---

## Screenshots / Product feel

Dark, focused UI designed for daily use — timer up top, today’s numbers in the middle, monthly history below, actions in the footer.

---

## Quick start (macOS app)

1. Build the app:

```bash
chmod +x scripts/build_mac.sh
./scripts/build_mac.sh
```

2. Open it:

```bash
open "dist/Hekal Work Tracker.app"
```

3. Or create a DMG installer:

```bash
chmod +x scripts/build_dmg.sh
./scripts/build_dmg.sh
```

Then drag **Hekal Work Tracker** into Applications.

> First launch on macOS (unsigned build): right-click the app → **Open**, or run:
>
> ```bash
> xattr -cr "dist/Hekal Work Tracker.app"
> ```

---

## Run from source

```bash
pip install -r requirements.txt
python3 app.py
```

Requirements: Python 3.10+

---

## How pay is calculated

For each day:

1. All tracked sessions are summed
2. The first *N* hours (default **4**) count as **regular**
3. Anything beyond that counts as **overtime**
4. Manual adjustments apply to the hour type you choose (regular or overtime)

Default rates (editable in Settings):

- Regular: **$10 / hour**
- Overtime: **$35 / hour**
- Payroll month start day: **17**

---

## Where your data lives

| Mode | Location |
|------|----------|
| Development | `data/work_sessions.json` + `data/work_hours_backup.xlsx` |
| Built macOS app | `~/Library/Application Support/HekalWorkTracker/data/` |

Excel sheets include settings, sessions, manual adjustments, daily summaries, and monthly rollups.

---

## Who it’s for

- Freelancers tracking billable time
- Contractors with overtime rules
- Remote workers with custom payroll cycles
- Anyone who wants a private, simple hour ledger

---

## Project structure

```
app.py              # UI
core.py             # Hours, overtime, earnings logic
storage.py          # JSON persistence
excel_sync.py       # Excel backup / restore / export
ui_theme.py         # Dark theme widgets
ui_responsive.py    # Responsive layout
scripts/            # macOS .app + DMG builders
```

---

## Contributing

Issues and pull requests are welcome. Keep changes focused, tested, and privacy-first (no telemetry, no cloud uploads).

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest test_core.py test_excel_sync.py -q
```

---

## License

MIT — free to use, share, and improve.

Built by **Mohamed Hekal**.
