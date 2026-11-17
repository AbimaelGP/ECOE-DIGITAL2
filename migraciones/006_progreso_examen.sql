-- ECOE Digital · Migración 006 · progreso del examen para retomar después de un error.
-- Guarda en qué pantalla/área va el estudiante, el tiempo que le quedaba y las áreas terminadas.
-- Solo agrega; no modifica datos existentes.
create table if not exists public.progreso_examen (
    matricula      text primary key,
    datos          jsonb default '{}'::jsonb,   -- pagina, modulo, caso, restante_seg, completados, finalizado...
    reanudaciones  integer default 0,           -- cuántas veces retomó el examen
    updated_at     timestamptz default now()
);
do $$
declare rls_actual boolean;
begin
    select c.relrowsecurity into rls_actual from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'usuarios';
    if coalesce(rls_actual, false) then
        execute 'alter table public.progreso_examen enable row level security';
    end if;
end $$;
notify pgrst, 'reload schema';
