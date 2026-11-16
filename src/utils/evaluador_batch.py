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

def evaluar_estudiante_completo(matricula, nombre_completo, circuito, progress_bar=None):
    try:
        casos = obtener_casos_circuito(circuito)
        if not casos:
            return False, "El circuito no tiene casos asignados."

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