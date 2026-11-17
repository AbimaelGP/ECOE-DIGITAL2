# utils/acceso_examen.py
"""Contraseña del examen por día (la misma para todos los estudiantes de esa fecha)."""
from utils.supabase_client import supabase
from utils.horario import leer_fecha, ahora


def _clave_fecha(valor):
    d = leer_fecha(valor)
    return d.strftime("%Y-%m-%d") if d else None


def obtener_contrasena_dia(fecha):
    """Contraseña configurada para esa fecha, o None."""
    f = _clave_fecha(fecha)
    if not f or not supabase:
        return None
    try:
        r = supabase.table("contrasena_examen").select("contrasena").eq("fecha", f).execute()
        return r.data[0]["contrasena"] if r.data else None
    except Exception as e:
        print(f"⚠️ No se pudo leer la contraseña del día (¿falta la migración 005?): {e}")
        return None


def guardar_contrasena_dia(fecha, contrasena, usuario="admin"):
    f = _clave_fecha(fecha)
    contrasena = (contrasena or "").strip()
    if not f:
        return False, "Fecha no válida"
    if len(contrasena) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres"
    try:
        datos = {"fecha": f, "contrasena": contrasena, "actualizado_por": usuario, "updated_at": ahora().isoformat()}
        existe = supabase.table("contrasena_examen").select("fecha").eq("fecha", f).execute().data
        if existe:
            supabase.table("contrasena_examen").update(datos).eq("fecha", f).execute()
        else:
            supabase.table("contrasena_examen").insert(datos).execute()
        return True, f"Contraseña guardada para el {leer_fecha(f).strftime('%d/%m/%Y')}"
    except Exception as e:
        if "contrasena_examen" in str(e):
            return False, ("Falta la tabla en la base. Ejecuta una vez en Supabase → SQL Editor el archivo "
                           "migraciones/005_contrasena_examen.sql")
        return False, f"Error: {e}"


def listar_contrasenas(limite=10):
    try:
        r = supabase.table("contrasena_examen").select("*").order("fecha", desc=True).limit(limite).execute()
        return r.data or []
    except Exception:
        return []
