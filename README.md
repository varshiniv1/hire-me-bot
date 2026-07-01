# hire-me-bot

A self-updating pipeline that watches company job boards for SWE internship and
new-grad roles, dedupes them, scores fit against your profile with Claude, and
pushes a Discord notification for strong matches. Runs for free every 3 hours
on GitHub Actions.

## Setup

1. Create a free [Supabase](https://supabase.com) project. Run [`sql/schema.sql`](sql/schema.sql)
   in its SQL editor. Copy the project URL and **service role** key.
2. Create a Discord channel and an [incoming webhook](https://support.discord.com/hc/en-us/articles/228383668)
   for it.
3. Have an Anthropic API key handy.
4. Copy `.env.example` to `.env` and fill in `SUPABASE_URL`, `SUPABASE_KEY`,
   `ANTHROPIC_API_KEY`, `DISCORD_WEBHOOK_URL`.
5. `pip install -e ".[dev]"`
6. Fill in [`config/profile.json`](config/profile.json) with your target role
   type, tech stack, and location preferences -- this is what Claude scores
   every posting's fit against.
7. Seed your company list: `python scripts/seed_companies.py` (pulls from the
   SimplifyJobs internship/new-grad tracker repos). Hand-edit
   [`config/companies.yaml`](config/companies.yaml) afterward to add/remove
   companies -- every company in it is crawled and scored identically.

## Running

- One-off local run: `python -m hire_me_bot.pipeline`
- Scheduled: `.github/workflows/pipeline.yml` runs it every 3 hours via GitHub
  Actions cron, plus supports manual `workflow_dispatch`. Add the four secrets
  above to the repo's Actions secrets for this to work in CI.

## Tracking applications

`python scripts/track.py <company> <status>` -- fuzzy-matches the company name
against all stored postings and updates its status. `status` accepts
`applied`/`interviewing`/`rejected`/`offer` or the shorthand `a`/`i`/`r`/`o`.

`python scripts/track.py` with no arguments lists postings you haven't applied
to yet, lets you pick one, then pick a status.

Optional PowerShell alias (add to your `$PROFILE`):

```powershell
function track { python scripts/track.py @args }
```

## Full status view

`python scripts/report.py` writes `REPORT.md` with every scored posting
(company, title, score, status, first seen, link) -- including low scores that
never triggered a Discord notification.
