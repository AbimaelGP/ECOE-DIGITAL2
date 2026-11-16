# utils/estudios.py
from utils.supabase_client import supabase


def listar_estudios_disponibles(caso_paciente):
    """
    Retorna la lista de estudios DISPONIBLES para un caso específico.
    Ahora lee los estudios que el médico creó en el caso.
    """
    if not supabase or not caso_paciente:
        return []
    
    try:
        response = supabase.table("casos_clinicos").select("valores_estudios").eq("clave_caso", caso_paciente).execute()
        
        if response.data and len(response.data) > 0:
            valores_estudios = response.data[0].get('valores_estudios', {}) or {}
            # Devolver solo las claves (nombres de estudios)
            return list(valores_estudios.keys())
        return []
    except Exception as e:
        print(f"Error listando estudios: {e}")
        return []


def obtener_valores_estudio(caso_paciente, nombre_estudio):
    """
    Obtiene los valores de un estudio específico desde Supabase.
    Retorna el diccionario completo del estudio:
    {
        "tipo": "imagen" | "parametros",
        "imagen_url": str | None,
        "parametros": { "Hemoglobina": {"valor": "14.5", "unidad": "g/dL"}, ... }
    }
    """
    if not supabase or not caso_paciente:
        return None
    
    try:
        response = supabase.table("casos_clinicos").select("valores_estudios").eq("clave_caso", caso_paciente).execute()
        
        if response.data and len(response.data) > 0:
            valores_estudios = response.data[0].get('valores_estudios', {}) or {}
            datos_estudio = valores_estudios.get(nombre_estudio, {})
            return datos_estudio if datos_estudio else None
        return None
    except Exception as e:
        print(f"Error obteniendo valores del estudio: {e}")
        return None


def estudio_tiene_imagen(datos_estudio):
    """Verifica si un estudio tiene imagen"""
    if not datos_estudio:
        return False
    return datos_estudio.get('tipo') == 'imagen'


def obtener_imagen_estudio(datos_estudio):
    """
    Obtiene la URL de la imagen del estudio.
    Ahora lee desde datos_estudio['imagen_url'].
    """
    if not datos_estudio:
        return None
    return datos_estudio.get('imagen_url')