# utils/evaluador_batch.py
import os
import tempfile
import uuid
from PyPDF2 import PdfMerger
from utils.supabase_client import supabase
from utils.evaluador.evaluador_api import evaluar_y_generar_pdf
import requests
import json


def obtener_datos_estudiante(matricula):
    """Obtiene la info del estudiante y el circuito asignado."""
    res = supabase.table("perfiles_estudiantes").select("*").eq("matricula", matricula).execute()
    if not res.data: return None
    return res.data[0]

def obtener_casos_circuito(nombre_circuito):
    """Obtiene los casos del circuito."""
    res = supabase.table("circuitos").select("*").eq("nombre", nombre_circuito).execute()
    if not res.data: return []
    
    circuito = res.data[0]
    casos_asignados = []
    for i in range(1, 7):
        clave_caso = circuito.get(f"caso_{i}")
        area = circuito.get(f"modulo_{i}")
        if clave_caso and area and area != "No asignar":
            casos_asignados.append({"area": area, "clave_caso": clave_caso, "num_area": i})
    return casos_asignados

def generar_texto_conversacion(matricula, clave_caso):
    texto = ""
    
    # 1. Chat
    res_chat = supabase.table("historial_chat_estudiante").select("mensajes").eq("matricula", matricula).eq("caso", clave_caso).execute()
    if res_chat.data:
        for fila in res_chat.data:
            mensajes = fila.get("mensajes", [])
            
            # SI VIENE COMO STRING, LO CONVERTIMOS A LISTA/DICCIONARIO
            if isinstance(mensajes, str):
                try:
                    mensajes = json.loads(mensajes)
                except:
                    pass # Si no se puede, lo dejamos como está
                    
            if isinstance(mensajes, list):
                for m in mensajes:
                    if isinstance(m, dict):
                        rol = "Estudiante" if m.get("role") == "user" else "Paciente"
                        texto += f"{rol}: {m.get('content', '')}\n"
    
    texto += "\n--- RESPUESTAS A PREGUNTAS DE EVALUACIÓN ---\n"
    
    # 2. Preguntas
    res_preguntas = supabase.table("historial_preguntas_estudiante").select("respuestas").eq("matricula", matricula).eq("caso", clave_caso).execute()
    if res_preguntas.data:
        for fila in res_preguntas.data:
            respuestas = fila.get("respuestas", [])
            
            # SI VIENE COMO STRING, LO CONVERTIMOS A LISTA/DICCIONARIO
            if isinstance(respuestas, str):
                try:
                    respuestas = json.loads(respuestas)
                except:
                    pass
                    
            if isinstance(respuestas, list) and respuestas:
                # Se usa el último envío del estudiante (diagnóstico, explicación,
                # tratamiento y respuestas a las preguntas del caso)
                from utils.evaluacion_dual import texto_respuestas
                ultimo = respuestas[-1]
                if isinstance(ultimo, dict):
                    texto += texto_respuestas(ultimo.get("respuestas", ultimo)) + "\n"
    
    return texto

ORDEN_AREAS = ["BÁSICAS", "ESPECÍFICAS", "PROFESIONALES"]


def _a_formato_caratula(items, resumen=""):
    """Convierte la evaluación por competencias (chatbot o médico) al formato de la carátula institucional."""
    import re as _re
    evaluacion, cats = [], []
    for it in items:
        cat = (it.get("categoria") or "General").upper()
        if cat not in cats:
            cats.append(cat)
        texto = _re.sub(r"^\s*\d+\.\s*", "", it.get("texto", ""))
        evaluacion.append({
            "criterio": texto, "categoria": cat,
            "puntuacion": float(it.get("puntaje") or 0), "maxima": 10,
            "nivel": it.get("nivel", ""),
            "fortalezas": it.get("criterio", ""),
            "debilidades": it.get("para_subir") or it.get("comentario") or "",
            "justificacion": it.get("criterio", ""),
        })
    cats.sort(key=lambda c: ORDEN_AREAS.index(c) if c in ORDEN_AREAS else 99)
    rubrica = {"categorias": [{"nombre": c, "criterios": [e for e in evaluacion if e["categoria"] == c]} for c in cats]}
    return {"evaluacion": evaluacion, "observaciones": resumen}, rubrica


ESPERA_MEDICO = "ESPERA_MEDICO"


def _eval_chatbot_vigente(matricula, clave_caso):
    """Evaluación del chatbot ya guardada con la versión actual del prompt (para no repetirla)."""
    from utils import evaluacion_dual as ed
    try:
        r = supabase.table("evaluacion_chatbot").select("*").eq("matricula", matricula) \
            .eq("clave_caso", clave_caso).eq("prompt_version", ed.PROMPT_VERSION).execute()
        return r.data[-1] if r.data else None
    except Exception:
        return None


def _evaluar_y_pdf_unificado(matricula, nombre_completo, circuito, casos, progress_bar=None):
    """Una sola evaluación por caso (la misma de la tabla comparativa) y la carátula
    institucional se arma con ella: el PDF y la app muestran la misma calificación.

    El PDF se genera solo cuando TODAS las estaciones tienen evaluación. Si falta la del
    médico en un caso estandarizado, devuelve (False, "ESPERA_MEDICO: ...") y se vuelve a
    lanzar cuando el médico envía. Los casos ya evaluados por el chatbot no se re-evalúan."""
    from utils import evaluacion_dual as ed
    from utils.evaluador.evaluador_api import GeneradorCaratula
    from utils.pdf_subcompetencias import generar_pagina_subcompetencias, generar_resumen_circuito

    total = len(casos)
    estaciones, espera, errores = [], [], []
    # 1) Reunir la evaluación de cada estación
    for idx, caso in enumerate(casos):
        if progress_bar:
            progress_bar.progress(idx / total, text=f"Evaluando caso {idx + 1}/{total}: {caso['clave_caso']}")
        info = ed.obtener_caso(caso["clave_caso"]) or {}
        modalidad = ed.modalidad_de(info.get("tipo_caso")) if info else "—"
        est = {"area": caso["area"], "clave_caso": caso["clave_caso"], "modalidad": modalidad,
               "evaluador": None, "calificacion": None, "items": None, "resumen": "", "estado": ""}
        estaciones.append(est)
        if not info:
            est["estado"] = "Caso no encontrado"
            continue
        if modalidad == "Estandarizado":
            try:
                r = supabase.table("evaluacion_docente").select("*").eq("matricula", matricula) \
                    .eq("clave_caso", caso["clave_caso"]).eq("estatus", "enviada").execute()
                d = r.data[-1] if r.data else None
            except Exception:
                d = None
            if d:
                est.update(evaluador="Médico", items=ed._a_json(d.get("criterios"), []),
                           resumen=d.get("comentarios_generales") or "")
            else:
                est["estado"] = "Esperando médico"
                espera.append(caso["clave_caso"])
            continue
        ev = _eval_chatbot_vigente(matricula, caso["clave_caso"])
        if not ev:
            ok, msg = ed.evaluar_con_chatbot(matricula, caso["clave_caso"], caso.get("num_area"))
            if ok:
                ev = _eval_chatbot_vigente(matricula, caso["clave_caso"])
            elif "sin evidencia" in msg or "no tiene evidencia" in msg or "no tiene competencias" in msg:
                est["estado"] = "Sin evidencia" if "evidencia" in msg else "Sin competencias"
                continue
            else:
                errores.append(f"{caso['clave_caso']}: {msg}")
                continue
        if ev:
            est.update(evaluador="Chatbot", items=ed._a_json(ev.get("competencias"), []), resumen=ev.get("resumen", ""))

    for est in estaciones:
        if est["items"]:
            est["calificacion"] = ed.calificacion_por_areas(est["items"])

    if errores:
        return False, "No se pudo evaluar: " + " | ".join(errores)
    if espera:
        return False, f"{ESPERA_MEDICO}: falta la evaluación del médico en {', '.join(espera)}"
    if not any(e["items"] for e in estaciones):
        return False, "Ninguna estación tiene evaluación (" + ", ".join(e["estado"] for e in estaciones) + ")"

    # 2) Armar el PDF: resumen del circuito (si hay varias estaciones) + carátula y gráfica por estación
    if progress_bar:
        progress_bar.progress(0.95, text="Generando PDF...")
    temp_dir = tempfile.mkdtemp()
    rutas = []
    if len(estaciones) > 1:
        rutas.append(generar_resumen_circuito(estaciones, os.path.join(temp_dir, "00_resumen.pdf"),
                                              matricula=matricula, nombre=nombre_completo, circuito=circuito))
    for n, est in enumerate(estaciones, 1):
        if not est["items"]:
            continue
        etiqueta = f"{nombre_completo} - Estación {n}: {est['area']} ({est['clave_caso']})"
        evaluacion, rubrica = _a_formato_caratula(est["items"], est["resumen"])
        ruta_caso = os.path.join(temp_dir, f"{n:02d}_{est['clave_caso']}.pdf")
        ok_pdf, msg_pdf = GeneradorCaratula.generar_pdf(evaluacion, rubrica, ruta_caso, matricula=matricula, nombre=etiqueta)
        if not ok_pdf:
            return False, f"{est['clave_caso']}: {msg_pdf}"
        rutas.append(ruta_caso)
        try:
            rutas.append(generar_pagina_subcompetencias(
                est["items"], os.path.join(temp_dir, f"{n:02d}_{est['clave_caso']}_sub.pdf"),
                matricula=matricula, nombre=etiqueta))
        except Exception as e:
            print(f"⚠️ No se generó la gráfica por subcompetencia: {e}")

    if progress_bar:
        progress_bar.progress(1.0, text="Uniendo PDFs finales...")
    merger = PdfMerger()
    for r_pdf in rutas:
        merger.append(r_pdf)
    ruta_final = os.path.join(temp_dir, f"Evaluacion_{matricula}.pdf")
    merger.write(ruta_final)
    merger.close()
    return True, ruta_final


def evaluar_estudiante_completo(matricula, nombre_completo, circuito, progress_bar=None):
    try:
        casos = obtener_casos_circuito(circuito)
        if not casos:
            return False, "El circuito no tiene casos asignados."

        # Si existen las tablas de la evaluación dual, el PDF usa ESA evaluación (una sola fuente).
        try:
            from utils.evaluacion_dual import tablas_dual_disponibles
            if tablas_dual_disponibles():
                return _evaluar_y_pdf_unificado(matricula, nombre_completo, circuito, casos, progress_bar)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error en la evaluación: {e}"
        # (Respaldo: evaluador original, solo si la base no tiene las tablas nuevas)

        temp_dir = tempfile.mkdtemp()
        rutas_pdfs_generados = []
        total_casos = len(casos)
        
        for idx, caso in enumerate(casos):
            if progress_bar:
                progress_bar.progress((idx) / total_casos, text=f"Evaluando caso {idx+1}/{total_casos}: {caso['clave_caso']}")

            # 1. Obtener la rúbrica del caso
            res_caso = supabase.table("casos_clinicos").select("rubrica_competencias").eq("clave_caso", caso["clave_caso"]).execute()
            if not res_caso.data:
                continue
            
            rubrica_db = res_caso.data[0].get("rubrica_competencias", [])
            if isinstance(rubrica_db, str):
                try:
                    rubrica_db = json.loads(rubrica_db)
                except: pass

            # Creamos un archivo de texto temporal con INSTRUCCIONES CLARAS y la rúbrica en JSON
            texto_rubrica = f"""
INSTRUCCIONES PARA EL EVALUADOR:
Eres un médico experto evaluando a un estudiante. 
A continuación te presento las competencias que se deben evaluar en este caso.
Debes calificar del 1 al 10 cada una de estas competencias basándote en la conversación y las respuestas del estudiante.
Es OBLIGATORIO que devuelvas un JSON con la estructura exacta que se te pide en tus instrucciones de sistema, evaluando cada competencia de la lista.

COMPETENCIAS A EVALUAR:
{json.dumps(rubrica_db, ensure_ascii=False, indent=2)}
"""
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as tmp_rub_caso:
                tmp_rub_caso.write(texto_rubrica)
                ruta_rub_caso = tmp_rub_caso.name

            # 2. Obtener la conversación (Chat + Preguntas)
            texto_conversacion = generar_texto_conversacion(matricula, caso["clave_caso"])
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as tmp_conv:
                tmp_conv.write(texto_conversacion)
                ruta_conv = tmp_conv.name

            ruta_pdf_parcial = os.path.join(temp_dir, f"{caso['clave_caso']}.pdf")

            # 3. LLAMAR AL EVALUADOR
            # Le pasamos el txt que creamos arriba en lugar del word
            exito, msg = evaluar_y_generar_pdf(
                ruta_rubrica=ruta_rub_caso, # <-- Usamos el texto estructurado
                ruta_conversacion=ruta_conv,
                ruta_pdf_salida=ruta_pdf_parcial,
                matricula=matricula,
                nombre=f"{nombre_completo} - {caso['area']} ({caso['clave_caso']})"
            )

            # Limpieza
            if os.path.exists(ruta_rub_caso): os.remove(ruta_rub_caso)
            if os.path.exists(ruta_conv): os.remove(ruta_conv)

            if exito:
                rutas_pdfs_generados.append(ruta_pdf_parcial)
            else:
                print(f"Error evaluando caso {caso['clave_caso']}: {msg}")

            # 4. Evaluación estructurada por competencia (para la evaluación dual).
            #    Si falla o no existen las tablas nuevas, el PDF sigue igual.
            try:
                from utils.evaluacion_dual import tablas_dual_disponibles, evaluar_con_chatbot
                if tablas_dual_disponibles():
                    ok_dual, msg_dual = evaluar_con_chatbot(matricula, caso["clave_caso"], caso.get("num_area"))
                    print(f"Evaluación dual {caso['clave_caso']}: {msg_dual}")
            except Exception as e:
                print(f"⚠️ Evaluación dual no disponible para {caso['clave_caso']}: {e}")

        if not rutas_pdfs_generados:
            return False, "No se pudo generar ningún PDF (la IA falló)."

        # 4. Unir todos los PDFs
        if progress_bar:
            progress_bar.progress(1.0, text="Uniendo PDFs finales...")
            
        merger = PdfMerger()
        for pdf in rutas_pdfs_generados:
            merger.append(pdf)
        
        ruta_final = os.path.join(temp_dir, f"Evaluacion_{matricula}.pdf")
        merger.write(ruta_final)
        merger.close()

        return True, ruta_final

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, str(e)