-- ECOE Digital · Migración 005 · contraseña del examen por día (la misma para todos los estudiantes de esa fecha).
-- Solo agrega; no modifica datos existentes.
create table if not exists public.contrasena_examen (
    fecha            text primary key,          -- 'YYYY-MM-DD'
    contrasena       text not null,
    actualizado_por  text,
    updated_at       timestamptz default now()
);
do $$
declare rls_actual boolean;
begin
    select c.relrowsecurity into rls_actual from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'usuarios';
    if coalesce(rls_actual, false) then
        execute 'alter table public.contrasena_examen enable row level security';
    end if;
end $$;
notify pgrst, 'reload schema';
