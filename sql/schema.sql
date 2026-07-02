-- Run this once in the Supabase SQL editor for your project.

create table if not exists postings (
    id              bigint generated always as identity primary key,
    source          text not null,               -- greenhouse|lever|ashby|smartrecruiters|recruitee|workday
    external_id     text not null,
    company         text not null,
    title           text not null,
    location        text,
    url             text not null,
    description     text not null,               -- full JD, never discarded
    posted_at       timestamptz,
    first_seen_at   timestamptz not null default now(),
    status          text not null default 'not_applied'
                        check (status in ('not_applied','applied','interviewing','rejected','offer')),
    fit_score       smallint check (fit_score between 1 and 5),
    scored_at       timestamptz,
    notified_at     timestamptz,                 -- null = not yet Discord-notified
    applied_at      timestamptz,                 -- set the moment status becomes 'applied' (for the stats calendar)
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    constraint postings_dedup_key unique (source, company, external_id)
);

create index if not exists idx_postings_status on postings (status);
create index if not exists idx_postings_fit_score on postings (fit_score);
create index if not exists idx_postings_notified_at on postings (notified_at) where notified_at is null;
create index if not exists idx_postings_first_seen_at on postings (first_seen_at);
create index if not exists idx_postings_applied_at on postings (applied_at) where applied_at is not null;

create or replace function set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_postings_updated_at on postings;
create trigger trg_postings_updated_at
before update on postings
for each row execute function set_updated_at();

-- Lets the GitHub Pages job browser (docs/jobs.html) mark a posting
-- applied using the public anon key, embedded client-side by design.
-- Supabase already grants anon broad column-level privileges on every
-- table by default (a platform default, not something set up here) --
-- Row Level Security below is the actual gatekeeper. service_role (used
-- server-side in GitHub Actions) bypasses RLS entirely and is unaffected.
alter table postings enable row level security;

grant update (status, applied_at) on postings to anon;
-- applied_at also SELECT-granted (not just id/status) so the GitHub Pages
-- stats page (docs/index.html) can query real application timestamps
-- directly from Supabase and render live, instead of only reflecting a
-- once-daily static docs/stats.json snapshot. Just a timestamp, not
-- sensitive -- company/title/description/url are still never exposed.
grant select (id, status, applied_at) on postings to anon;

-- A SELECT policy is required for the UPDATE below to work at all: without
-- one, RLS blocks all row visibility for anon (including the UPDATE
-- policy's own USING clause), so the update silently matches zero rows
-- while PostgREST still reports success. And it must cover BOTH
-- not_applied and applied: Postgres requires the post-update row to also
-- satisfy the SELECT policy, not just the UPDATE policy's WITH CHECK, so
-- restricting this to only 'not_applied' makes every update fail with
-- "new row violates row-level security policy" even though the WITH CHECK
-- condition itself is satisfied. (Confirmed both failure modes against a
-- throwaway scratch table before settling on this.) Company/title/
-- description/url etc are not exposed by this -- the page reads full
-- listings from the pre-generated jobs.json instead, this policy only
-- covers the id/status/applied_at columns actually granted above.
drop policy if exists "anon can see not_applied postings" on postings;
drop policy if exists "anon can see own status postings" on postings;
create policy "anon can see own status postings"
on postings
for select
to anon
using (status in ('not_applied', 'applied'));

drop policy if exists "anon can mark postings applied" on postings;
create policy "anon can mark postings applied"
on postings
for update
to anon
using (status = 'not_applied')
with check (status = 'applied');
