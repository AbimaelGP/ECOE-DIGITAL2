# utils/evaluacion_automatica.py
"""Evaluación automática con el chatbot cuando el estudiante termina su circuito.

Corre en segundo plano (el estudiante no espera): evalúa cada estación, genera la
carátula en PDF y la guarda. Se hace UNA sola vez por estudiante; el administrador ya
no re-evalúa, solo descarga el PDF, ve resultados y ajusta ponderaciones."""
import os
import threading
import uuid

from utils.supabase_client import supabase

_en_curso = set()
_candado = threading.Lock()
_ultimo_resultado = {}   # matricula -> mensaje del último intento sin PDF (se pierde al reiniciar)


def ultimo_resultado(matricula):
    return _ultimo_resultado.get(matricula)


def _casos(circuito):
    from utils.evaluador_batch import obtener_casos_circuito
    try:
        return obtener_casos_circuito(circuito) or []
    except Exception:
        return []


def circuito_terminado(matricula, circuito):
    """True si el estudiante tiene chat o respuestas en todas las estaciones de su circuito."""
    casos = _casos(circuito)
    if not casos:
        return False
    for c in casos:
        try:
            ch = supabase.table("historial_chat_estudiante").select("id").eq("matricula", matricula).eq("caso", c["clave_caso"]).execute().data
            pr = supabase.table("historial_preguntas_estudiante").select("id").eq("matricula", matricula).eq("caso", c["clave_caso"]).execute().data
        except Exception:
            return False
        if not ch and not pr:
            return False
    return True


def falta_medico(matricula, circuito):
    """Claves de los casos estandarizados del circuito que aún no tienen evaluación enviada del médico."""
    from utils.evaluacion_dual import obtener_caso, modalidad_de
    faltan = []
    for c in _casos(circuito):
        info = obtener_caso(c["clave_caso"]) or {}
        if modalidad_de(info.get("tipo_caso")) != "Estandarizado":
            continue
        try:
            r = supabase.table("evaluacion_docente").select("id").eq("matricula", matricula) \
                .eq("clave_caso", c["clave_caso"]).eq("estatus", "enviada").execute().data
        except Exception:
            r = None
        if not r:
            faltan.append(c["clave_caso"])
    return faltan


def al_enviar_medico(matricula):
    """Cuando el médico envía una evaluación: si el estudiante ya terminó su circuito y aún
    no tiene PDF, se genera (en segundo plano)."""
    try:
        r = supabase.table("perfiles_estudiantes").select("circuito_asignado, nombre_completo") \
            .eq("matricula", matricula).execute().data
        if not r:
            return False
        circuito = r[0].get("circuito_asignado")
        if circuito and circuito_terminado(matricula, circuito):
            return lanzar_evaluacion(matricula, r[0].get("nombre_completo"), circuito)
    except Exception as e:
        print(f"⚠️ No se pudo lanzar la evaluación tras el envío del médico: {e}")
    return False


def subir_pdf(ruta_local, matricula, circuito):
    """Sube el PDF al Storage y registra la URL en evaluaciones_pdf."""
    nombre_archivo = f"{matricula}_{uuid.uuid4().hex[:6]}.pdf"
    ruta_storage = f"evaluaciones/{nombre_archivo}"
    with open(ruta_local, "rb") as f:
        supabase.storage.from_("casos_clinicos").upload(
            path=ruta_storage, file=f.read(), file_options={"content-type": "application/pdf"})
    url = supabase.storage.from_("casos_clinicos").get_public_url(ruta_storage)
    supabase.table("evaluaciones_pdf").insert({"matricula": matricula, "circuito": circuito, "url_pdf": url}).execute()
    return url


def ya_evaluado(matricula):
    try:
        r = supabase.table("evaluaciones_pdf").select("id").eq("matricula", matricula).limit(1).execute()
        return bool(r.data)
    except Exception:
        return False


def en_curso(matricula):
    return matricula in _en_curso


def _trabajo(matricula, nombre, circuito):
    try:
        from utils.evaluador_batch import evaluar_estudiante_completo
        ok, resultado = evaluar_estudiante_completo(matricula, nombre, circuito)
        if ok:
            subir_pdf(resultado, matricula, circuito)
            _ultimo_resultado.pop(matricula, None)
            try:
                os.remove(resultado)
            except OSError:
                pass
            print(f"✅ Evaluación automática lista: {matricula}")
        else:
            _ultimo_resultado[matricula] = resultado
            print(f"⏸️ Evaluación de {matricula} sin PDF todavía: {resultado}")
    except Exception as e:
        _ultimo_resultado[matricula] = f"Error: {e}"
        print(f"❌ Error en evaluación automática de {matricula}: {e}")
    finally:
        with _candado:
            _en_curso.discard(matricula)


def lanzar_evaluacion(matricula, nombre, circuito=None, esperar=False):
    """Inicia la evaluación si el estudiante aún no tiene PDF. Devuelve True si se lanzó."""
    if not matricula:
        return False
    if circuito is None:
        try:
            r = supabase.table("perfiles_estudiantes").select("circuito_asignado, nombre_completo") \
                .eq("matricula", matricula).execute()
            if r.data:
                circuito = r.data[0].get("circuito_asignado")
                nombre = nombre or r.data[0].get("nombre_completo")
        except Exception:
            pass
    if not circuito:
        return False
    with _candado:
        if matricula in _en_curso or ya_evaluado(matricula):
            return False
        _en_curso.add(matricula)
    if esperar:
        _trabajo(matricula, nombre, circuito)
    else:
        threading.Thread(target=_trabajo, args=(matricula, nombre, circuito), daemon=True).start()
    return True
