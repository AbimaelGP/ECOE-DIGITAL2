# utils/casos.py
from utils.supabase_client import supabase
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def cargar_info_caso(caso_id):
    """Carga la información del caso desde Supabase (con visibilidad e instrucciones)"""
    
    if not supabase:
        return None
    
    try:
        response = supabase.table("casos_clinicos").select("*").eq("clave_caso", caso_id).execute()
        if response.data and len(response.data) > 0:
            caso = response.data[0]
            data = caso.get('data', {}) or {}
            
            return {
                # ===== Datos del paciente =====
                'nombre': data.get('nombre', 'Paciente'),
                'edad': data.get('edad', 'No especificada'),
                'sexo': data.get('sexo', 'No especificado'),
                'motivo_consulta': data.get('motivo_consulta', 'No especificado'),
                'descripcion': data.get('descripcion', 'No disponible'),
                'antecedentes': data.get('antecedentes', 'No disponibles'),
                'medicamentos_actuales': data.get('medicamentos_actuales', 'No refiere tratamiento actual'),
                
                # ===== Sprite y estudios =====
                'sprite_url': caso.get('sprite_url'),
                'valores_estudios': caso.get('valores_estudios', {}),
                
                # ===== NUEVOS CAMPOS =====
                'nombre_caso': data.get('nombre_caso', ''),
                'instrucciones': data.get('instrucciones', {}),
                'visibilidad': data.get('visibilidad', {}),
                
                # ===== Metadata útil =====
                'clave_caso': caso.get('clave_caso', ''),
                'especialidad': caso.get('especialidad', ''),
                'tipo_caso': caso.get('tipo_caso', 'Estático'),
                'responsable': caso.get('responsable', ''),          # ← NUEVO
                'fecha_actualizacion': caso.get('fecha_actualizacion', ''),  # ← NUEVO

                'solucion': caso.get('solucion', {}),
                'rubrica_competencias': caso.get('rubrica_competencias', []) or [],  # ← NUEVO
            }
        return None
    except Exception as e:
        print(f"Error al cargar caso: {e}")
        return None


def obtener_sprite_url(caso_id):
    """Obtiene la URL del sprite del caso"""
    
    if not supabase:
        return None
    
    try:
        response = supabase.table("casos_clinicos").select("sprite_url").eq("clave_caso", caso_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get('sprite_url')
        return None
    except Exception as e:
        print(f"Error al obtener sprite: {e}")
        return None

def formatear_fecha_inteligente(fecha_str):
    if not fecha_str:
        return "-"
    
    try:
        # 1. Si la fecha no tiene 'Z' o '+00:00', se la agregamos para forzar que es UTC
        fecha_str_clean = str(fecha_str)
        if not fecha_str_clean.endswith('Z') and '+' not in fecha_str_clean:
            if 'T' in fecha_str_clean:
                fecha_str_clean = fecha_str_clean.split('.')[0] + "+00:00" # Quita microsegundos si los hay
            else:
                fecha_str_clean = fecha_str_clean.replace(' ', 'T') + "+00:00"
                
        fecha_utc = datetime.fromisoformat(fecha_str_clean)
            
        # 2. Convertir a hora de México (Zona Centro)
        zona_mexico = ZoneInfo("America/Mexico_City")
        fecha_local = fecha_utc.astimezone(zona_mexico)
        
        # 3. Obtener la fecha y hora actual en México
        ahora_local = datetime.now(zona_mexico)
        
        # 4. Calcular diferencias
        diferencia = ahora_local - fecha_local
        dias_diferencia = diferencia.days
        
        # 5. Aplicar la lógica de formato
        if dias_diferencia == 0:
            return f"Hoy, {fecha_local.strftime('%H:%M')}"
        elif dias_diferencia == 1:
            return f"Ayer, {fecha_local.strftime('%H:%M')}"
        elif dias_diferencia < 365:
            return fecha_local.strftime('%d-%b').capitalize()
        else:
            return fecha_local.strftime('%d-%b-%Y').capitalize()
            
    except Exception as e:
        print(f"Error formateando fecha: {e}")
        return str(fecha_str)[:10]