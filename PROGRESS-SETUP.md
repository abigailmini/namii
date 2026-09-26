# NAMII Progress — setup

Roadmap page for the omakase opening, plus daily email reminders.

```
progress/index.html        the page
progress/milestones.json   all dates, notes and done/not-done (edit this)
progress/assets/           logo
tools/send_reminders.py    reminder email script (Python, no dependencies)
.github/workflows/roadmap-reminders.yml   runs the script daily at 8:17am MYT
```

## 1. Put the page online at `namiiprogress` (free, ~5 min)

1. https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. Pick `abigailmini/namii`
3. Settings:
   - **Project name:** `namiiprogress`  → gives you **https://namiiprogress.pages.dev**
   - **Production branch:** `main`
   - **Build command:** *(empty)*
   - **Build output directory:** `progress`
4. **Save and Deploy**

**Own domain (optional):** register `namiiprogress.com` (Cloudflare Registrar is about US$10/yr).
Then go to the Pages project → **Custom domains** → add `namiiprogress.com`.

**Keep it private (recommended):** this page shows your internal plan. Go to the Pages project →
**Settings** → **Access policy** → enable Cloudflare Access. It's free for up to 50 users and lets you
allow only your email addresses. The page also sets `noindex` so search engines skip it.

## 2. Turn on email reminders

Gmail is used as the sender.

1. Turn on 2-Step Verification on the Google account, then create an **App password**
   at https://myaccount.google.com/apppasswords (name it "NAMII roadmap").
2. On GitHub, go to `abigailmini/namii` → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

   | Secret | Value |
   |---|---|
   | `SMTP_USER` | the Gmail address that sends |
   | `SMTP_PASSWORD` | the 16-character app password |
   | `MAIL_TO` | who receives the reminders, comma-separated (e.g. `davidyangmini@gmail.com, partner@…`) |

   Optional: the **Variables** tab → `SITE_URL` = your final page URL (the default is `https://namiiprogress.pages.dev`).
3. Test it: go to **Actions** → **Roadmap reminders** → **Run workflow** (keep "test" ticked).
   You should get an email right away listing the next 14 days.

After that it runs by itself every morning. It **only emails when something is due**:
7 days, 3 days and 1 day before, and on the day. Overdue items come back the day after they slip
and every Monday until they're done.

Other providers work too. Set `SMTP_HOST` / `SMTP_PORT` secrets
(e.g. Outlook `smtp.office365.com` / `587`).

## 3. Update progress

Edit `progress/milestones.json` on GitHub (the page's **Edit roadmap** button opens it):

- finished something → change `"done": false` to `"done": true`
- date moved → change `"due"`
- new task → copy a block and give it a new `id`

Commit to `main`. The page redeploys in about a minute and the next day's email uses the new dates.

Check a day's email locally without sending it:

```
python3 tools/send_reminders.py --date 2026-10-08 --dry-run
```
