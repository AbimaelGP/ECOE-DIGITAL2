-- ECOE Digital · Migración 003 · columna "activo" en circuitos (la usa "Guardar circuito").
-- Solo agrega; no modifica datos existentes.
alter table public.circuitos add column if not exists activo boolean default true;
notify pgrst, 'reload schema';
