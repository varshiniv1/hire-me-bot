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
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    constraint postings_dedup_key unique (source, company, external_id)
);

create index if not exists idx_postings_status on postings (status);
create index if not exists idx_postings_fit_score on postings (fit_score);
create index if not exists idx_postings_notified_at on postings (notified_at) where notified_at is null;
create index if not exists idx_postings_first_seen_at on postings (first_seen_at);

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
