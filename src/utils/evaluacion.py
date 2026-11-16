# utils/evaluacion.py
import streamlit as st
from datetime import datetime
from utils.supabase_client import supabase
import json

def obtener_evaluacion(matricula, modulo, clave_caso):
    """
    Obtiene la evaluación de un estudiante para un módulo específico
    """
    if not supabase:
        return None
    
    try:
        response = supabase.table("evaluacion_estudiantes")\
            .select("*")\
            .eq("matricula", matricula)\
            .eq("modulo", modulo)\
            .eq("clave_caso", clave_caso)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error al obtener evaluación: {e}")
        return None

def crear_evaluacion(matricula, modulo, clave_caso):
    """
    Crea una nueva evaluación para un estudiante
    """
    if not supabase:
        return False, "Supabase no conectado"
    
    try:
        # Verificar si ya existe
        existente = obtener_evaluacion(matricula, modulo, clave_caso)
        if existente:
            return True, "La evaluación ya existe"
        
        data = {
            "matricula": matricula,
            "modulo": modulo,
            "clave_caso": clave_caso,
            "historial_chat": [],
            "historial_preguntas": [],
            "evaluado": False,
            "fecha_inicio": datetime.now().isoformat()
        }
        
        response = supabase.table("evaluacion_estudiantes").insert(data).execute()
        return True, "Evaluación creada exitosamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def guardar_mensaje_chat(matricula, modulo, clave_caso, mensaje, rol):
    """
    Guarda un mensaje del chat en el historial
    """
    if not supabase:
        return False, "Supabase no conectado"
    
    try:
        # Obtener evaluación actual
        evaluacion = obtener_evaluacion(matricula, modulo, clave_caso)
        if not evaluacion:
            return False, "No se encontró la evaluación"
        
        # Obtener historial actual
        historial = evaluacion.get("historial_chat", [])
        
        # Agregar nuevo mensaje
        nuevo_mensaje = {
            "rol": rol,  # "estudiante" o "bot"
            "mensaje": mensaje,
            "timestamp": datetime.now().isoformat()
        }
        historial.append(nuevo_mensaje)
        
        # Actualizar en Supabase
        supabase.table("evaluacion_estudiantes")\
            .update({
                "historial_chat": historial,
                "updated_at": datetime.now().isoformat()
            })\
            .eq("matricula", matricula)\
            .eq("modulo", modulo)\
            .eq("clave_caso", clave_caso)\
            .execute()
        
        return True, "Mensaje guardado"
    except Exception as e:
        return False, f"Error: {str(e)}"

def guardar_pregunta_diagnostico(matricula, modulo, clave_caso, pregunta, respuesta):
    """
    Guarda una pregunta del diagnóstico y su respuesta
    """
    if not supabase:
        return False, "Supabase no conectado"
    
    try:
        evaluacion = obtener_evaluacion(matricula, modulo, clave_caso)
        if not evaluacion:
            return False, "No se encontró la evaluación"
        
        historial_preguntas = evaluacion.get("historial_preguntas", [])
        
        nueva_pregunta = {
            "pregunta": pregunta,
            "respuesta": respuesta,
            "timestamp": datetime.now().isoformat()
        }
        historial_preguntas.append(nueva_pregunta)
        
        supabase.table("evaluacion_estudiantes")\
            .update({
                "historial_preguntas": historial_preguntas,
                "updated_at": datetime.now().isoformat()
            })\
            .eq("matricula", matricula)\
            .eq("modulo", modulo)\
            .eq("clave_caso", clave_caso)\
            .execute()
        
        return True, "Pregunta guardada"
    except Exception as e:
        return False, f"Error: {str(e)}"

def guardar_evaluacion_completa(matricula, modulo, clave_caso, puntuacion=None, feedback=None):
    """
    Marca la evaluación como completada y guarda la puntuación
    """
    if not supabase:
        return False, "Supabase no conectado"
    
    try:
        data = {
            "evaluado": True,
            "fecha_fin": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        if puntuacion is not None:
            data["puntuacion"] = puntuacion
        if feedback is not None:
            data["feedback"] = feedback
        
        supabase.table("evaluacion_estudiantes")\
            .update(data)\
            .eq("matricula", matricula)\
            .eq("modulo", modulo)\
            .eq("clave_caso", clave_caso)\
            .execute()
        
        return True, "Evaluación completada"
    except Exception as e:
        return False, f"Error: {str(e)}"

def obtener_historial_completo(matricula):
    """
    Obtiene todo el historial de evaluaciones de un estudiante
    """
    if not supabase:
        return []
    
    try:
        response = supabase.table("evaluacion_estudiantes")\
            .select("*")\
            .eq("matricula", matricula)\
            .order("fecha_inicio", desc=True)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Error al obtener historial: {e}")
        return []

def inicializar_evaluacion_si_no_existe(matricula, modulo, clave_caso):
    """
    Inicializa la evaluación si no existe
    """
    evaluacion = obtener_evaluacion(matricula, modulo, clave_caso)
    if not evaluacion:
        return crear_evaluacion(matricula, modulo, clave_caso)
    return True, "Evaluación ya existe"