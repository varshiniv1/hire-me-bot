import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]

# Not required at import time -- scripts that don't touch Supabase/Claude/Discord
# (e.g. seed_companies.py, which is filesystem-only by design) must be able to
# import this module without those secrets configured. Whatever actually uses
# a given value (db/client.py, scoring/claude_client.py, notify/discord.py)
# is responsible for failing clearly if it's missing.
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

FIT_SCORE_NOTIFY_THRESHOLD = int(os.environ.get("FIT_SCORE_NOTIFY_THRESHOLD", "4"))

COMPANIES_CONFIG_PATH = REPO_ROOT / "config" / "companies.yaml"
PROFILE_CONFIG_PATH = REPO_ROOT / "config" / "profile.json"

# Batching thresholds for scoring/scorer.py
BATCH_SCORING_TRIGGER = 15
BATCH_SIZE = 6

# scoring/jd_extract.py fallback truncation length when no requirements section is found
JD_FALLBACK_TRUNCATE_CHARS = 1500

CLAUDE_MODEL = "claude-sonnet-5"
