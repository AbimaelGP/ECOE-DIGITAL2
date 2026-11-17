# utils/evaluacion_dual.py
"""
Lógica de la evaluación dual (chatbot evaluador + médico evaluador).

- Rúbrica del caso: competencias elegidas por el médico + 5 niveles de la
  Rúbrica General (Preformal … Estratégico) en escala 1–10.
- Evidencia del estudiante: transcripción numerada, estudios solicitados y
  respuestas escritas.
- Evaluación estructurada del chatbot (nivel, criterio, evidencias, qué faltó).
- Ponderación chatbot/médico y calificación final.
- Métricas de confiabilidad: ICC(2,1), kappa ponderada, acuerdo ±1 nivel, MAE y sesgo.
"""
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import requests
import streamlit as st

from utils.supabase_client import supabase

# ===================== CONFIGURACIÓN =====================

PROMPT_VERSION = "v2.1"

# Escala de la propuesta (puedes ajustar los rangos aquí y se actualiza en toda la app)
NIVELES = [
    ("Preformal", 1, 2),
    ("Receptivo", 3, 4),
    ("Resolutivo", 5, 6),
    ("Autónomo", 7, 8),
    ("Estratégico", 9, 10),
]

MODALIDADES = {
    "Paciente Virtual": "Virtual",
    "Estático": "Estático",
    "Paciente Estandarizado": "Estandarizado",
}

_RUTA_DESCRIPTORES = Path(__file__).resolve().parent / "evaluador" / "rubrica_niveles.json"


# ===================== UTILIDADES =====================

def _a_json(valor, defecto):
    """Supabase a veces guarda JSON como texto; esto lo normaliza."""
    if valor is None:
        return defecto
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except Exception:
            return defecto
    return valor


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s).split()


def modalidad_de(tipo_caso):
    return MODALIDADES.get(tipo_caso or "", tipo_caso or "Estático")


def nivel_de_puntaje(puntaje):
    if puntaje is None:
        return None
    p = float(puntaje)
    for nombre, lo, hi in NIVELES:
        if p <= hi:
            return nombre
    return NIVELES[-1][0]


def indice_nivel(puntaje):
    nombre = nivel_de_puntaje(puntaje)
    for i, (n, _, _) in enumerate(NIVELES):
        if n == nombre:
            return i
    return None


def calificacion_por_areas(items):
    """Calificación del caso igual que la carátula institucional:
    promedio de cada área troncal (Básicas, Específicas, Profesionales) y luego promedio de esas áreas."""
    grupos = {}
    for it in items or []:
        p = it.get("puntaje")
        if p is None:
            continue
        grupos.setdefault(it.get("categoria") or "General", []).append(float(p))
    if not grupos:
        return None
    return round(sum(sum(v) / len(v) for v in grupos.values()) / len(grupos), 2)


def promedio(valores):
    v = [float(x) for x in valores if x is not None]
    return round(sum(v) / len(v), 2) if v else None


# ===================== RÚBRICA DEL CASO =====================

@lru_cache(maxsize=1)
def _descriptores():
    try:
        return json.loads(_RUTA_DESCRIPTORES.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _descriptores_para(dominio, texto):
    d = _descriptores()
    clave = f"{dominio}|{texto}"
    if clave in d:
        return d[clave]
    # Búsqueda aproximada por si el texto cambió ligeramente
    objetivo = set(_norm(texto))
    mejor, puntaje = None, 0
    for k, v in d.items():
        s = len(objetivo & set(_norm(k.split("|", 1)[-1]))) / max(1, len(objetivo))
        if s > puntaje:
            mejor, puntaje = v, s
    if mejor and puntaje >= 0.6:
        return mejor
    return [f"Desempeño {n.lower()} en la competencia." for n, _, _ in NIVELES]


def competencias_de_caso(caso_o_lista):
    """Devuelve la lista de criterios del formulario a partir del caso
    (fila de casos_clinicos) o de la lista competencias_seleccionadas."""
    if isinstance(caso_o_lista, dict):
        lista = _a_json(caso_o_lista.get("rubrica_competencias"), [])
    else:
        lista = caso_o_lista or []
    criterios = []
    for c in lista:
        if not isinstance(c, dict):
            continue
        dominio = c.get("subcategoria", "")
        texto = c.get("texto", "")
        criterios.append({
            "clave": f"{dominio}|{texto}",
            "categoria": c.get("categoria", ""),
            "dominio": dominio,
            "texto": texto,
            "niveles": _descriptores_para(dominio, texto),
        })
    return criterios


# ===================== CARGA DE DATOS =====================

def _tabla(nombre, columnas="*"):
    if not supabase:
        return []
    try:
        return supabase.table(nombre).select(columnas).execute().data or []
    except Exception as e:
        print(f"⚠️ No se pudo leer {nombre}: {e}")
        return []


@st.cache_data(ttl=60, show_spinner=False)
def tablas_dual_disponibles():
    """True si ya existen las tablas nuevas (migración 002 aplicada)."""
    if not supabase:
        return False
    try:
        supabase.table("evaluacion_docente").select("id").limit(1).execute()
        supabase.table("evaluacion_chatbot").select("id").limit(1).execute()
        supabase.table("configuracion_ponderacion").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def obtener_caso(clave_caso):
    if not supabase or not clave_caso:
        return None
    try:
        r = supabase.table("casos_clinicos").select("*").eq("clave_caso", clave_caso).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def obtener_medico(identificador):
    try:
        r = supabase.table("perfiles_medicos").select("*").eq("identificador", identificador).execute()
        return r.data[0] if r.data else {}
    except Exception:
        return {}


def _estaciones_de_circuito(circuito):
    estaciones = []
    for i in range(1, 7):
        area = circuito.get(f"modulo_{i}")
        caso = circuito.get(f"caso_{i}")
        if area and caso and area != "No asignar":
            estaciones.append({"num_area": i, "area": area, "clave_caso": caso})
    return estaciones


def construir_filas(circuito_filtro=None, area_filtro=None):
    """Una fila por (estudiante, caso) según los circuitos asignados.
    Incluye modalidad, si completó la estación y ambas evaluaciones."""
    estudiantes = _tabla("perfiles_estudiantes")
    circuitos = {c["nombre"]: c for c in _tabla("circuitos") if c.get("nombre")}
    casos = {c["clave_caso"]: c for c in _tabla("casos_clinicos", "clave_caso, tipo_caso, especialidad, data, rubrica_competencias")}
    chats = {(h["matricula"], h["caso"]) for h in _tabla("historial_chat_estudiante", "matricula, caso")}
    pregs = {(h["matricula"], h["caso"]) for h in _tabla("historial_preguntas_estudiante", "matricula, caso")}

    ev_doc = {}
    for e in _tabla("evaluacion_docente"):
        ev_doc.setdefault((e["matricula"], e["clave_caso"]), []).append(e)
    ev_bot = {}
    for e in sorted(_tabla("evaluacion_chatbot"), key=lambda x: x.get("fecha_evaluacion") or ""):
        ev_bot[(e["matricula"], e["clave_caso"])] = e  # se queda la más reciente
    finales = {(f["matricula"], f["clave_caso"]): f for f in _tabla("calificacion_final")}

    filas = []
    for est in estudiantes:
        nombre_circ = est.get("circuito_asignado")
        if not nombre_circ or nombre_circ not in circuitos:
            continue
        if circuito_filtro and nombre_circ not in circuito_filtro:
            continue
        for estacion in _estaciones_de_circuito(circuitos[nombre_circ]):
            if area_filtro and estacion["area"] != area_filtro:
                continue
            clave = estacion["clave_caso"]
            caso = casos.get(clave, {})
            par = (est["matricula"], clave)
            data = _a_json(caso.get("data"), {})
            docentes = ev_doc.get(par, [])
            filas.append({
                "matricula": est["matricula"],
                "nombre": est.get("nombre_completo", ""),
                "circuito": nombre_circ,
                "fecha_examen": est.get("fecha_examen", ""),
                "num_area": estacion["num_area"],
                "area": estacion["area"],
                "clave_caso": clave,
                "nombre_caso": data.get("nombre_caso", ""),
                "modalidad": modalidad_de(caso.get("tipo_caso")),
                "realizada": par in chats or par in pregs,
                "eval_docentes": docentes,
                "eval_chatbot": ev_bot.get(par),
                "final": finales.get(par),
            })
    filas.sort(key=lambda f: (str(f["fecha_examen"]), f["circuito"], f["num_area"], f["matricula"]))
    return filas


def filas_para_medico(identificador):
    medico = obtener_medico(identificador)
    area = medico.get("modulo_asignado")
    circ = medico.get("circuito_asignado")
    circuito_filtro = None if not circ or circ == "Todos" else [circ]
    filas = construir_filas(circuito_filtro=circuito_filtro, area_filtro=area)
    for f in filas:
        f["mi_eval"] = next((e for e in f["eval_docentes"] if e.get("evaluador") == identificador), None)
    return medico, filas


# ===================== EVIDENCIA DEL ESTUDIANTE =====================

def obtener_evidencia(matricula, clave_caso):
    """Transcripción numerada, estudios solicitados y respuestas escritas."""
    evidencia = {"transcripcion": [], "estudios": [], "respuestas": {}}
    if not supabase:
        return evidencia
    try:
        r = supabase.table("historial_chat_estudiante").select("*") \
            .eq("matricula", matricula).eq("caso", clave_caso).execute()
        n = 0
        for fila in r.data or []:
            for m in _a_json(fila.get("mensajes"), []) or []:
                if not isinstance(m, dict):
                    continue
                n += 1
                evidencia["transcripcion"].append({
                    "n": n,
                    "rol": "Estudiante" if m.get("role") == "user" else "Paciente virtual",
                    "texto": m.get("content", ""),
                    "hora": m.get("hora", ""),
                })
            for e in _a_json(fila.get("estudios_solicitados"), []) or []:
                if e not in evidencia["estudios"]:
                    evidencia["estudios"].append(e)
    except Exception as e:
        print(f"⚠️ Error leyendo chat: {e}")
    try:
        r = supabase.table("historial_preguntas_estudiante").select("*") \
            .eq("matricula", matricula).eq("caso", clave_caso).execute()
        envios = []
        for fila in r.data or []:
            envios.extend(_a_json(fila.get("respuestas"), []) or [])
        if envios:
            ultimo = envios[-1]
            evidencia["respuestas"] = ultimo.get("respuestas", ultimo) if isinstance(ultimo, dict) else {}
    except Exception as e:
        print(f"⚠️ Error leyendo respuestas: {e}")
    return evidencia


def texto_respuestas(respuestas):
    if not respuestas:
        return ""
    partes = []
    for etiqueta, clave in [("Diagnóstico", "diagnostico"), ("Explicación", "explicacion"), ("Tratamiento / plan", "tratamiento")]:
        if respuestas.get(clave):
            partes.append(f"{etiqueta}: {respuestas[clave]}")
    for preg, resp in (respuestas.get("respuestas_preguntas") or {}).items():
        partes.append(f"Pregunta: {preg}\nRespuesta: {resp}")
    return "\n".join(partes)


# ===================== EVALUACIÓN DEL MÉDICO =====================

def obtener_eval_docente(matricula, clave_caso, evaluador):
    try:
        r = supabase.table("evaluacion_docente").select("*").eq("matricula", matricula) \
            .eq("clave_caso", clave_caso).eq("evaluador", evaluador).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def guardar_eval_docente(fila, criterios, comentarios_generales, evaluador, enviar):
    """Inserta o actualiza (nunca borra) la evaluación del médico."""
    puntajes = [c.get("puntaje") for c in criterios if c.get("puntaje")]
    datos = {
        "matricula": fila["matricula"],
        "clave_caso": fila["clave_caso"],
        "modulo": str(fila.get("num_area", "")),
        "circuito": fila.get("circuito"),
        "area": fila.get("area"),
        "modalidad": fila.get("modalidad"),
        "evaluador": evaluador,
        "criterios": criterios,
        "comentarios_generales": comentarios_generales,
        "calificacion": calificacion_por_areas([c for c in criterios if c.get("puntaje")]),
        "updated_at": _ahora(),
    }
    existente = obtener_eval_docente(fila["matricula"], fila["clave_caso"], evaluador)
    if enviar:
        datos["estatus"] = "enviada"
        datos["fecha_envio"] = _ahora()
    elif not existente or existente.get("estatus") != "enviada":
        datos["estatus"] = "borrador"
    try:
        if existente:
            supabase.table("evaluacion_docente").update(datos).eq("id", existente["id"]).execute()
        else:
            supabase.table("evaluacion_docente").insert(datos).execute()
        if enviar:
            try:
                from utils.evaluacion_automatica import al_enviar_medico
                al_enviar_medico(fila["matricula"])
            except Exception:
                pass
        return True, "Evaluación enviada" if enviar else "Borrador guardado"
    except Exception as e:
        return False, f"Error al guardar: {e}"


def nota_medico(fila):
    enviadas = [e for e in fila.get("eval_docentes", []) if e.get("estatus") == "enviada"]
    return promedio([e.get("calificacion") for e in enviadas])


def nota_chatbot(fila):
    ev = fila.get("eval_chatbot")
    return float(ev["calificacion"]) if ev and ev.get("calificacion") is not None else None


# ===================== CHATBOT EVALUADOR =====================

def _gemini_key():
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            key = ""
    return key.split(",")[0].strip()


def _llamar_gemini(prompt):
    from utils.evaluador import config
    key = _gemini_key()
    if not key:
        raise RuntimeError("Falta GEMINI_API_KEY en los Secrets")
    ultimo_error = None
    for modelo in config.GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        try:
            r = requests.post(url, headers={"Content-Type": "application/json", "x-goog-api-key": key},
                              json=payload, timeout=120)
            if r.status_code == 200:
                texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return texto, modelo
            ultimo_error = f"{modelo}: HTTP {r.status_code} {r.text[:120]}"
            if r.status_code in (401, 403):
                break
        except Exception as e:
            ultimo_error = f"{modelo}: {e}"
    raise RuntimeError(f"No se pudo usar Gemini ({ultimo_error})")


def _json_de_texto(texto):
    texto = re.sub(r"```(?:json)?", "", texto).strip()
    i, j = texto.find("{"), texto.rfind("}")
    return json.loads(texto[i:j + 1] if i >= 0 else texto)


def construir_prompt_chatbot(caso, criterios, evidencia):
    data = _a_json(caso.get("data"), {})
    solucion = _a_json(caso.get("solucion"), {})
    modalidad = modalidad_de(caso.get("tipo_caso"))

    lineas_crit = []
    for i, c in enumerate(criterios, 1):
        niveles = "\n".join(
            f"      - {n} ({lo}–{hi}): {desc}" for (n, lo, hi), desc in zip(NIVELES, c["niveles"])
        )
        lineas_crit.append(f"  [{i}] {c['dominio']} · {c['texto']}\n{niveles}")

    if evidencia["transcripcion"]:
        transcript = "\n".join(f"[#{m['n']}] {m['rol']}: {m['texto']}" for m in evidencia["transcripcion"])
    else:
        transcript = "(sin conversación: caso sin paciente virtual)"

    preguntas_esp = "\n".join(
        f"- {p.get('pregunta', '')} → respuesta esperada: {p.get('respuesta_esperada', p.get('respuesta', ''))}"
        for p in (solucion.get("preguntas") or []) if isinstance(p, dict) and p.get("pregunta")
    ) or "(sin preguntas registradas)"
    estudios = ", ".join(evidencia["estudios"]) or "ninguno registrado"
    respuestas = texto_respuestas(evidencia["respuestas"]) or "(sin respuestas escritas)"

    return f"""Eres el CHATBOT EVALUADOR de un examen ECOE de medicina. Evalúas con rigor y justicia,
usando SOLO la evidencia proporcionada. Prompt {PROMPT_VERSION}.

CASO {caso.get('clave_caso')} · modalidad {modalidad}
Motivo de consulta: {data.get('motivo_consulta', '')}
Diagnóstico esperado: {solucion.get('diagnostico_correcto', '')}
Diagnóstico alternativo aceptable: {solucion.get('diagnostico_alternativo', '')}
Tratamiento esperado: {solucion.get('tratamiento_esperado', '')}
Errores críticos: {solucion.get('errores_criticos', '')}
Preguntas del caso y respuestas esperadas (definidas por el médico):
{preguntas_esp}

COMPETENCIAS A EVALUAR (escala 1–10 con 5 niveles):
{chr(10).join(lineas_crit)}

TRANSCRIPCIÓN NUMERADA:
{transcript}

ESTUDIOS SOLICITADOS: {estudios}

RESPUESTAS ESCRITAS DEL ESTUDIANTE:
{respuestas}

INSTRUCCIONES:
- Califica CADA competencia con un entero de 1 a 10; el nivel debe corresponder al rango.
- "criterio": explica por qué ese nivel y no el siguiente, en 1–3 oraciones.
- "evidencias": cita textual breve (máx. 20 palabras) y el número de mensaje [#n] si viene
  de la transcripción; usa null si viene de respuestas escritas o estudios.
- "para_subir": qué le faltó concretamente para el siguiente nivel ("" si es Estratégico).
- No inventes nada que no esté en la evidencia. Si no hay evidencia para una competencia,
  asigna el nivel más bajo justificable y dilo en el criterio.

Devuelve SOLO este JSON:
{{"competencias": [{{"indice": 1, "puntaje": 7, "nivel": "Autónomo", "criterio": "...",
  "evidencias": [{{"mensaje": 3, "cita": "..."}}], "para_subir": "..."}}],
  "resumen": "retroalimentación detallada para el estudiante (4 a 6 oraciones): qué hizo bien, qué le faltó y qué debe estudiar"}}"""


def evaluar_con_chatbot(matricula, clave_caso, modulo=None):
    """Evalúa un (estudiante, caso) y guarda el resultado estructurado."""
    caso = obtener_caso(clave_caso)
    if not caso:
        return False, "Caso no encontrado"
    modalidad = modalidad_de(caso.get("tipo_caso"))
    if modalidad == "Estandarizado":
        return False, "Los casos estandarizados no los evalúa el chatbot"
    criterios = competencias_de_caso(caso)
    if not criterios:
        return False, "El caso no tiene competencias seleccionadas"
    evidencia = obtener_evidencia(matricula, clave_caso)
    if not evidencia["transcripcion"] and not evidencia["respuestas"]:
        return False, "El estudiante no tiene evidencia registrada en este caso"

    texto, modelo = _llamar_gemini(construir_prompt_chatbot(caso, criterios, evidencia))
    salida = _json_de_texto(texto)

    por_indice = {int(c.get("indice", i + 1)): c for i, c in enumerate(salida.get("competencias", []))}
    competencias, contador = [], 0
    for i, crit in enumerate(criterios, 1):
        c = por_indice.get(i, {})
        try:
            puntaje = int(round(float(c.get("puntaje", 1))))
        except Exception:
            puntaje = 1
        puntaje = max(1, min(10, puntaje))
        evidencias = []
        for ev in c.get("evidencias", []) or []:
            if not isinstance(ev, dict):
                continue
            contador += 1
            msg = ev.get("mensaje")
            try:
                msg = int(msg) if msg not in (None, "", "null") else None
            except Exception:
                msg = None
            evidencias.append({"id": f"E{contador}", "mensaje": msg, "cita": str(ev.get("cita", ""))[:300]})
        competencias.append({
            "clave": crit["clave"], "categoria": crit["categoria"], "dominio": crit["dominio"],
            "texto": crit["texto"], "puntaje": puntaje, "nivel": nivel_de_puntaje(puntaje),
            "criterio": str(c.get("criterio", "")), "evidencias": evidencias,
            "para_subir": "" if puntaje >= 9 else str(c.get("para_subir", "")),
        })

    calif = calificacion_por_areas(competencias)
    registro = {
        "matricula": matricula, "clave_caso": clave_caso, "modulo": str(modulo or ""),
        "modalidad": modalidad, "competencias": competencias, "calificacion": calif,
        "nivel_global": nivel_de_puntaje(calif), "resumen": str(salida.get("resumen", "")),
        "transcripcion": evidencia["transcripcion"], "modelo": modelo,
        "prompt_version": PROMPT_VERSION, "fecha_evaluacion": _ahora(),
    }
    try:
        existente = supabase.table("evaluacion_chatbot").select("id").eq("matricula", matricula) \
            .eq("clave_caso", clave_caso).eq("prompt_version", PROMPT_VERSION).execute().data
        if existente:
            supabase.table("evaluacion_chatbot").update(registro).eq("id", existente[0]["id"]).execute()
        else:
            supabase.table("evaluacion_chatbot").insert(registro).execute()
    except Exception as e:
        return False, f"Evaluó pero no pudo guardar: {e}"
    return True, f"Calificación del chatbot: {calif}"


# ===================== REPORTES =====================

def reportar_chatbot(matricula, clave_caso, competencia, comentario, tipo, usuario, rol, prompt_version):
    try:
        supabase.table("reportes_chatbot").insert({
            "matricula": matricula, "clave_caso": clave_caso, "competencia": competencia,
            "comentario": comentario, "tipo": tipo, "reportado_por": usuario, "rol": rol,
            "prompt_version": prompt_version,
        }).execute()
        return True
    except Exception as e:
        print(f"⚠️ No se pudo guardar el reporte: {e}")
        return False


# ===================== PONDERACIÓN =====================

def obtener_ponderaciones():
    return _tabla("configuracion_ponderacion")


def guardar_ponderacion(alcance, valor, w_bot, w_med, usar_disponible, estandarizado_solo_medico, bloqueada, usuario):
    total = (w_bot or 0) + (w_med or 0)
    if total <= 0:
        return False, "Al menos un peso debe ser mayor que 0"
    datos = {
        "alcance": alcance, "valor": valor,
        "w_chatbot": round(w_bot / total, 4), "w_medico": round(w_med / total, 4),
        "usar_disponible": usar_disponible, "estandarizado_solo_medico": estandarizado_solo_medico,
        "bloqueada": bloqueada, "actualizado_por": usuario, "updated_at": _ahora(),
    }
    try:
        existente = supabase.table("configuracion_ponderacion").select("id, bloqueada") \
            .eq("alcance", alcance).eq("valor", valor).execute().data
        if existente:
            if existente[0].get("bloqueada") and bloqueada:
                return False, "Esta ponderación está bloqueada; desmarca 'Bloquear' para cambiarla"
            supabase.table("configuracion_ponderacion").update(datos).eq("id", existente[0]["id"]).execute()
        else:
            supabase.table("configuracion_ponderacion").insert(datos).execute()
        return True, "Ponderación guardada"
    except Exception as e:
        return False, f"Error: {e}"


def ponderacion_para(fila, configs):
    """Prioridad: modalidad > circuito > fecha de examen > todo el examen."""
    def buscar(alcance, valor):
        return next((c for c in configs if c.get("alcance") == alcance and str(c.get("valor")) == str(valor)), None)
    return (buscar("modalidad", fila.get("modalidad")) or buscar("circuito", fila.get("circuito"))
            or buscar("examen", fila.get("fecha_examen")) or buscar("examen", "todos")
            or {"w_chatbot": 0.5, "w_medico": 0.5, "usar_disponible": True, "estandarizado_solo_medico": True})


def calcular_final(fila, cfg):
    bot, med = nota_chatbot(fila), nota_medico(fila)
    wb, wm = float(cfg.get("w_chatbot", 0.5)), float(cfg.get("w_medico", 0.5))
    res = {"chatbot": bot, "medico": med, "w_chatbot": wb, "w_medico": wm, "final": None, "parcial": False}

    # Estandarizados: 100 % médico
    if fila.get("modalidad") == "Estandarizado" and cfg.get("estandarizado_solo_medico", True):
        res.update(w_chatbot=0.0, w_medico=1.0, final=med)
        return res
    # Ambas notas: promedio ponderado
    if bot is not None and med is not None:
        res["final"] = round(wb * bot + wm * med, 2)
        return res
    # Solo una nota: se usa al 100 % si la regla lo permite (queda marcada como parcial)
    disponible = bot if bot is not None else med
    if disponible is not None and cfg.get("usar_disponible", True):
        res.update(final=round(disponible, 2), parcial=True)
    return res


def publicar_calificaciones(filas, configs, usuario):
    """Guarda/actualiza la calificación final de cada par con nota completa."""
    publicadas = 0
    for f in filas:
        r = calcular_final(f, ponderacion_para(f, configs))
        if r["final"] is None or r["parcial"]:
            continue
        datos = {
            "matricula": f["matricula"], "clave_caso": f["clave_caso"], "circuito": f["circuito"],
            "modalidad": f["modalidad"], "nota_chatbot": r["chatbot"], "nota_medico": r["medico"],
            "w_chatbot": r["w_chatbot"], "w_medico": r["w_medico"], "calificacion": r["final"],
            "publicada": True, "publicada_por": usuario, "fecha_publicacion": _ahora(), "updated_at": _ahora(),
        }
        try:
            ex = supabase.table("calificacion_final").select("id").eq("matricula", f["matricula"]) \
                .eq("clave_caso", f["clave_caso"]).execute().data
            if ex:
                supabase.table("calificacion_final").update(datos).eq("id", ex[0]["id"]).execute()
            else:
                supabase.table("calificacion_final").insert(datos).execute()
            publicadas += 1
        except Exception as e:
            print(f"⚠️ No se pudo publicar {f['matricula']}/{f['clave_caso']}: {e}")
    return publicadas


# ===================== CONFIABILIDAD =====================

def pares_criterio(filas):
    """Pares (chatbot, médico) por competencia para evaluaciones completas."""
    pares = []
    for f in filas:
        bot = f.get("eval_chatbot")
        if not bot:
            continue
        bot_c = {c["clave"]: c for c in _a_json(bot.get("competencias"), [])}
        for ev in f.get("eval_docentes", []):
            if ev.get("estatus") != "enviada":
                continue
            for c in _a_json(ev.get("criterios"), []):
                b = bot_c.get(c.get("clave"))
                if b and c.get("puntaje") and b.get("puntaje"):
                    pares.append({"dominio": c.get("dominio"), "modalidad": f["modalidad"], "area": f["area"],
                                  "chatbot": float(b["puntaje"]), "medico": float(c["puntaje"])})
    return pares


def icc_2_1(x, y):
    """ICC(2,1): dos vías, efectos aleatorios, acuerdo absoluto, medida única."""
    n = len(x)
    if n < 3:
        return None
    k = 2
    datos = list(zip(x, y))
    gran = sum(x + y) / (n * k)
    medias_f = [(a + b) / 2 for a, b in datos]
    medias_c = [sum(x) / n, sum(y) / n]
    ssr = k * sum((m - gran) ** 2 for m in medias_f)
    ssc = n * sum((m - gran) ** 2 for m in medias_c)
    sst = sum((v - gran) ** 2 for v in x + y)
    sse = sst - ssr - ssc
    msr, msc, mse = ssr / (n - 1), ssc / (k - 1), sse / ((n - 1) * (k - 1))
    den = msr + (k - 1) * mse + k * (msc - mse) / n
    return round((msr - mse) / den, 3) if den else None


def kappa_ponderada(x, y, categorias=5):
    """Kappa con pesos cuadráticos sobre los 5 niveles."""
    a = [indice_nivel(v) for v in x]
    b = [indice_nivel(v) for v in y]
    n = len(a)
    if n < 3:
        return None
    k = categorias
    obs = [[0] * k for _ in range(k)]
    for i, j in zip(a, b):
        obs[i][j] += 1
    fa = [sum(obs[i]) for i in range(k)]
    fb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = ((i - j) ** 2) / ((k - 1) ** 2)
            num += w * obs[i][j]
            den += w * fa[i] * fb[j] / n
    return round(1 - num / den, 3) if den else None


def metricas(pares):
    if not pares:
        return None
    x = [p["chatbot"] for p in pares]
    y = [p["medico"] for p in pares]
    niv = [(indice_nivel(a), indice_nivel(b)) for a, b in zip(x, y)]
    return {
        "n": len(pares),
        "icc": icc_2_1(x, y),
        "kappa": kappa_ponderada(x, y),
        "acuerdo_1": round(100 * sum(abs(i - j) <= 1 for i, j in niv) / len(niv), 1),
        "acuerdo_exacto": round(100 * sum(i == j for i, j in niv) / len(niv), 1),
        "mae": round(sum(abs(a - b) for a, b in zip(x, y)) / len(x), 2),
        "sesgo": round(sum(a - b for a, b in zip(x, y)) / len(x), 2),
    }


def interpretar_icc(v):
    if v is None:
        return "Datos insuficientes"
    if v < 0.5:
        return "Pobre (< 0.50)"
    if v < 0.75:
        return "Moderado (0.50–0.75)"
    if v < 0.9:
        return "Bueno (0.75–0.90)"
    return "Excelente (> 0.90)"


def interpretar_kappa(v):
    if v is None:
        return "Datos insuficientes"
    for lim, txt in [(0.2, "Leve"), (0.4, "Aceptable"), (0.6, "Moderada"), (0.8, "Sustancial")]:
        if v <= lim:
            return txt
    return "Casi perfecta"


# ===================== CALIFICACIÓN MÍNIMA Y RESULTADOS POR ESTUDIANTE =====================

def obtener_calificacion_minima():
    """Calificación mínima guardada (configuracion_examen.id = 1). None si no está configurada."""
    try:
        r = supabase.table("configuracion_examen").select("calificacion_minima").eq("id", 1).execute()
        v = (r.data or [{}])[0].get("calificacion_minima")
        return float(v) if v is not None else None
    except Exception:
        return None


def guardar_calificacion_minima(valor, usuario="admin"):
    try:
        supabase.table("configuracion_examen").update({
            "calificacion_minima": valor, "actualizado_por": usuario,
        }).eq("id", 1).execute()
        return True, "Calificación mínima guardada"
    except Exception as e:
        texto = str(e)
        if "calificacion_minima" in texto:
            return False, ("Falta la columna en la base. Ejecuta en Supabase → SQL Editor: "
                           "alter table public.configuracion_examen add column if not exists calificacion_minima numeric;")
        return False, f"Error: {texto}"


def resultados_por_estudiante():
    """{matricula: {"por_area": {num_area: final}, "final": promedio, "evaluadas": n, "estaciones": total}}
    usando la calificación final ponderada (chatbot + médico) de cada estación."""
    configs = obtener_ponderaciones() if tablas_dual_disponibles() else []
    salida = {}
    for f in construir_filas():
        r = calcular_final(f, ponderacion_para(f, configs)) if tablas_dual_disponibles() else {"final": None}
        d = salida.setdefault(f["matricula"], {"por_area": {}, "final": None, "evaluadas": 0, "estaciones": 0, "parcial": False})
        d["estaciones"] += 1
        if r.get("final") is not None:
            d["por_area"][f["num_area"]] = r["final"]
            d["evaluadas"] += 1
            d["parcial"] = d["parcial"] or bool(r.get("parcial"))
    for d in salida.values():
        d["final"] = promedio(list(d["por_area"].values()))
    return salida


def obtener_eval_chatbot_reciente(matricula, clave_caso):
    try:
        r = supabase.table("evaluacion_chatbot").select("*").eq("matricula", matricula).eq("clave_caso", clave_caso) \
            .order("fecha_evaluacion", desc=True).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None
