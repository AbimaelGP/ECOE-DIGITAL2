# -*- coding: utf-8 -*-
# config.py - VERSIÓN PARA CLAVE DE PAGO ESTÁNDAR
import os
import logging
from datetime import datetime

# ──────────────────────────────────────────────
# API KEY - TU CLAVE DE PAGO
# ──────────────────────────────────────────────
# Coloca aquí tu clave de API de pago estándar (comienza con AIzaSy...)
# La clave se lee de la variable de entorno GEMINI_API_KEY (.env local o Secrets de Streamlit Cloud)
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ──────────────────────────────────────────────
# MODELOS - COMPATIBLES CON GEMINI 2.5
# ──────────────────────────────────────────────
GEMINI_MODELS = [
    "gemini-2.5-flash",       # ✅ Modelo más reciente y rápido
    "gemini-2.5-flash-lite",  # ✅ Versión ligera
    "gemini-1.5-flash",       # ✅ Modelo estable
    "gemini-1.5-pro",         # ✅ Modelo Pro
]

DEFAULT_MODEL = "gemini-2.5-flash"  # 👈 Modelo principal

# ──────────────────────────────────────────────
# CONFIGURACIÓN GENERAL
# ──────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
MAX_CHARS_RUBRICA = 4000
MAX_CHARS_CONV = 6000

DIR_RUBRICAS = "Rubricas"
DIR_CONVERSACIONES = "Conversaciones"
DIR_RESULTADOS = "Resultados"
DIR_LOGS = "Logs"

# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────
def configurar_logging():
    os.makedirs(DIR_LOGS, exist_ok=True)
    log_file = os.path.join(DIR_LOGS, "ecoe_{}.log".format(datetime.now().strftime("%Y%m%d")))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ]
    )
    return logging.getLogger("ECOE")

logger = configurar_logging()

# ──────────────────────────────────────────────
# FUNCIONES DE ACCESO SIMPLIFICADAS
# ──────────────────────────────────────────────
def get_api_key():
    """Devuelve la única clave de API configurada"""
    return GEMINI_API_KEY

def get_model():
    """Devuelve el modelo por defecto"""
    return DEFAULT_MODEL

def get_models():
    """Devuelve la lista de modelos disponibles"""
    return GEMINI_MODELS

# Funciones para compatibilidad (no se usan con clave única)
def mark_key_success(key):
    pass

def mark_key_failed(key):
    pass