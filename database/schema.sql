-- AIFX Phase 1 Supabase setup
-- Run this in the Supabase SQL editor after creating the project.

create extension if not exists "pgcrypto";

create table if not exists public.task_history (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null,
    user_id uuid not null references auth.users(id) on delete cascade,
    filename text not null,
    status text not null default 'completed',
    original_image_url text not null,
    cropped_image_urls jsonb not null default '[]'::jsonb,
    bounding_boxes jsonb not null default '[]'::jsonb,
    face_count integer not null default 0,
    image_width integer,
    image_height integer,
    settings jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists task_history_user_created_at_idx
    on public.task_history (user_id, created_at desc);

alter table public.task_history enable row level security;

drop policy if exists "Users can read their own task history" on public.task_history;
create policy "Users can read their own task history"
    on public.task_history
    for select
    using (auth.uid() = user_id);

drop policy if exists "Users can insert their own task history" on public.task_history;
create policy "Users can insert their own task history"
    on public.task_history
    for insert
    with check (auth.uid() = user_id);

insert into storage.buckets (id, name, public)
values ('face-processing', 'face-processing', true)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values
    ('aifx-originals', 'aifx-originals', true),
    ('aifx-crops', 'aifx-crops', true),
    ('aifx-enhanced-crops', 'aifx-enhanced-crops', true),
    ('aifx-enhanced-originals', 'aifx-enhanced-originals', true)
on conflict (id) do nothing;

drop policy if exists "Users can read face-processing files" on storage.objects;
create policy "Users can read face-processing files"
    on storage.objects
    for select
    using (bucket_id = 'face-processing');

drop policy if exists "Users can upload their own face-processing files" on storage.objects;
create policy "Users can upload their own face-processing files"
    on storage.objects
    for insert
    with check (
        bucket_id = 'face-processing'
        and auth.uid()::text = (storage.foldername(name))[1]
    );

drop policy if exists "Users can read AIFX phase2 files" on storage.objects;
create policy "Users can read AIFX phase2 files"
    on storage.objects
    for select
    using (
        bucket_id in (
            'aifx-originals',
            'aifx-crops',
            'aifx-enhanced-crops',
            'aifx-enhanced-originals'
        )
    );

drop policy if exists "Users can upload their own AIFX phase2 files" on storage.objects;
create policy "Users can upload their own AIFX phase2 files"
    on storage.objects
    for insert
    with check (
        bucket_id in (
            'aifx-originals',
            'aifx-crops',
            'aifx-enhanced-crops',
            'aifx-enhanced-originals'
        )
        and auth.uid()::text = (storage.foldername(name))[1]
    );

create table if not exists public.enhancement_jobs (
    job_id text primary key,
    user_id text not null,
    status text not null default 'queued',
    source_filename text,
    character_id text,
    prompt text not null default '',
    original_bucket text,
    original_path text,
    original_url text,
    crop_bucket text,
    crop_path text,
    crop_url text,
    enhanced_crop_bucket text,
    enhanced_crop_path text,
    enhanced_crop_url text,
    enhanced_original_bucket text,
    enhanced_original_path text,
    enhanced_original_url text,
    crop_bbox jsonb not null default '{}'::jsonb,
    face_bbox jsonb not null default '{}'::jsonb,
    comfy_input_filename text,
    comfy_input_subfolder text,
    comfy_input_type text,
    comfy_prompt_id text,
    retry_count integer not null default 0,
    max_retries integer not null default 3,
    next_retry_at timestamptz,
    last_error text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    completed_at timestamptz,
    constraint enhancement_jobs_job_id_format
        check (job_id ~ '^[0-9]{8}_[0-9]{2,}$')
);

alter table public.enhancement_jobs
    add column if not exists comfy_input_filename text,
    add column if not exists comfy_input_subfolder text,
    add column if not exists comfy_input_type text,
    add column if not exists feather_radius integer not null default 24;

create table if not exists public.enhancement_job_counters (
    job_date date primary key,
    last_value integer not null default 0
);

create or replace function public.next_enhancement_job_id()
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
    today date := current_date;
    next_value integer;
begin
    insert into public.enhancement_job_counters (job_date, last_value)
    values (today, 1)
    on conflict (job_date)
    do update set last_value = enhancement_job_counters.last_value + 1
    returning last_value into next_value;

    return to_char(today, 'YYYYMMDD') || '_' || lpad(next_value::text, 2, '0');
end;
$$;

revoke all on function public.next_enhancement_job_id() from public;
grant execute on function public.next_enhancement_job_id() to authenticated, service_role;

create table if not exists public.enhancement_job_faces (
    id uuid primary key default gen_random_uuid(),
    job_id text not null references public.enhancement_jobs(job_id) on delete cascade,
    user_id text not null,
    face_id text not null,
    output_index integer not null,
    status text not null default 'queued',
    character_id text not null,
    prompt text not null default '',
    crop_bbox jsonb not null,
    face_bbox jsonb not null default '{}'::jsonb,
    crop_bucket text not null,
    crop_path text not null,
    crop_url text not null,
    enhanced_crop_bucket text,
    enhanced_crop_path text,
    enhanced_crop_url text,
    comfy_input_filename text,
    comfy_input_subfolder text,
    comfy_input_type text,
    comfy_prompt_id text,
    comfy_output jsonb not null default '{}'::jsonb,
    retry_count integer not null default 0,
    max_retries integer not null default 3,
    next_retry_at timestamptz,
    last_error text,
    runtime_seconds numeric,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    completed_at timestamptz,
    unique (job_id, face_id),
    unique (job_id, output_index)
);

create index if not exists enhancement_job_faces_job_idx
    on public.enhancement_job_faces (job_id, output_index);

drop index if exists enhancement_job_faces_queue_idx;
create index enhancement_job_faces_queue_idx
    on public.enhancement_job_faces (status, next_retry_at, created_at)
    where status in ('queued', 'retrying');

alter table public.enhancement_job_faces enable row level security;

drop policy if exists "Users can read their own enhancement faces" on public.enhancement_job_faces;
create policy "Users can read their own enhancement faces"
    on public.enhancement_job_faces
    for select
    using (auth.uid()::text = user_id);

drop policy if exists "Users can insert their own enhancement faces" on public.enhancement_job_faces;
create policy "Users can insert their own enhancement faces"
    on public.enhancement_job_faces
    for insert
    with check (auth.uid()::text = user_id);

drop policy if exists "Users can update their own enhancement faces" on public.enhancement_job_faces;
create policy "Users can update their own enhancement faces"
    on public.enhancement_job_faces
    for update
    using (auth.uid()::text = user_id)
    with check (auth.uid()::text = user_id);

create index if not exists enhancement_jobs_user_created_at_idx
    on public.enhancement_jobs (user_id, created_at desc);

drop index if exists enhancement_jobs_queue_idx;
create index enhancement_jobs_queue_idx
    on public.enhancement_jobs (status, next_retry_at, created_at)
    where status in ('queued_for_comfy_upload', 'retrying_comfy_upload');

alter table public.enhancement_jobs enable row level security;

drop policy if exists "Users can read their own enhancement jobs" on public.enhancement_jobs;
create policy "Users can read their own enhancement jobs"
    on public.enhancement_jobs
    for select
    using (auth.uid()::text = user_id);

drop policy if exists "Users can insert their own enhancement jobs" on public.enhancement_jobs;
create policy "Users can insert their own enhancement jobs"
    on public.enhancement_jobs
    for insert
    with check (auth.uid()::text = user_id);
