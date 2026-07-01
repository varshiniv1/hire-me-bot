from functools import lru_cache

from supabase import Client, create_client

from hire_me_bot import settings


@lru_cache(maxsize=1)
def get_client() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set (in .env or the environment) "
            "to use the database."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
