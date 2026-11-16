# utils/database.py
import hashlib
import random
from datetime import datetime
from utils.supabase_client import supabase

def generar_clave_acceso():
    """Genera una clave aleatoria de 6 dígitos"""
    return ''.join(str(random.randint(0, 9)) for _ in range(6))

def crear_estudiante_supabase(matricula, nombre_completo, contraseña, creado_por):
    """Crea un nuevo estudiante en Supabase"""
    if not supabase:
        return False, "Supabase no conectado", None
    
    password_hash = hashlib.sha256(contraseña.encode()).hexdigest()
    clave_acceso = generar_clave_acceso()
    
    try:
        # Insertar en tabla usuarios
        user_data = {
            "identificador": matricula,
            "nombre": nombre_completo,
            "tipo_usuario": "estudiante",
            "password_hash": password_hash
        }
        supabase.table("usuarios").insert(user_data).execute()
        
        # Insertar en perfiles_estudiantes
        perfil_data = {
            "matricula": matricula,
            "nombre_completo": nombre_completo,
            "clave_acceso": clave_acceso,
            "creado_por": creado_por
        }
        supabase.table("perfiles_estudiantes").insert(perfil_data).execute()
        
        return True, "Estudiante creado exitosamente", clave_acceso
    except Exception as e:
        return False, f"Error: {str(e)}", None

def obtener_estudiantes_supabase():
    """Obtiene todos los estudiantes desde Supabase"""
    if not supabase:
        return []
    
    try:
        response = supabase.table("usuarios").select("*").eq("tipo_usuario", "estudiante").execute()
        
        estudiantes = []
        for user in response.data:
            perfil_response = supabase.table("perfiles_estudiantes").select("*").eq("matricula", user["identificador"]).execute()
            perfil = perfil_response.data[0] if perfil_response.data else {}
            
            estudiantes.append({
                "matricula": user["identificador"],
                "nombre": user["nombre"],
                "clave_acceso": perfil.get("clave_acceso", ""),
                "numero_estudiante": perfil.get("numero_estudiante", ""),
                "circuito_asignado": perfil.get("circuito_asignado", ""),
                "fecha_examen": perfil.get("fecha_examen", ""),
                "hora_inicio": perfil.get("hora_inicio", ""),
                "hora_fin": perfil.get("hora_fin", ""),
                "creado_por": perfil.get("creado_por", ""),
                "fecha_creacion": perfil.get("fecha_creacion", "")
            })
        
        return estudiantes
    except Exception as e:
        print(f"Error al obtener estudiantes: {e}")
        return []

def actualizar_campo_estudiante_supabase(matricula, campo, valor):
    """Actualiza un campo específico del perfil del estudiante"""
    if not supabase:
        return False, "Supabase no conectado"
    
    campos_validos = ['numero_estudiante', 'circuito_asignado', 'fecha_examen', 'hora_inicio', 'hora_fin']
    
    if campo not in campos_validos:
        return False, f"Campo {campo} no válido"
    
    try:
        supabase.table("perfiles_estudiantes").update({campo: valor}).eq("matricula", matricula).execute()
        return True, "Actualizado correctamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def eliminar_estudiante_supabase(matricula):
    """Elimina un estudiante de Supabase"""
    if not supabase:
        return False, "Supabase no conectado"
    
    try:
        supabase.table("perfiles_estudiantes").delete().eq("matricula", matricula).execute()
        supabase.table("usuarios").delete().eq("identificador", matricula).execute()
        return True, "Estudiante eliminado correctamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def obtener_horario_estudiante(matricula):
    """Obtiene el horario de un estudiante desde Supabase"""
    if not supabase:
        return None
    
    try:
        perfil_response = supabase.table("perfiles_estudiantes").select("*").eq("matricula", matricula).execute()
        if perfil_response.data:
            perfil = perfil_response.data[0]
            return (
                perfil.get("fecha_examen", ""),
                perfil.get("hora_inicio", ""),
                perfil.get("hora_fin", ""),
                perfil.get("clave_acceso", ""),
                "Pendiente"
            )
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def obtener_datos_estudiante(matricula):
    """
    Obtiene todos los datos del estudiante incluyendo casos y módulos desde el circuito.
    
    Retorna un DICCIONARIO con la siguiente estructura:
    {
        'fecha_examen': str,
        'hora_inicio': str,
        'hora_fin': str,
        'clave_acceso': str,
        'estatus': str,
        'asesor': str,
        'circuito': str,
        'modulos': [  # Lista de hasta 6 módulos
            {
                'numero': 1,
                'nombre': 'Medicina Familiar',
                'caso': 'MF0004',
                'asignado': True
            },
            {
                'numero': 2,
                'nombre': 'Medicina Interna',
                'caso': 'MI0003',
                'asignado': True
            },
            ...
        ]
    }
    """
    if not supabase:
        print("DEBUG: Supabase no conectado")
        return None
    
    try:
        # Obtener perfil del estudiante
        perfil_response = supabase.table("perfiles_estudiantes").select("*").eq("matricula", matricula).execute()
        
        if not perfil_response.data:
            print("DEBUG: No se encontró el perfil del estudiante")
            return None
        
        perfil = perfil_response.data[0]
        circuito_nombre = perfil.get("circuito_asignado", "")
        
        modulos = []
        
        # Si tiene circuito asignado, obtener TODOS los casos y módulos
        if circuito_nombre:
            circuito_response = supabase.table("circuitos").select(
                "modulo_1, modulo_2, modulo_3, modulo_4, modulo_5, modulo_6, "
                "caso_1, caso_2, caso_3, caso_4, caso_5, caso_6"
            ).eq("nombre", circuito_nombre).execute()
            
            if circuito_response.data:
                circuito = circuito_response.data[0]
                
                # Iterar sobre los 6 módulos posibles
                for i in range(1, 7):
                    nombre_modulo = circuito.get(f"modulo_{i}", "") or ""
                    caso = circuito.get(f"caso_{i}", "") or ""
                    
                    # Determinar si está asignado
                    # Un módulo está asignado si:
                    # - Tiene nombre (no está vacío)
                    # - NO dice "No asignar"
                    # - Tiene caso (no está vacío)
                    asignado = (
                        nombre_modulo.strip() != "" 
                        and nombre_modulo.strip().lower() != "no asignar"
                        and caso.strip() != ""
                    )
                    
                    modulos.append({
                        'numero': i,
                        'nombre': nombre_modulo if nombre_modulo else "No asignar",
                        'caso': caso,
                        'asignado': asignado
                    })
            else:
                print(f"DEBUG: No se encontró el circuito '{circuito_nombre}'")
        else:
            print(f"DEBUG: Estudiante {matricula} no tiene circuito asignado")
        
        # Si no hay circuito, crear los 6 módulos vacíos
        if not modulos:
            for i in range(1, 7):
                modulos.append({
                    'numero': i,
                    'nombre': "No asignar",
                    'caso': "",
                    'asignado': False
                })
        
        resultado = {
            'fecha_examen': perfil.get("fecha_examen", ""),
            'hora_inicio': perfil.get("hora_inicio", ""),
            'hora_fin': perfil.get("hora_fin", ""),
            'clave_acceso': perfil.get("clave_acceso", ""),
            'estatus': "Pendiente",
            'asesor': "",
            'circuito': circuito_nombre,
            'modulos': modulos
        }
        
        print(f"DEBUG: Modulos asignados = {[m for m in modulos if m['asignado']]}")
        return resultado
        
    except Exception as e:
        print(f"ERROR en obtener_datos_estudiante: {e}")
        import traceback
        traceback.print_exc()
        return None


def actualizar_estatus_estudiante(matricula, nuevo_estatus):
    """Actualiza el estatus de un estudiante"""
    # Por ahora solo registra, puedes implementar después
    print(f"Actualizar estatus de {matricula} a {nuevo_estatus}")
    return True

def verificar_credenciales(identificador, password):
    """Verifica credenciales usando Supabase (mantener compatibilidad)"""
    from utils.supabase_client import verificar_credenciales_supabase
    return verificar_credenciales_supabase(identificador, password)