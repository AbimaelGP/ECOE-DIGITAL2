# utils/guardar_historial.py
import streamlit as st
from utils.supabase_client import supabase
from datetime import datetime
import json

def guardar_historial_chat(matricula, modulo, clave_caso):
    """
    Guarda el historial del chat en la tabla historial_chat_estudiante
    """
    if not supabase:
        print("❌ Supabase no conectado")
        return False
    
    try:
        # 1. Obtener el historial del chat desde session_state
        chat_key = f"chat_{clave_caso}"
        historial_chat = st.session_state.get(chat_key, [])
        
        # 2. Convertir a JSON válido para Supabase
        historial_chat_json = json.dumps(historial_chat, ensure_ascii=False)
        
        # 3. Verificar si ya existe un registro para este estudiante, módulo y caso
        response = supabase.table("historial_chat_estudiante") \
            .select("*") \
            .eq("matricula", matricula) \
            .eq("modulo", modulo) \
            .eq("caso", clave_caso) \
            .execute()
        
        if response.data and len(response.data) > 0:
            # Si existe, ACTUALIZAR
            supabase.table("historial_chat_estudiante") \
                .update({
                    "mensajes": historial_chat_json,
                    "updated_at": datetime.now().isoformat()
                }) \
                .eq("matricula", matricula) \
                .eq("modulo", modulo) \
                .eq("caso", clave_caso) \
                .execute()
            print(f"✅ Chat actualizado para {matricula}, caso {clave_caso}, módulo {modulo}")
        else:
            # Si no existe, INSERTAR nuevo registro
            supabase.table("historial_chat_estudiante") \
                .insert({
                    "matricula": matricula,
                    "modulo": modulo,
                    "caso": clave_caso,
                    "mensajes": historial_chat_json
                }) \
                .execute()
            print(f"✅ Chat creado para {matricula}, caso {clave_caso}, módulo {modulo}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error guardando historial de chat: {e}")
        return False


def guardar_historial_preguntas(matricula, modulo, clave_caso, respuestas_diagnostico):
    """
    Guarda las respuestas del diagnóstico en la tabla historial_preguntas_estudiante
    """
    if not supabase:
        print("❌ Supabase no conectado")
        return False, "Supabase no conectado"
    
    try:
        # 1. Estructurar la nueva respuesta
        nueva_respuesta = {
            "fecha": datetime.now().isoformat(),
            "respuestas": respuestas_diagnostico
        }
        
        # 2. Verificar si ya existe un registro para este estudiante, módulo y caso
        response = supabase.table("historial_preguntas_estudiante") \
            .select("*") \
            .eq("matricula", matricula) \
            .eq("modulo", modulo) \
            .eq("caso", clave_caso) \
            .execute()
        
        if response.data and len(response.data) > 0:
            # Si existe, obtener las respuestas actuales y agregar la nueva
            respuestas_actuales = response.data[0].get('respuestas', [])
            
            # Si es string, parsear a lista
            if isinstance(respuestas_actuales, str):
                try:
                    respuestas_actuales = json.loads(respuestas_actuales)
                except:
                    respuestas_actuales = []
            
            # Si no es lista, convertir a lista
            if not isinstance(respuestas_actuales, list):
                respuestas_actuales = []
            
            # Agregar nueva respuesta
            respuestas_actuales.append(nueva_respuesta)
            
            # Actualizar
            supabase.table("historial_preguntas_estudiante") \
                .update({
                    "respuestas": respuestas_actuales,
                    "updated_at": datetime.now().isoformat()
                }) \
                .eq("matricula", matricula) \
                .eq("modulo", modulo) \
                .eq("caso", clave_caso) \
                .execute()
            
            print(f"✅ Preguntas actualizadas para {matricula}, caso {clave_caso}, módulo {modulo}")
            print(f"📊 Total de respuestas: {len(respuestas_actuales)}")
            
        else:
            # Si no existe, INSERTAR nuevo registro con la primera respuesta
            supabase.table("historial_preguntas_estudiante") \
                .insert({
                    "matricula": matricula,
                    "modulo": modulo,
                    "caso": clave_caso,
                    "respuestas": [nueva_respuesta]
                }) \
                .execute()
            
            print(f"✅ Preguntas creadas para {matricula}, caso {clave_caso}, módulo {modulo}")
        
        return True, "Diagnóstico guardado exitosamente"
        
    except Exception as e:
        print(f"❌ Error guardando historial de preguntas: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error: {str(e)}"


def obtener_historial_chat(matricula, modulo, clave_caso):
    """
    Obtiene el historial del chat de la tabla historial_chat_estudiante
    """
    if not supabase:
        return []
    
    try:
        response = supabase.table("historial_chat_estudiante") \
            .select("mensajes") \
            .eq("matricula", matricula) \
            .eq("modulo", modulo) \
            .eq("caso", clave_caso) \
            .execute()
        
        if response.data and len(response.data) > 0:
            mensajes = response.data[0].get('mensajes', [])
            if isinstance(mensajes, str):
                try:
                    mensajes = json.loads(mensajes)
                except:
                    mensajes = []
            return mensajes
        return []
        
    except Exception as e:
        print(f"❌ Error obteniendo historial de chat: {e}")
        return []


def obtener_historial_preguntas(matricula, modulo, clave_caso):
    """
    Obtiene el historial de preguntas de la tabla historial_preguntas_estudiante
    """
    if not supabase:
        return []
    
    try:
        response = supabase.table("historial_preguntas_estudiante") \
            .select("respuestas") \
            .eq("matricula", matricula) \
            .eq("modulo", modulo) \
            .eq("caso", clave_caso) \
            .execute()
        
        if response.data and len(response.data) > 0:
            respuestas = response.data[0].get('respuestas', [])
            if isinstance(respuestas, str):
                try:
                    respuestas = json.loads(respuestas)
                except:
                    respuestas = []
            return respuestas
        return []
        
    except Exception as e:
        print(f"❌ Error obteniendo historial de preguntas: {e}")
        return []


def limpiar_historial_chat(matricula, modulo, clave_caso):
    """
    Limpia el historial del chat de la tabla historial_chat_estudiante
    """
    if not supabase:
        return False
    
    try:
        supabase.table("historial_chat_estudiante") \
            .update({
                "mensajes": [],
                "updated_at": datetime.now().isoformat()
            }) \
            .eq("matricula", matricula) \
            .eq("modulo", modulo) \
            .eq("caso", clave_caso) \
            .execute()
        return True
    except Exception as e:
        print(f"❌ Error limpiando historial de chat: {e}")
        return False


def guardar_estudios_solicitados(matricula, modulo, clave_caso, estudios):
    """Guarda la lista de estudios solicitados en historial_chat_estudiante
    (columna estudios_solicitados). Crea el registro si aún no existe.
    Nunca borra mensajes: solo actualiza esa columna."""
    if not supabase:
        return False
    try:
        r = supabase.table("historial_chat_estudiante").select("id") \
            .eq("matricula", matricula).eq("modulo", modulo).eq("caso", clave_caso).execute()
        if r.data:
            supabase.table("historial_chat_estudiante").update({
                "estudios_solicitados": list(estudios),
                "updated_at": datetime.now().isoformat(),
            }).eq("id", r.data[0]["id"]).execute()
        else:
            supabase.table("historial_chat_estudiante").insert({
                "matricula": matricula, "modulo": modulo, "caso": clave_caso,
                "mensajes": [], "estudios_solicitados": list(estudios),
            }).execute()
        return True
    except Exception as e:
        print(f"⚠️ Error guardando estudios solicitados (¿falta la migración 002?): {e}")
        return False
