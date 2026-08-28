-- Dzvonko — Agent Dzvonko-DB (project ref: wzeauydeiddxzcairuxm)
-- Initial schema for the LangGraph job-application automation agent (spec §8).
-- Run via: Supabase Dashboard → SQL Editor, or `supabase db push`.

-- Extensions
create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- users (Supabase auth.users reference)
-- ---------------------------------------------------------------------------
create table if not exists public.users (
  id          uuid primary key references auth.users(id) on delete cascade,
  email       text,
  created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- user_profiles (spec §8) — source of truth for CV facts
-- ---------------------------------------------------------------------------
create table if not exists public.user_profiles (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references public.users(id) on delete cascade,
  full_name           text,
  email               text,
  phone               text,
  location            text,
  headline            text,
  summary             text,
  skills              jsonb not null default '[]'::jsonb,
  experience          jsonb not null default '[]'::jsonb,
  education           jsonb not null default '[]'::jsonb,
  certifications      jsonb not null default '[]'::jsonb,
  languages           jsonb not null default '[]'::jsonb,
  salary_expectation  numeric,
  remote_preference   text,
  cv_url              text,
  portfolio_url       text,
  linkedin_url        text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (user_id)
);

-- ---------------------------------------------------------------------------
-- job_sources — where we discover jobs (LinkedIn API / Greenhouse / custom)
-- ---------------------------------------------------------------------------
create table if not exists public.job_sources (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  kind        text not null default 'http',   -- http | api | manual
  url         text,
  filters     jsonb not null default '{}'::jsonb,
  enabled     boolean not null default true,
  created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- jobs (spec §8 minimum fields)
-- ---------------------------------------------------------------------------
create table if not exists public.jobs (
  id              uuid primary key default gen_random_uuid(),
  source          text not null,
  external_id     text,
  title           text,
  company         text,
  location        text,
  url             text,
  description     text,
  salary_min      numeric,
  salary_max      numeric,
  employment_type text,
  remote_type     text,
  posted_at       timestamptz,
  created_at      timestamptz not null default now(),
  unique (source, external_id)
);

-- ---------------------------------------------------------------------------
-- job_matches — analysis + scoring outcome per user
-- ---------------------------------------------------------------------------
create table if not exists public.job_matches (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references public.users(id) on delete cascade,
  job_id              uuid not null references public.jobs(id) on delete cascade,
  score               numeric not null default 0,
  match_level         text,
  reasons             jsonb not null default '[]'::jsonb,
  missing_req         jsonb not null default '[]'::jsonb,
  recommended         boolean not null default false,
  analysis            jsonb not null default '{}'::jsonb,
  created_at          timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- applications (spec §8 minimum fields)
-- ---------------------------------------------------------------------------
create table if not exists public.applications (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.users(id) on delete cascade,
  job_id          uuid not null references public.jobs(id) on delete cascade,
  status          text not null default 'draft',  -- draft|ready|submitted|cancelled|error
  application_url text,
  match_score     numeric,
  cover_letter    text,
  submitted_at    timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- application_events — audit log / timeline
-- ---------------------------------------------------------------------------
create table if not exists public.application_events (
  id              uuid primary key default gen_random_uuid(),
  application_id  uuid not null references public.applications(id) on delete cascade,
  event_type      text not null,
  payload         jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- agent_runs — observability (spec §17)
-- ---------------------------------------------------------------------------
create table if not exists public.agent_runs (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid,
  workflow      text not null,
  node          text,
  run_id        text,
  started_at    timestamptz,
  finished_at   timestamptz,
  duration_ms   integer,
  status        text,
  error         text,
  created_at    timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- email_messages — outbound emails (spec §10)
-- ---------------------------------------------------------------------------
create table if not exists public.email_messages (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid,
  application_id uuid references public.applications(id) on delete set null,
  recipient     text,
  subject       text,
  body          text,
  provider      text,
  status        text,         -- draft|approved|sent|error
  sent_at       timestamptz,
  created_at    timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------
alter table public.users               enable row level security;
alter table public.user_profiles       enable row level security;
alter table public.job_sources         enable row level security;
alter table public.jobs                enable row level security;
alter table public.job_matches         enable row level security;
alter table public.applications        enable row level security;
alter table public.application_events  enable row level security;
alter table public.agent_runs          enable row level security;
alter table public.email_messages      enable row level security;

-- Broad RLS policy: allow select/insert/update for authenticated users scoped
-- to their own rows where user_id is present. Service-role key bypasses RLS.
-- Tighten these before production (spec §18 least-privilege).

create policy "users_select_own" on public.users
  for select using (auth.uid() = id);

create policy "profiles_select_own" on public.user_profiles
  for select using (auth.uid() = user_id);
create policy "profiles_upsert_own" on public.user_profiles
  for insert with check (auth.uid() = user_id);
create policy "profiles_update_own" on public.user_profiles
  for update using (auth.uid() = user_id);

create policy "applications_select_own" on public.applications
  for select using (auth.uid() = user_id);

-- Public read for anonymous job browsing (adjust to your auth model)
create policy "jobs_select_public" on public.jobs
  for select using (true);
