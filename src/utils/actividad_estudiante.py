import streamlit as st
from datetime import datetime, timedelta
from utils.horario import ahora as ahora_local
from utils.supabase_client import supabase
import uuid

def actualizar_actividad_estudiante(matricula, pantalla, modulo=None, estacion=None, circuito=None, progreso=None):
    """Actualiza o crea un registro de actividad para el estudiante"""
    if not supabase:
        return False
    
    try:
        data = {
            "pantalla_actual": pantalla,
            "hora_ultima_actividad": ahora_local().isoformat()
        }
        
        if modulo is not None:
            data["modulo_actual"] = modulo
        if estacion is not None:
            data["estacion_actual"] = estacion
        if circuito is not None:
            data["circuito"] = circuito
        if progreso is not None:
            data["progreso"] = progreso
        
        # Obtener IP
        try:
            ip = st.request.headers.get('X-Forwarded-For', st.request.remote_addr)
            if ip:
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                data["direccion_ip"] = ip
        except:
            pass
        
        # Asegurar que el session_id exista
        session_id = st.session_state.get('session_id', None)
        if not session_id:
            session_id = str(uuid.uuid4())
            st.session_state['session_id'] = session_id
        
        # Buscar si ESTE dispositivo ya tiene un registro activo
        response = supabase.table("actividad_estudiante")\
            .select("*")\
            .eq("matricula", matricula)\
            .eq("session_id", session_id)\
            .eq("estatus", "activo")\
            .execute()
        
        if response.data and len(response.data) > 0:
            # Si ya existe en este dispositivo, solo actualizamos
            supabase.table("actividad_estudiante")\
                .update(data)\
                .eq("matricula", matricula)\
                .eq("session_id", session_id)\
                .eq("estatus", "activo")\
                .execute()
        else:
            # Si es un dispositivo nuevo, creamos una nueva fila
            data["matricula"] = matricula
            data["estatus"] = "activo"
            data["session_id"] = session_id
            data["hora_inicio_sesion"] = ahora_local().isoformat()
            supabase.table("actividad_estudiante").insert(data).execute()
        
        return True
    except Exception as e:
        print(f"Error al actualizar actividad: {e}")
        return False

def limpiar_sesiones_antiguas(matricula):
    """Marca como finalizadas las sesiones antiguas del estudiante"""
    if not supabase:
        return False
    
    try:
        supabase.table("actividad_estudiante")\
            .update({
                "estatus": "finalizado",
                "hora_ultima_actividad": ahora_local().isoformat()
            })\
            .eq("matricula", matricula)\
            .eq("estatus", "activo")\
            .execute()
        return True
    except Exception as e:
        print(f"Error al limpiar sesiones: {e}")
        return False

def finalizar_sesion_estudiante(matricula, session_id=None):
    """Marca la sesion del estudiante como finalizada"""
    if not supabase:
        return False
    
    try:
        if not session_id:
            session_id = st.session_state.get('session_id', None)
        
        if session_id:
            supabase.table("actividad_estudiante")\
                .update({
                    "estatus": "finalizado",
                    "hora_ultima_actividad": ahora_local().isoformat()
                })\
                .eq("matricula", matricula)\
                .eq("session_id", session_id)\
                .eq("estatus", "activo")\
                .execute()
        else:
            supabase.table("actividad_estudiante")\
                .update({
                    "estatus": "finalizado",
                    "hora_ultima_actividad": ahora_local().isoformat()
                })\
                .eq("matricula", matricula)\
                .eq("estatus", "activo")\
                .execute()
        
        return True
    except Exception as e:
        print(f"Error al finalizar sesion: {e}")
        return False

def limpiar_sesiones_inactivas(minutos=5):
    """Cierra sesiones que no han tenido actividad en X minutos"""
    if not supabase:
        return False
    
    try:
        limite_tiempo = (ahora_local() - timedelta(minutes=minutos)).isoformat()
        
        supabase.table("actividad_estudiante")\
            .update({"estatus": "finalizado"})\
            .eq("estatus", "activo")\
            .lt("hora_ultima_actividad", limite_tiempo)\
            .execute()
        return True
    except Exception as e:
        print(f"Error al limpiar inactivos: {e}")
        return False

def obtener_actividad_estudiantes():
    """Obtiene la actividad actual de todos los estudiantes activos de hoy"""
    if not supabase:
        return []
    
    try:
        hoy_str = ahora_local().strftime("%Y-%m-%d")
        manana_str = (ahora_local() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = supabase.table("actividad_estudiante")\
            .select("*, perfiles_estudiantes(nombre_completo)")\
            .eq("estatus", "activo")\
            .gte("hora_inicio_sesion", hoy_str)\
            .lt("hora_inicio_sesion", manana_str)\
            .order("hora_ultima_actividad", desc=True)\
            .execute()
        
        estudiantes = []
        contador = 1
        
        # Contar cuántas sesiones tiene cada matrícula
        sesiones_por_estudiante = {}
        for actividad in response.data:
            matricula = actividad["matricula"]
            if matricula not in sesiones_por_estudiante:
                sesiones_por_estudiante[matricula] = 0
            sesiones_por_estudiante[matricula] += 1
        
        # Ordenar para que los que tienen múltiples sesiones salgan arriba
        datos_ordenados = sorted(
            response.data,
            key=lambda x: (
                -sesiones_por_estudiante.get(x["matricula"], 0),
                x.get("hora_ultima_actividad", "")
            )
        )
        
        # Diccionario para traducir el número al nombre del área
        nombres_areas = {
            1: "Medicina Familiar",
            2: "Medicina Interna",
            3: "Pediatría",
            4: "Ginecología y Obstetricia",
            5: "Cirugía",
            6: "Urgencias"
        }
        
        for actividad in datos_ordenados:
            perfil = actividad.get("perfiles_estudiantes", {})
            
            pantallas = {
                "login": "Iniciando sesion",
                "inicio": "Pantalla de inicio",
                "instrucciones": "Leyendo instrucciones",
                "seleccion_modulo": "Seleccionando area",
                "seleccion_a": "Seleccionando area",
                "examen_modulo": "Examen - Area",
                "historial_clinico": "Viendo historial clinico",
                "finalizado": "Examen finalizado"
            }
            
            pantalla_raw = actividad.get("pantalla_actual", "")
            pantalla_actual = pantalla_raw if pantalla_raw.startswith("Resolviendo") else pantallas.get(pantalla_raw, pantalla_raw if pantalla_raw else "Desconocido")
            
            hora_inicio_sesion = actividad.get("hora_inicio_sesion", "")
            if hora_inicio_sesion:
                try:
                    dt = datetime.fromisoformat(hora_inicio_sesion.replace('Z', '+00:00')) if 'T' in str(hora_inicio_sesion) else datetime.strptime(hora_inicio_sesion, "%Y-%m-%d %H:%M:%S")
                    hora_inicio_sesion = dt.strftime("%H:%M:%S")
                except:
                    hora_inicio_sesion = "No disponible"
            else:
                hora_inicio_sesion = "No disponible"
            
            hora_ultima = actividad.get("hora_ultima_actividad", "")
            if hora_ultima:
                try:
                    dt = datetime.fromisoformat(hora_ultima.replace('Z', '+00:00')) if 'T' in str(hora_ultima) else datetime.strptime(hora_ultima, "%Y-%m-%d %H:%M:%S")
                    hora_ultima = dt.strftime("%H:%M:%S")
                except:
                    hora_ultima = "No disponible"
            else:
                hora_ultima = "No disponible"
            
            session_id = actividad.get("session_id", "")
            session_short = session_id[:8] if session_id else "Sesion unica"
            
            matricula_actual = actividad["matricula"]
            es_doble = sesiones_por_estudiante.get(matricula_actual, 0) > 1
            
            ip = actividad.get("direccion_ip", "0.0.0.0")
            
            modulo_valor = actividad.get("modulo_actual", "-")
            if modulo_valor and str(modulo_valor).isdigit():
                area_mostrar = nombres_areas.get(int(modulo_valor), f"Area {modulo_valor}")
            elif modulo_valor and modulo_valor != "-":
                area_mostrar = str(modulo_valor)
            else:
                area_mostrar = "-"
            
            estudiantes.append({
                "No.": contador,
                "Matricula": actividad["matricula"],
                "Nombre": perfil.get("nombre_completo", "Desconocido"),
                "Pantalla": pantalla_actual,
                "Area": area_mostrar,
                "Hora Inicio Sesion": hora_inicio_sesion,
                "Ultima Actividad": hora_ultima,
                "Direccion IP": ip,
                "Dispositivo": "Multiple" if es_doble else "Unico",
                "Sesion ID": session_short,
                "_es_doble": es_doble
            })
            contador += 1
        
        return estudiantes
    except Exception as e:
        print(f"Error al obtener actividad: {e}")
        return []