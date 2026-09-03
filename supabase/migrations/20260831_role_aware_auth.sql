-- DuesPilot: production user profile and role foundation.
-- Run in the Supabase SQL editor or through the Supabase CLI before enabling
-- AUTH_REQUIRED=true on the API.

create type public.recovery_role as enum ('admin', 'user');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  full_name text,
  role public.recovery_role not null default 'user',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users can read their own profile"
  on public.profiles for select to authenticated
  using ((select auth.uid()) = id);

create policy "Users can update their own display name only"
  on public.profiles for update to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- Every authenticated person begins as a read-only recovery user. Promote an
-- administrator only with server-side tooling; never grant roles from a browser.
create or replace function public.create_profile_for_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, coalesce(new.email, ''), new.raw_user_meta_data ->> 'full_name');
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.create_profile_for_new_user();

-- The backend authorizes recovery mutations from auth.users.app_metadata
-- (key: recovery_role). Set it using the service-role Admin API, for example:
-- auth.admin.updateUserById(userId, { app_metadata: { recovery_role: 'admin' } })
-- Keep ordinary users at recovery_role: 'user'.
