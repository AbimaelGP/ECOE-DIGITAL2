# utils/migraciones.py
"""
Aplica automáticamente las migraciones de base de datos (carpeta /migraciones)
al iniciar la app, SOLO si existe el secreto DATABASE_URL (cadena de conexión
de Postgres de Supabase).

Reglas de seguridad:
- Cada archivo se aplica una sola vez (se registra en la tabla ecoe_migraciones).
- Antes de ejecutar, se rechaza cualquier archivo que contenga instrucciones
  que borren o cambien datos existentes (DROP, DELETE, TRUNCATE, RENAME,
  ALTER ... TYPE, UPDATE). Las migraciones solo pueden AGREGAR.
- Si algo falla, la app sigue funcionando y se registra el error.
"""
import os
import re
from pathlib import Path

import streamlit as st

CARPETA = Path(__file__).resolve().parents[2] / "migraciones"

_PROHIBIDAS = [
    r"\bdrop\b", r"\bdelete\b", r"\btruncate\b", r"\brename\b",
    r"\balter\s+column\b.*\btype\b", r"^\s*update\b",
]


def _quitar_comentarios(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def es_migracion_segura(sql: str) -> tuple[bool, str]:
    limpio = _quitar_comentarios(sql).lower()
    for patron in _PROHIBIDAS:
        if re.search(patron, limpio, flags=re.MULTILINE):
            return False, patron
    return True, ""


def _database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        try:
            url = st.secrets.get("DATABASE_URL")
        except Exception:
            url = None
    return url


@st.cache_resource(show_spinner=False)
def aplicar_migraciones():
    """Devuelve un dict con el resultado. Se ejecuta una vez por servidor."""
    url = _database_url()
    if not url:
        return {"estado": "sin_database_url", "aplicadas": [], "error": None}

    try:
        import psycopg2
    except ImportError:
        return {"estado": "error", "aplicadas": [], "error": "Falta psycopg2-binary en requirements.txt"}

    aplicadas = []
    try:
        con = psycopg2.connect(url, connect_timeout=10)
        con.autocommit = False
        cur = con.cursor()
        cur.execute(
            "create table if not exists public.ecoe_migraciones ("
            " nombre text primary key, aplicada timestamptz default now())"
        )
        con.commit()
        cur.execute("select nombre from public.ecoe_migraciones")
        ya = {r[0] for r in cur.fetchall()}

        for archivo in sorted(CARPETA.glob("*.sql")):
            if archivo.name in ya:
                continue
            sql = archivo.read_text(encoding="utf-8")
            ok, patron = es_migracion_segura(sql)
            if not ok:
                con.rollback()
                return {"estado": "error", "aplicadas": aplicadas,
                        "error": f"{archivo.name} rechazada: contiene '{patron}'"}
            cur.execute(sql)
            cur.execute("insert into public.ecoe_migraciones (nombre) values (%s)", (archivo.name,))
            con.commit()
            aplicadas.append(archivo.name)
        cur.close()
        con.close()
        return {"estado": "ok", "aplicadas": aplicadas, "error": None}
    except Exception as e:
        print(f"❌ Error aplicando migraciones: {e}")
        return {"estado": "error", "aplicadas": aplicadas, "error": str(e)}
