# utils/progreso_examen.py
"""Progreso del examen del estudiante, guardado en la base (tabla progreso_examen).

Si el estudiante pierde la conexión, se cierra el navegador o la app se reinicia, al volver a
entrar retoma donde iba: mismas áreas terminadas, el área en curso con su chat y estudios, y el
tiempo que le quedaba en esa área (el reloj se guarda cada pocos segundos).

Si la tabla aún no existe (falta la migración 006), todo sigue funcionando: las áreas
terminadas se recuperan de las respuestas guardadas, pero sin el tiempo restante."""
import json
import time
from datetime import datetime, timedelta

import streamlit as st

from utils.horario import ahora as ahora_local
from utils.supabase_client import supabase

DURACION_AREA = 600          # segundos por área (10 min)
CADA_SEGUNDOS = 10           # cada cuánto se guarda el tiempo restante
PAGINAS_EXAMEN = {"instrucciones", "seleccion_a", "historial_clinico", "modulo_activo", "examen_final"}


# ===================== LECTURA / ESCRITURA =====================

def _leer(matricula):
    """(datos, reanudaciones, existe_fila). datos=None si la tabla no existe."""
    try:
        r = supabase.table("progreso_examen").select("*").eq("matricula", matricula).execute()
    except Exception:
        return None, 0, False
    if not r.data:
        return {}, 0, False
    fila = r.data[0]
    datos = fila.get("datos") or {}
    if isinstance(datos, str):
        try:
            datos = json.loads(datos)
        except Exception:
            datos = {}
    return datos, int(fila.get("reanudaciones") or 0), True


def guardar(matricula, sumar_reanudacion=False, **cambios):
    """Mezcla `cambios` en el progreso guardado. Nunca rompe el examen si falla."""
    if not matricula:
        return False
    datos, reanud, existe = _leer(matricula)
    if datos is None:
        return False
    datos.update(cambios)
    fila = {"datos": datos, "updated_at": ahora_local().isoformat()}
    if sumar_reanudacion:
        fila["reanudaciones"] = reanud + 1
    try:
        if existe:
            supabase.table("progreso_examen").update(fila).eq("matricula", matricula).execute()
        else:
            supabase.table("progreso_examen").insert({"matricula": matricula, **fila}).execute()
        return True
    except Exception as e:
        print(f"⚠️ No se guardó el progreso de {matricula}: {e}")
        return False


# ===================== EVENTOS DEL EXAMEN =====================

def marcar_inicio(matricula):
    guardar(matricula, examen_iniciado=True, finalizado=False, inicio_examen=datetime.now().isoformat())


def entrar_area(matricula, modulo, caso, restante=DURACION_AREA):
    st.session_state["_progreso_ultimo_latido"] = time.time()
    guardar(matricula, modulo_activo=int(modulo), caso_activo=caso, restante_seg=int(restante), en_preguntas=False)


def latido(matricula, modulo, restante, forzar=False):
    """Guarda el tiempo restante del área en curso (como mucho cada CADA_SEGUNDOS)."""
    ultimo = st.session_state.get("_progreso_ultimo_latido", 0)
    if not forzar and time.time() - ultimo < CADA_SEGUNDOS:
        return
    st.session_state["_progreso_ultimo_latido"] = time.time()
    guardar(matricula, modulo_activo=int(modulo), restante_seg=max(0, int(restante)))


def marcar_preguntas(matricula, abierto=True):
    guardar(matricula, en_preguntas=bool(abierto))


def terminar_area(matricula, modulo):
    datos, _, _ = _leer(matricula)
    completados = dict((datos or {}).get("completados") or {})
    completados[str(modulo)] = True
    guardar(matricula, completados=completados, modulo_activo=None, caso_activo=None,
            restante_seg=None, en_preguntas=False)


def finalizar(matricula):
    guardar(matricula, finalizado=True, modulo_activo=None, caso_activo=None, restante_seg=None)


# ===================== CONSULTAS =====================

def examen_en_curso():
    """True mientras el estudiante está dentro del examen (para ocultar 'Cerrar sesión')."""
    return (st.session_state.get("tipo_usuario") == "estudiante"
            and st.session_state.get("pagina") in PAGINAS_EXAMEN
            and not st.session_state.get("examen_finalizado", False))


def examen_terminado(matricula):
    """True si el estudiante ya terminó su examen (llegó a la pantalla final)."""
    datos, _, _ = _leer(matricula)
    return bool(datos and datos.get("finalizado"))


def _areas_con_respuestas(matricula, modulos):
    """Áreas que ya tienen respuestas guardadas (sirve aunque no exista la tabla de progreso)."""
    hechas = {}
    for m in modulos:
        if not m.get("asignado") or not m.get("caso"):
            continue
        try:
            r = supabase.table("historial_preguntas_estudiante").select("id").eq("matricula", matricula) \
                .eq("caso", m["caso"]).execute()
            if r.data:
                hechas[int(m["numero"])] = True
        except Exception:
            pass
    return hechas


def progreso_pendiente(matricula):
    """Devuelve el progreso si el estudiante empezó el examen y no lo ha terminado; si no, None."""
    datos, _, _ = _leer(matricula)
    if datos and datos.get("examen_iniciado") and not datos.get("finalizado"):
        return {**datos, "_fuente": "tabla"}
    if datos is None or not datos.get("finalizado"):   # sin tabla o sin fila: por chats/respuestas guardados
        try:
            ch = supabase.table("historial_chat_estudiante").select("id").eq("matricula", matricula).limit(1).execute().data
            pr = supabase.table("historial_preguntas_estudiante").select("id").eq("matricula", matricula).limit(1).execute().data
            if ch or pr:
                return {"examen_iniciado": True, "_fuente": "historial"}
        except Exception:
            pass
    return None


def _cargar_chat(matricula, caso):
    try:
        r = supabase.table("historial_chat_estudiante").select("mensajes, estudios_solicitados") \
            .eq("matricula", matricula).eq("caso", caso).execute()
    except Exception:
        try:
            r = supabase.table("historial_chat_estudiante").select("mensajes") \
                .eq("matricula", matricula).eq("caso", caso).execute()
        except Exception:
            return [], []
    if not r.data:
        return [], []
    fila = r.data[-1]
    mensajes, estudios = fila.get("mensajes") or [], fila.get("estudios_solicitados") or []
    for nombre in ("mensajes", "estudios"):
        valor = mensajes if nombre == "mensajes" else estudios
        if isinstance(valor, str):
            try:
                valor = json.loads(valor)
            except Exception:
                valor = []
        if nombre == "mensajes":
            mensajes = valor if isinstance(valor, list) else []
        else:
            estudios = valor if isinstance(valor, list) else []
    return mensajes, estudios


def restaurar(matricula):
    """Reconstruye la sesión del examen desde la base y devuelve la página a la que se regresa."""
    from utils.database import obtener_datos_estudiante

    datos = progreso_pendiente(matricula) or {}
    info = obtener_datos_estudiante(matricula) or {}
    modulos = info.get("modulos", [])

    # Estado general
    st.session_state["examen_iniciado"] = True
    st.session_state["instrucciones_terminadas"] = True
    try:
        st.session_state["tiempo_inicio_examen"] = datetime.fromisoformat(datos["inicio_examen"])
    except Exception:
        st.session_state.setdefault("tiempo_inicio_examen", datetime.now())

    # Áreas terminadas: lo guardado + las que ya tienen respuestas
    completados = {int(k): bool(v) for k, v in (datos.get("completados") or {}).items()}
    completados.update(_areas_con_respuestas(matricula, modulos))
    for m in modulos:
        if m.get("asignado"):
            completados.setdefault(int(m["numero"]), False)
    st.session_state["modulos_completados"] = completados

    pagina = "seleccion_a"
    modulo = datos.get("modulo_activo")
    caso = datos.get("caso_activo")
    restante = datos.get("restante_seg")
    if modulo and caso and not completados.get(int(modulo)):
        modulo = int(modulo)
        if restante is not None and int(restante) > 5:
            ahora = ahora_local()
            restante = int(restante)
            st.session_state["modulo_seleccionado"] = modulo
            st.session_state["caso_seleccionado"] = caso
            st.session_state[f"tiempo_inicio_modulo_{modulo}"] = ahora - timedelta(seconds=DURACION_AREA - restante)
            st.session_state[f"tiempo_limite_modulo_{modulo}"] = ahora + timedelta(seconds=restante)
            mensajes, estudios = _cargar_chat(matricula, caso)
            st.session_state[f"chat_{caso}"] = mensajes
            escena = f"modulo_{modulo}"
            if estudios:
                st.session_state[f"estudios_solicitados_{escena}_{modulo}"] = list(estudios)
                st.session_state[f"modal_estudios_abierto_{escena}_{modulo}"] = True
            if datos.get("en_preguntas"):
                st.session_state[f"modal_diagnostico_abierto_{escena}_{modulo}"] = True
            st.session_state["_progreso_ultimo_latido"] = time.time()
            pagina = "modulo_activo"
        else:
            # Se le acabó el tiempo de esa área: se da por terminada con lo que alcanzó a hacer
            completados[modulo] = True
            st.session_state["modulos_completados"] = completados
            terminar_area(matricula, modulo)

    guardar(matricula, sumar_reanudacion=True, examen_iniciado=True, finalizado=False)
    st.session_state["examen_reanudado"] = True
    return pagina
