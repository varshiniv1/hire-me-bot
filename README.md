# hire-me-bot

[![Pipeline](https://github.com/varshiniv1/hire-me-bot/actions/workflows/pipeline.yml/badge.svg)](https://github.com/varshiniv1/hire-me-bot/actions/workflows/pipeline.yml)
[![Stats](https://github.com/varshiniv1/hire-me-bot/actions/workflows/stats.yml/badge.svg)](https://github.com/varshiniv1/hire-me-bot/actions/workflows/stats.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

A self-updating pipeline that watches company job boards for **SWE/SDE**
internship and new-grad roles in the **USA**, dedupes them, and pushes a
Discord notification for every fresh match -- grouped under Internships and
Full-Time headers. Runs for free on GitHub Actions -- every 3 hours
Tue/Wed/Thu, every 6 hours the rest of the week.

## Contents

- [What gets tracked](#what-gets-tracked)
- [Setup](#setup)
- [Running](#running)
- [Notifications](#notifications)
- [Tracking applications](#tracking-applications)
- [Full status view](#full-status-view)

Live pages (GitHub Pages, auto-updated every run):
- **[Jobs browser](https://varshiniv1.github.io/hire-me-bot/jobs.html)** --
  tabbed Internships/Full-Time table with Apply links, styled after
  SimplifyJobs' tracker repos, plus a third **Applied** tab tracking your
  full application history (company, role, status, and the date you
  applied) so it's never lost once a posting drops out of the other tabs.
- **[Application stats calendar](https://varshiniv1.github.io/hire-me-bot/index.html)**
  -- click any day to see how many applications went out that day, updates
  live from Supabase on every page load.

Also auto-committed every run: [`REPORT.md`](REPORT.md), a git-trackable log
of every posting found (so git history itself is a timestamped record).

## What gets tracked

- **Sources**: Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workday
  -- seeded from ~3,200 companies pulled out of the SimplifyJobs
  internship/new-grad tracker repos (`scripts/seed_companies.py`), hand-edited
  from there in [`config/companies.yaml`](config/companies.yaml). Every
  company is crawled and scored identically -- no priority/bias. A weekly
  workflow (`.github/workflows/reseed-companies.yml`) merges in any new
  companies those repos add, without ever undoing hand-edits (renamed
  tokens, removed staffing agencies -- see
  [`config/excluded_companies.yaml`](config/excluded_companies.yaml)).
  Optionally, [JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
  (Google for Jobs) adds a 7th, query-keyed source that catches companies
  with none of the above ATS platforms -- disabled by default, enable by
  adding a `RAPIDAPI_KEY` repo secret (see `src/hire_me_bot/connectors/jsearch.py`).
  Results that duplicate a company already covered by a direct ATS
  connector are skipped in favor of the more complete direct-connector data.
  LinkedIn/Indeed are not scraped directly (against their ToS).
- **Role scope**: Software Engineer, SRE/Production Engineer, and Backend/
  Frontend/Full-Stack roles only -- titles need "software", "SWE", "SDE",
  "SDET", "site reliability"/"SRE", "production engineer", "backend",
  "frontend", or "full-stack". A bare "Developer" is no longer sufficient
  on its own (that used to catch things like "Salesforce Developer",
  "ServiceNow Developer", ".NET Developer", which aren't general SWE roles).
  Data Engineer, ML Engineer, generic "programmer", Embedded/Firmware, and
  Scientific Software roles are deliberately excluded. Titles signaling
  Engineer III+/L3+/Level 3+ (3+ years tiers) or "Lead"/"Leader" are also
  excluded (see `src/hire_me_bot/filtering/keywords.py`).
- **Location**: USA only (`src/hire_me_bot/filtering/location.py`) --
  ambiguous locations (bare "Remote", a city with no state/country, "N/A")
  are excluded rather than guessed at.
- **Experience level**: entry-level/new-grad only, strictly up to
  `MAX_YEARS_EXPERIENCE` (default 2) years -- postings whose JD states a
  requirement above that are excluded (e.g. "3-5 years of experience"), even
  if the title itself doesn't sound senior. For a range like "1-3 years",
  the upper bound (3) is what's checked against the cap, not just the lower
  bound -- a role open to candidates with up to 3 years doesn't qualify as
  strictly entry-level even though its floor is low
  (`src/hire_me_bot/filtering/experience.py`).
- **Clearance**: postings requiring a security clearance are excluded, title
  or JD body (`src/hire_me_bot/filtering/clearance.py`).
- **Citizenship**: postings requiring U.S. citizenship (not just work
  authorization) are excluded, title or JD body
  (`src/hire_me_bot/filtering/citizenship.py`).
- **Freshness**: postings are never deleted from the database, but only
  recent ones get surfaced -- within `NOTIFY_MAX_AGE_DAYS` (default 6) for
  Discord and `REPORT.md`, and within `JOBS_MAX_AGE_DAYS` (default 7) for
  the jobs browser, which you check back on rather than getting pinged
  from, so it can hold postings a little longer. A listing you're only now
  discovering that's 3 weeks old isn't actionable the way a fresh one is.

## Setup

1. Create a free [Supabase](https://supabase.com) project. Run [`sql/schema.sql`](sql/schema.sql)
   in its SQL editor. Copy the project URL and **service role** key.
2. Create a Discord channel and an [incoming webhook](https://support.discord.com/hc/en-us/articles/228383668)
   for it.
3. Copy `.env.example` to `.env` and fill in `SUPABASE_URL`, `SUPABASE_KEY`,
   `DISCORD_WEBHOOK_URL`.
4. `pip install -e ".[dev]"`
5. Seed your company list: `python scripts/seed_companies.py`. Hand-edit
   [`config/companies.yaml`](config/companies.yaml) afterward to add/remove
   companies.
6. Enable [GitHub Pages](https://docs.github.com/en/pages) for this repo,
   serving from `main` / `/docs`, so the jobs browser and calendar go live.

## Running

- One-off local run: `python -m hire_me_bot.pipeline`
- Scheduled: [`.github/workflows/pipeline.yml`](.github/workflows/pipeline.yml)
  runs it every 3 hours Tue/Wed/Thu and every 6 hours the rest of the week
  (UTC) via GitHub Actions cron, plus supports manual
  `workflow_dispatch`. Add the secrets above to the repo's Actions
  secrets for this to work in CI.
- [`.github/workflows/stats.yml`](.github/workflows/stats.yml) regenerates
  the application-stats calendar data once a day.

## Notifications

Every run, Discord gets:
1. An **Internships** header + a card per new internship posting (if any).
2. A **Full-Time** header + a card per new full-time posting (if any).
3. A one-line heartbeat summary (`Pipeline run at ... -- N posting(s)
   fetched, M new notification(s) sent`), sent every run even when nothing
   new was found, so silence never means "is this still running?"

Each job card is just the role/company (as the link), location, and how
long ago it was posted -- no clutter.

## Tracking applications

`python scripts/track.py <company> <status>` -- fuzzy-matches the company name
against all stored postings and updates its status. `status` accepts
`applied`/`interviewing`/`rejected`/`offer` or the shorthand `a`/`i`/`r`/`o`.
Marking something `applied` records the day for the stats calendar.

`python scripts/track.py` with no arguments lists postings you haven't applied
to yet, lets you pick one, then pick a status.

Optional PowerShell alias (add to your `$PROFILE`):

```powershell
function track { python scripts/track.py @args }
```

## Full status view

`python scripts/report.py` writes [`REPORT.md`](REPORT.md) -- Internships and
Full-Time sections, each with company, role, location, source platform,
status, an Apply link, and age. Also regenerated automatically every
scheduled run.

`python scripts/generate_jobs_json.py` regenerates `docs/jobs.json`, which
feeds the [jobs browser](https://varshiniv1.github.io/hire-me-bot/jobs.html)
page.
