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
