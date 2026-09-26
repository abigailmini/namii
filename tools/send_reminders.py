#!/usr/bin/env python3
"""Daily NAMII roadmap reminder.

Reads progress/milestones.json and emails a digest when a milestone is
N days away (N from reminders.days_before, e.g. 7/3/1/0), and lists overdue
items the day after they slip and every Monday until marked done.

Environment:
  SMTP_USER       sender login, e.g. you@gmail.com
  SMTP_PASSWORD   app password (Gmail: Google Account → Security → App passwords)
  MAIL_TO         comma-separated recipients (defaults to SMTP_USER)
  SMTP_HOST       default smtp.gmail.com
  SMTP_PORT       default 465 (SSL)
  SITE_URL        optional link to the roadmap page

Usage:
  python tools/send_reminders.py                 # normal daily run
  python tools/send_reminders.py --dry-run       # print, don't send
  python tools/send_reminders.py --date 2026-10-08 --dry-run
  python tools/send_reminders.py --test          # always send (next 14 days)
"""
import argparse
import json
import os
import smtplib
import sys
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "progress" / "milestones.json"


def fmt(d):
    return d.strftime("%a %d %b")


def when(days):
    if days == 0:
        return "TODAY"
    if days == 1:
        return "tomorrow"
    if days > 0:
        return f"in {days} days"
    return f"{-days} day{'s' if days != -1 else ''} overdue"


def build(data, today, test=False):
    cats = data["categories"]
    rem = data.get("reminders", {})
    offsets = set(rem.get("days_before", [7, 3, 1, 0]))
    monday = today.weekday() == 0

    upcoming, overdue = [], []
    for m in data["milestones"]:
        if m.get("done"):
            continue
        due = date.fromisoformat(m["due"])
        days = (due - today).days
        m = {**m, "_due": due, "_days": days, "_cat": cats.get(m["category"], m["category"])}
        if days >= 0 and (days in offsets or (test and days <= 14)):
            upcoming.append(m)
        elif days < 0 and (days == -1 or test or (monday and rem.get("overdue_on_mondays", True))):
            overdue.append(m)

    upcoming.sort(key=lambda m: m["_days"])
    overdue.sort(key=lambda m: m["_days"])
    return upcoming, overdue


def render(data, today, upcoming, overdue, site_url):
    opening = date.fromisoformat(data["opening"])
    to_open = (opening - today).days
    total = len(data["milestones"])
    done = sum(1 for m in data["milestones"] if m.get("done"))

    first = (upcoming or overdue)[0]
    if overdue and not upcoming:
        subject = f"NAMII · {len(overdue)} overdue: {overdue[0]['title']}"
    else:
        subject = f"NAMII · {first['title']} — {when(first['_days'])}"
        extra = len(upcoming) + len(overdue) - 1
        if extra > 0:
            subject += f" (+{extra} more)"

    # Plain text
    lines = [f"NAMII 鮨 roadmap — {fmt(today)}", f"{to_open} days to opening · {done}/{total} done", ""]
    if upcoming:
        lines.append("COMING UP")
        for m in upcoming:
            lines.append(f"  • {fmt(m['_due'])} ({when(m['_days'])}) — {m['title']} [{m['_cat']}]")
            if m.get("note") and m.get("flag") == "risk":
                lines.append(f"      ⚠ {m['note']}")
        lines.append("")
    if overdue:
        lines.append("OVERDUE — mark done in milestones.json or move the date")
        for m in overdue:
            lines.append(f"  • {fmt(m['_due'])} ({when(m['_days'])}) — {m['title']} [{m['_cat']}]")
        lines.append("")
    if site_url:
        lines.append(f"Full roadmap: {site_url}")
    text = "\n".join(lines)

    # HTML
    def rows(items, accent):
        out = []
        for m in items:
            note = ""
            if m.get("note") and m.get("flag") == "risk":
                note = (f'<div style="margin-top:6px;font-size:13px;color:#8a4b2a;line-height:1.5">'
                        f'⚠ {escape(m["note"])}</div>')
            out.append(
                f'<tr><td style="padding:14px 0;border-top:1px solid #e5d8c4;vertical-align:top;width:92px">'
                f'<div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#8c7562">{m["_due"].strftime("%a")}</div>'
                f'<div style="font-family:Georgia,serif;font-size:22px;color:#2b1b12">{m["_due"].strftime("%d %b")}</div></td>'
                f'<td style="padding:14px 0;border-top:1px solid #e5d8c4;vertical-align:top">'
                f'<div style="font-size:15px;color:#2b1b12;font-weight:600">{escape(m["title"])}</div>'
                f'<div style="font-size:12px;color:#8c7562;margin-top:3px">{escape(m["_cat"])} · '
                f'<b style="color:{accent}">{when(m["_days"])}</b></div>{note}</td></tr>'
            )
        return "".join(out)

    section = lambda title, body: (
        f'<div style="font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:#8c7562;margin:28px 0 4px">{title}</div>'
        f'<table style="width:100%;border-collapse:collapse">{body}</table>'
    )
    parts = []
    if upcoming:
        parts.append(section("Coming up", rows(upcoming, "#a6774d")))
    if overdue:
        parts.append(section("Overdue", rows(overdue, "#b3261e")))
    link = (f'<p style="margin-top:28px"><a href="{escape(site_url)}" style="display:inline-block;background:#2b1b12;'
            f'color:#f5f0e7;padding:12px 22px;text-decoration:none;font-size:13px;letter-spacing:.12em;'
            f'text-transform:uppercase">Open roadmap</a></p>') if site_url else ""
    html = f"""<!doctype html><html><body style="margin:0;background:#f5f0e7;font-family:Helvetica,Arial,sans-serif">
<div style="max-width:560px;margin:0 auto;padding:32px 24px">
<div style="font-family:Georgia,serif;font-size:28px;letter-spacing:.35em;color:#2b1b12">NAMII <span style="letter-spacing:0">鮨</span></div>
<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#8c7562;margin-top:6px">Opening roadmap · {fmt(today)}</div>
<div style="margin-top:22px;padding:16px 18px;background:#2b1b12;color:#f5f0e7">
<span style="font-family:Georgia,serif;font-size:30px">{to_open}</span>
<span style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;opacity:.8">&nbsp;days to opening &nbsp;·&nbsp; {done}/{total} done</span></div>
{''.join(parts)}{link}
<p style="font-size:11px;color:#8c7562;margin-top:32px;line-height:1.6">You get this email 7, 3 and 1 day before each milestone and on the day.
Mark items done in <code>progress/milestones.json</code> to stop reminders.</p>
</div></body></html>"""
    return subject, text, html


def send(subject, text, html):
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASSWORD"]
    to = [a.strip() for a in os.environ.get("MAIL_TO", user).split(",") if a.strip()]
    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or 465)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"NAMII Roadmap <{user}>"
    msg["To"] = ", ".join(to)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    if port == 465:
        with smtplib.SMTP_SSL(host, port) as s:
            s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
    print(f"Sent to {', '.join(to)}: {subject}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="pretend today is YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", action="store_true", help="send even if nothing is due (next 14 days)")
    args = ap.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    tz = timezone(timedelta(hours=data.get("timezone_offset_hours", 8)))
    today = date.fromisoformat(args.date) if args.date else datetime.now(tz).date()

    upcoming, overdue = build(data, today, test=args.test)
    if not upcoming and not overdue:
        print(f"{today}: nothing to remind.")
        return 0

    subject, text, html = render(data, today, upcoming, overdue, os.environ.get("SITE_URL", ""))
    if args.dry_run:
        print("Subject:", subject)
        print(text)
        return 0
    send(subject, text, html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
