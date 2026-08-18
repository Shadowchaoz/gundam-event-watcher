# Gundam TCG Event Watcher

Checks a list of local store websites every 30 minutes. If a page changes
(new event posted), it pings a Discord channel via webhook. Runs entirely
on GitHub's free tier — no server of your own needed.

## How it works

- `sites.json` lists the store pages to watch.
- `scraper.py` fetches each page, grabs the text (or just a section of it
  if you give it a CSS `selector`), and hashes it.
- If the hash changed since last time, it posts a message to your Discord
  webhook. First run for a new site just records a baseline — it won't
  alert on the very first check.
- A GitHub Actions workflow runs the script on a schedule and commits the
  updated hashes back to the repo so state persists between runs.

## Setup

1. **Create a Discord webhook**
   In your Discord server: Server Settings → Integrations → Webhooks →
   New Webhook. Pick the channel, copy the webhook URL.

2. **Create a GitHub repo**
   Make a new repo (public is simplest — public repos get unlimited free
   Actions minutes; private works fine too since this only uses a few
   minutes a day). Upload all the files in this folder, keeping the
   folder structure (the `.github/workflows/check-events.yml` path
   matters).

3. **Add the webhook as a secret**
   In the repo: Settings → Secrets and variables → Actions → New
   repository secret. Name it `DISCORD_WEBHOOK_URL`, paste in the
   webhook URL.

4. **Edit `sites.json`**
   Replace the examples with your actual store URLs — the page each
   store posts events/tournaments on. Leave `"selector": ""` to start.

5. **(Optional) Narrow down noisy pages**
   Some sites have things that change constantly for no reason (ads, a
   "today's date" widget, a visitor counter) which would cause false
   alerts. If you get noisy pings, open the page, right-click the
   section that actually lists events → Inspect, and find a CSS
   selector (e.g. `.events-list`, `#tournament-calendar`) that scopes
   to just that part. Put it in `sites.json` for that site.

6. **Test it**
   In the repo: Actions tab → "Check for new Gundam TCG events" →
   Run workflow. Check the logs — it should say "Baseline recorded"
   for each site the first time. Run it again after editing something
   on one of the sites (or just wait for a real change) to confirm you
   get a Discord ping.

After that, it runs automatically every 30 minutes — no further action
needed.

## Notes / limitations

- This detects *any* change to the watched section, not specifically
  "new event." If a store frequently edits unrelated text on the same
  page, you may get some false positives — that's what the `selector`
  option is for.
- Some sites block simple scrapers or require JavaScript to render
  content. If a site returns errors or the scraper can't see the
  event text at all (check the Action logs), it may need a different
  approach (e.g. Playwright), that this simple script doesn't cover.
- 30-minute checks fit comfortably in the free Actions minutes quota.
  You can loosen the schedule (e.g. hourly) by editing the `cron` line
  if you want to be extra conservative.
