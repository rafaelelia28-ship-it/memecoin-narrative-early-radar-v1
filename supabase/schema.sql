create table if not exists public.signals (
  id text primary key,
  title text not null,
  url text not null,
  source_name text not null,
  summary text default '',
  published_at timestamptz not null,
  first_seen_at timestamptz not null default now(),
  narrative_slug text not null,
  narrative_title text not null,
  category text not null
);

create index if not exists signals_published_at_idx on public.signals (published_at desc);
create index if not exists signals_narrative_slug_idx on public.signals (narrative_slug);

create table if not exists public.narratives (
  slug text primary key,
  title text not null,
  category text not null,
  score integer not null default 0 check (score between 0 and 100),
  mentions_24h integer not null default 0,
  sources_count integer not null default 0,
  source_names text[] not null default '{}',
  first_seen_at timestamptz,
  last_seen_at timestamptz,
  saturation text not null default 'Unknown',
  stage text not null default 'Observing',
  sample_evidence jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.daily_reports (
  report_date date primary key,
  narratives_count integer not null default 0,
  top_narratives jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.signals enable row level security;
alter table public.narratives enable row level security;
alter table public.daily_reports enable row level security;

drop policy if exists "Public read signals" on public.signals;
create policy "Public read signals" on public.signals for select to anon, authenticated using (true);

drop policy if exists "Public read narratives" on public.narratives;
create policy "Public read narratives" on public.narratives for select to anon, authenticated using (true);

drop policy if exists "Public read daily reports" on public.daily_reports;
create policy "Public read daily reports" on public.daily_reports for select to anon, authenticated using (true);

-- No public insert/update/delete policies. Only the server-side service role used by GitHub Actions writes data.
grant select on public.signals, public.narratives, public.daily_reports to anon, authenticated;
