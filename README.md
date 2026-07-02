# hire-me-bot

A self-updating pipeline that watches company job boards for **SWE/SDE**
internship and new-grad roles in the **USA**, dedupes them, and pushes a
Discord notification for every fresh match -- grouped under Internships and
Full-Time headers. Runs for free on GitHub Actions -- every 3 hours
Tue/Wed/Thu, every 6 hours the rest of the week -- forever (see
[Staying alive forever](#staying-alive-forever)).

Live pages (GitHub Pages, auto-updated every run):
- **[Jobs browser](https://varshiniv1.github.io/hire-me-bot/jobs.html)** --
  tabbed Internships/Full-Time table with Apply links, styled after
  SimplifyJobs' tracker repos.
- **[Application stats calendar](https://varshiniv1.github.io/hire-me-bot/index.html)**
  -- click any day to see how many applications went out that day.

Also auto-committed every run: [`REPORT.md`](REPORT.md), a git-trackable log
of every posting found (so git history itself is a timestamped record).

## What gets tracked

- **Sources**: Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workday
  -- seeded from ~3,200 companies pulled out of the SimplifyJobs
  internship/new-grad tracker repos (`scripts/seed_companies.py`), hand-edited
  from there in [`config/companies.yaml`](config/companies.yaml). Every
  company is crawled and scored identically -- no priority/bias.
- **Role scope**: SWE/SDE only -- titles need "software", "SWE", "SDE",
  "SDET", or a bare "Developer" (Backend/Frontend/.NET Developer etc). Data
  Engineer, ML Engineer, and generic "programmer" are deliberately excluded
  (see `src/hire_me_bot/filtering/keywords.py`).
- **Location**: USA only (`src/hire_me_bot/filtering/location.py`) --
  ambiguous locations (bare "Remote", a city with no state/country, "N/A")
  are excluded rather than guessed at.
- **Experience level**: entry-level/new-grad only -- postings whose JD states
  a minimum of more than `MAX_YEARS_EXPERIENCE` (default 2) years are
  excluded (e.g. "3-5 years of experience"), even if the title itself
  doesn't sound senior (`src/hire_me_bot/filtering/experience.py`).
- **Clearance**: postings requiring a security clearance are excluded, title
  or JD body (`src/hire_me_bot/filtering/clearance.py`).
- **Freshness**: postings are never deleted from the database, but only
  ones posted within the last `NOTIFY_MAX_AGE_DAYS` (default 4) get
  surfaced -- in Discord, `REPORT.md`, and the jobs browser. A listing
  you're only now discovering that's 3 weeks old isn't actionable the way a
  fresh one is.

## Setup

1. Create a free [Supabase](https://supabase.com) project. Run [`sql/schema.sql`](sql/schema.sql)
   in its SQL editor. Copy the project URL and **service role** key.
2. Create a Discord channel and an [incoming webhook](https://support.discord.com/hc/en-us/articles/228383668)
   for it.
3. (Optional for now -- see [Scoring](#scoring)) Have an Anthropic API key handy.
4. Copy `.env.example` to `.env` and fill in `SUPABASE_URL`, `SUPABASE_KEY`,
   `ANTHROPIC_API_KEY`, `DISCORD_WEBHOOK_URL`.
5. `pip install -e ".[dev]"`
6. Fill in [`config/profile.json`](config/profile.json) with your target role
   type, tech stack, and location preferences -- this is what fit-scoring
   uses once it's enabled.
7. Seed your company list: `python scripts/seed_companies.py`. Hand-edit
   [`config/companies.yaml`](config/companies.yaml) afterward to add/remove
   companies.
8. Enable [GitHub Pages](https://docs.github.com/en/pages) for this repo,
   serving from `main` / `/docs`, so the jobs browser and calendar go live.

## Running

- One-off local run: `python -m hire_me_bot.pipeline`
- Scheduled: [`.github/workflows/pipeline.yml`](.github/workflows/pipeline.yml)
  runs it every 3 hours Tue/Wed/Thu and every 6 hours the rest of the week
  (UTC) via GitHub Actions cron, plus supports manual
  `workflow_dispatch`. Add the four secrets above to the repo's Actions
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

## Scoring

Fit-scoring against `config/profile.json` via Claude is built
(`src/hire_me_bot/scoring/`) but **disabled by default**
(`SCORING_ENABLED=false`) -- the Anthropic API requires paid credits, which
a Claude Pro/Max subscription doesn't cover. While disabled, every
keyword-and-location-matched posting gets notified (no score gate) and
`fit_score` stays null. Set `SCORING_ENABLED=true` (and fund the Anthropic
account, or swap in a different provider in `scoring/claude_client.py`) to
turn it back on -- notifications then only fire for postings scoring
`>= FIT_SCORE_NOTIFY_THRESHOLD` (default 4).

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

## Staying alive forever

GitHub auto-disables scheduled workflows after 60 days with no repo
activity. `stats.yml` runs daily and always commits a timestamp file
(`docs/last_updated.txt`) regardless of whether anything else changed,
which guarantees commit activity well under that threshold -- so both cron
workflows keep running indefinitely without any manual upkeep. This repo is
public, so GitHub Actions minutes are free and unlimited either way.
