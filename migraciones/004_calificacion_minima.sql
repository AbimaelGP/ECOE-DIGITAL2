-- ECOE Digital · Migración 004 · calificación mínima aprobatoria guardada en la base.
-- Solo agrega; no modifica datos existentes.
alter table public.configuracion_examen add column if not exists calificacion_minima numeric;
notify pgrst, 'reload schema';
