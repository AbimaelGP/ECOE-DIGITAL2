# utils/horario.py
"""Hora local de la app y lectura tolerante de fechas/horas capturadas a mano.

Streamlit Cloud corre en UTC; sin esto el examen abriría y cerraría 6 horas
antes en Chihuahua. La zona se puede cambiar con el secreto ZONA_HORARIA.
"""
import os
import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

ZONA_POR_DEFECTO = "America/Chihuahua"


def _zona():
    nombre = os.getenv("ZONA_HORARIA")
    if not nombre:
        try:
            import streamlit as st
            nombre = st.secrets.get("ZONA_HORARIA")
        except Exception:
            nombre = None
    try:
        return ZoneInfo(nombre or ZONA_POR_DEFECTO)
    except Exception:
        return ZoneInfo(ZONA_POR_DEFECTO)


def ahora():
    """Fecha y hora local (sin zona) para comparar con lo que captura el administrador."""
    return datetime.now(_zona()).replace(tzinfo=None)


def leer_fecha(valor):
    """Acepta date, '2026-11-17', '17/11/2026', '17-11-2026' (y con hora al final). Devuelve date o None."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    if not texto or texto.lower() in ("none", "nan", "nat"):
        return None
    texto = texto.split("T")[0].split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            pass
    return None


def leer_hora(valor):
    """Acepta time, datetime, '08:00', '8:00', '08:00:00', '14:30:00.000', '1970-01-01 14:30:00',
    '7', '7.30', '7am', '2 pm', '0730'. Devuelve time o None."""
    if isinstance(valor, datetime):            # también pandas.Timestamp
        return valor.time().replace(second=0, microsecond=0)
    if isinstance(valor, time):
        return valor.replace(second=0, microsecond=0)
    texto = str(valor or "").strip().lower()
    if not texto or texto in ("none", "nan", "nat"):
        return None
    pm = bool(re.search(r"p\.?\s*m\.?$", texto))
    am = bool(re.search(r"a\.?\s*m\.?$", texto))

    def armar(h, mi):
        if pm and h < 12:
            h += 12
        if am and h == 12:
            h = 0
        return time(h, mi) if 0 <= h <= 23 and 0 <= mi <= 59 else None

    # 1) Hay "HH:MM" en algún lugar (p. ej. '14:30:00.000' o '1970-01-01 14:30:00'): usar la última
    pares = re.findall(r"(\d{1,2}):(\d{2})(?::\d{2}(?:\.\d+)?)?", texto)
    if pares:
        h, mi = pares[-1]
        return armar(int(h), int(mi))
    # 2) Formatos cortos: '7', '7.30', '7am', '0730'
    corto = re.sub(r"[ap]\.?\s*m\.?$", "", texto).replace(" ", "")
    m = re.fullmatch(r"(\d{1,2})(?:[.,](\d{2}))?", corto) or re.fullmatch(r"(\d{2})(\d{2})", corto)
    if not m:
        return None
    return armar(int(m.group(1)), int(m.group(2) or 0))
