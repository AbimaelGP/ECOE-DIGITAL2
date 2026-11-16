# escenas/crear_caso/utils.py
import streamlit as st
from datetime import datetime
from utils.supabase_client import supabase, SUPABASE_URL

# ==================== CONSTANTES ====================

CODIGO_ESPECIALIDAD = {
    "Medicina Familiar": "MF",
    "Medicina Interna": "MI",
    "Pediatría": "PED",
    "Ginecología y Obstetricia": "GO",
    "Cirugía": "CIR",
    "Urgencias": "URG"
}

TIPOS_CASO = ["Paciente Virtual", "Paciente Estandarizado", "Estático"]

# Claves de session_state
KEY_CASO = 'caso_en_creacion'
KEY_MODO = 'modo_creacion_caso'  # 'crear' o 'editar'


# ==================== FUNCIONES DE SESSION STATE ====================

def inicializar_caso():
    """Inicializa el diccionario del caso en session_state si no existe"""
    if KEY_CASO not in st.session_state:
        st.session_state[KEY_CASO] = {
            # Paso 1
            'id_caso': '',
            'nombre_caso': '',
            'especialidad': '',
            'autor': '',
            'responsable': '',
            'tipo_caso': 'Estático',
            # Paso 2 (Competencias)
            'competencias_seleccionadas': [],
            # Paso 3
            'sprite_url': None,
            'nombre': '',
            'visible_nombre': True,
            'edad': '',
            'visible_edad': True,
            'sexo': 'Femenino',
            'visible_sexo': True,
            'motivo_consulta': '',
            'visible_motivo': True,
            'descripcion': '',
            'visible_descripcion': True,
            'antecedentes': '',
            'visible_antecedentes': True,
            'medicamentos_actuales': '',
            'visible_medicamentos': True,
            'visible_sprite': True,
            'instrucciones_caso': '',
            'guion_paciente': '',
            # Paso 4 (Estudios)
            'estudios_incluidos': [],
            'valores_estudios': {},
            # Paso 5 (Solución)
            'diagnostico_correcto': '',
            'diagnostico_alternativo': '',
            'tratamiento_esperado': '',
            'errores_criticos': '',
            'preguntas_caso': [],
        }


def obtener_caso():
    """Retorna el diccionario del caso en creación"""
    return st.session_state.get(KEY_CASO, {})


def actualizar_caso(campo, valor):
    """Actualiza un campo del caso en creación"""
    if KEY_CASO not in st.session_state:
        inicializar_caso()
    st.session_state[KEY_CASO][campo] = valor


def limpiar_caso():
    """Limpia el caso en creación"""
    if KEY_CASO in st.session_state:
        del st.session_state[KEY_CASO]
    if 'sprite_seleccionado' in st.session_state:
        del st.session_state['sprite_seleccionado']
    if 'imagenes_subidas' in st.session_state:
        del st.session_state['imagenes_subidas']
    if 'imagenes_editadas' in st.session_state:
        del st.session_state['imagenes_editadas']
    if 'mostrar_selector_sprite' in st.session_state:
        del st.session_state['mostrar_selector_sprite']


# ==================== FUNCIONES DE MODO (CREAR/EDITAR) ====================

def iniciar_modo_crear():
    """Inicia el flujo en modo CREAR (limpia todo)"""
    limpiar_caso()
    st.session_state[KEY_MODO] = 'crear'
    if 'clave_caso_editando' in st.session_state:
        del st.session_state['clave_caso_editando']


def iniciar_modo_editar(clave_caso):
    """
    Inicia el flujo en modo EDITAR.
    Carga los datos del caso desde Supabase en session_state.
    Retorna True si se cargó exitosamente, False si hubo error.
    """
    limpiar_caso()
    st.session_state[KEY_MODO] = 'editar'
    st.session_state['clave_caso_editando'] = clave_caso
    
    # Cargar el caso desde Supabase
    caso_db = obtener_caso_por_clave(clave_caso)
    if not caso_db:
        print(f"❌ No se encontró el caso {clave_caso} en Supabase")
        return False
    
    # Extraer datos de las columnas
    data = caso_db.get('data', {}) or {}
    solucion = caso_db.get('solucion', {}) or {}
    instrucciones = data.get('instrucciones', {}) or {}
    visibilidad = data.get('visibilidad', {}) or {}
    valores_estudios = caso_db.get('valores_estudios', {}) or {}
    imagenes_estudios = caso_db.get('imagenes_estudios', {}) or {}
    competencias_guardadas = caso_db.get('rubrica_competencias', []) or []
    
    # Reconstruir el diccionario del caso
    st.session_state[KEY_CASO] = {
        # ===== Paso 1 =====
        'id_caso': caso_db.get('clave_caso', ''),
        'nombre_caso': data.get('nombre_caso', ''),
        'especialidad': caso_db.get('especialidad', ''),
        'autor': caso_db.get('responsable', ''),
        'responsable': caso_db.get('responsable', ''),
        'tipo_caso': caso_db.get('tipo_caso', 'Estático'),
        
        # ===== Paso 2 - Competencias =====
        'competencias_seleccionadas': competencias_guardadas,
        
        # ===== Paso 3 - Datos del paciente =====
        'sprite_url': caso_db.get('sprite_url'),
        'nombre': data.get('nombre', ''),
        'edad': data.get('edad', ''),
        'sexo': data.get('sexo', 'Femenino'),
        'motivo_consulta': data.get('motivo_consulta', ''),
        'descripcion': data.get('descripcion', ''),
        'antecedentes': data.get('antecedentes', ''),
        'medicamentos_actuales': data.get('medicamentos_actuales', ''),
        
        # ===== Instrucciones =====
        'instrucciones_caso': instrucciones.get('instrucciones_caso', ''),
        'guion_paciente': instrucciones.get('guion_paciente', ''),
        
        # ===== Visibilidad =====
        'visible_sprite': visibilidad.get('sprite', True),
        'visible_nombre': visibilidad.get('nombre', True),
        'visible_edad': visibilidad.get('edad', True),
        'visible_sexo': visibilidad.get('sexo', True),
        'visible_motivo': visibilidad.get('motivo_consulta', True),
        'visible_descripcion': visibilidad.get('descripcion', True),
        'visible_antecedentes': visibilidad.get('antecedentes', True),
        'visible_medicamentos': visibilidad.get('medicamentos_actuales', True),
        
        # ===== Paso 4 - Estudios =====
        'estudios_incluidos': list(valores_estudios.keys()),
        'valores_estudios': valores_estudios,
        
        # ===== Paso 5 - Solución =====
        'diagnostico_correcto': solucion.get('diagnostico_correcto', ''),
        'diagnostico_alternativo': solucion.get('diagnostico_alternativo', ''),
        'tratamiento_esperado': solucion.get('tratamiento_esperado', ''),
        'errores_criticos': solucion.get('errores_criticos', ''),
        'preguntas_caso': solucion.get('preguntas', []),
    }
    
    # Cargar imágenes existentes en session_state
    if imagenes_estudios:
        st.session_state['imagenes_subidas'] = {
            f"{clave_caso}_{nombre}": url for nombre, url in imagenes_estudios.items()
        }
    
    # Cargar sprite seleccionado
    if caso_db.get('sprite_url'):
        st.session_state['sprite_seleccionado'] = caso_db.get('sprite_url')
    
    print(f"✅ Caso {clave_caso} cargado para edición")
    return True


def obtener_modo():
    """Retorna el modo actual: 'crear' o 'editar'"""
    return st.session_state.get(KEY_MODO, 'crear')


def es_modo_editar():
    """Retorna True si estamos en modo editar"""
    return obtener_modo() == 'editar'


def obtener_clave_caso_editando():
    """Retorna la clave del caso que se está editando"""
    return st.session_state.get('clave_caso_editando', '')


# ==================== FUNCIONES DE SUPABASE ====================

def obtener_siguiente_numero_caso(codigo):
    """Obtiene el siguiente número de caso para un código de especialidad"""
    if not supabase:
        return 1
    
    try:
        response = supabase.table("casos_clinicos").select("clave_caso").like("clave_caso", f"{codigo}%").order("clave_caso", desc=True).limit(1).execute()
        if response.data and len(response.data) > 0:
            ultima_clave = response.data[0]['clave_caso']
            try:
                numero = int(ultima_clave[len(codigo):])
                return numero + 1
            except ValueError:
                return 1
        return 1
    except Exception as e:
        print(f"Error al obtener siguiente número: {e}")
        return 1


def obtener_medico_supabase(identificador):
    """Obtiene el perfil del médico"""
    if not supabase:
        return None
    
    try:
        response = supabase.table("perfiles_medicos").select("*").eq("identificador", identificador).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error al obtener médico: {e}")
        return None


def obtener_caso_por_clave(clave_caso):
    """Obtiene un caso clínico existente"""
    if not supabase:
        return None
    
    try:
        response = supabase.table("casos_clinicos").select("*").eq("clave_caso", clave_caso).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error al obtener caso: {e}")
        return None


def subir_imagen_supabase(archivo_subido, clave_caso, nombre_estudio):
    """Sube una imagen a Supabase Storage y retorna la URL pública"""
    if not supabase or not archivo_subido:
        return None
    
    try:
        extension = archivo_subido.name.split('.')[-1].lower()
        nombre_archivo = f"{clave_caso}_{nombre_estudio.replace(' ', '_')}.{extension}"
        ruta_storage = f"{clave_caso}/imagenes/{nombre_archivo}"
        
        supabase.storage.from_("casos_clinicos").upload(
            path=ruta_storage,
            file=archivo_subido.getvalue(),
            file_options={"content-type": archivo_subido.type}
        )
        
        url_publica = supabase.storage.from_("casos_clinicos").get_public_url(ruta_storage)
        return url_publica
    except Exception as e:
        print(f"❌ Error al subir imagen: {e}")
        return None


# ==================== FUNCIONES DE SPRITES ====================

def obtener_sprite_segun_edad_sexo(edad, sexo):
    """Retorna la URL del sprite según edad y sexo"""
    if edad < 12:
        categoria = "ninos"
    elif edad < 20:
        categoria = "adolescentes"
    elif edad < 60:
        categoria = "adultos"
    else:
        categoria = "adulto_mayor"
    
    if sexo.lower() == "femenino":
        genero = "femenino"
    else:
        genero = "masculino"
    
    return f"{SUPABASE_URL}/storage/v1/object/public/sprites/{categoria}_{genero}.png"


def obtener_sprites_disponibles():
    """Retorna la lista de sprites disponibles"""
    return [
        {"nombre": "Niño", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/ninos_masculino.png"},
        {"nombre": "Niña", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/ninos_femenino.png"},
        {"nombre": "Adolescente M", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adolescentes_masculino.png"},
        {"nombre": "Adolescente F", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adolescentes_femenino.png"},
        {"nombre": "Adulto M", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adultos_masculino.png"},
        {"nombre": "Adulto F", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adultos_femenino.png"},
        {"nombre": "Adulto Mayor M", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adulto_mayor_masculino.png"},
        {"nombre": "Adulto Mayor F", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adulto_mayor_femenino.png"}
    ]


# ==================== VALORES PREDETERMINADOS DE ESTUDIOS ====================

def obtener_valores_estudios_predeterminados():
    """Retorna la estructura de estudios con valores por defecto"""
    return {
        "Biometria Hematica": {
            "tipo": "parametros",
            "parametros": {
                "Hemoglobina": {"valor": 14.5, "unidad": "g/dL"},
                "Hematocrito": {"valor": 42, "unidad": "%"},
                "Leucocitos": {"valor": 7.5, "unidad": "x10³/µL"},
                "Plaquetas": {"valor": 250, "unidad": "x10³/µL"}
            }
        },
        "Prueba de glucosa en sangre": {
            "tipo": "parametros",
            "parametros": {
                "Glucosa": {"valor": 90, "unidad": "mg/dL"}
            }
        },
        "Troponinas": {
            "tipo": "parametros",
            "parametros": {
                "Troponina I": {"valor": 0.02, "unidad": "ng/mL"}
            }
        },
        "Pruebas de funcion pulmonar": {
            "tipo": "parametros",
            "parametros": {
                "FEV1": {"valor": 3.5, "unidad": "L"},
                "FVC": {"valor": 4.2, "unidad": "L"},
                "Relacion FEV1/FVC": {"valor": 83, "unidad": "%"}
            }
        },
        "Electrocardiograma": {
            "tipo": "imagen",
            "parametros": {}
        },
        "EGO": {
            "tipo": "parametros",
            "parametros": {
                "Proteinas": {"valor": "Negativo", "unidad": "mg/dL"},
                "Leucocitos": {"valor": 2, "unidad": "por campo"},
                "Densidad": {"valor": 1.020, "unidad": ""},
                "pH": {"valor": 6.0, "unidad": ""},
                "Glucosa": {"valor": "Negativo", "unidad": ""}
            }
        },
        "Rayos X de Torax": {
            "tipo": "imagen",
            "parametros": {}
        },
        "Ecocardiograma": {
            "tipo": "imagen",
            "parametros": {}
        },
        "Radiografia de Abdomen": {
            "tipo": "imagen",
            "parametros": {}
        },
        "Tomografia Abdominal": {
            "tipo": "imagen",
            "parametros": {}
        }
    }

# ==================== UNIDADES DISPONIBLES ====================

UNIDADES_DISPONIBLES = [
    "g/dL", "mg/dL", "ng/mL", "pg/mL", "mEq/L", "mmol/L",
    "%", "x10³/µL", "x10⁶/µL", "/µL",
    "L", "mL", "dL",
    "U/L", "UI/L",
    "LPM", "rpm",
    "mmHg", "cmH2O",
    "°C", "°F",
    "kg", "g", "mg",
    "cm", "m", "mm",
    "años", "meses",
    "segundos", "minutos",
    "por campo", "Negativo/Positivo",
    "Unidad", ""
]


# ==================== FUNCIONES DE IMÁGENES ====================

def subir_imagen_caso(archivo_subido, clave_caso, identificador_medico, nombre_estudio):
    """
    Sube una imagen a Supabase Storage con el formato:
    {clave_caso}_{id_medico}_{nombre_estudio}.png
    """
    if not supabase or not archivo_subido:
        return None
    
    try:
        import unicodedata
        
        # Limpiar nombre
        nombre_limpio = unicodedata.normalize('NFKD', nombre_estudio).encode('ASCII', 'ignore').decode('ASCII')
        nombre_limpio = nombre_limpio.replace(' ', '_').replace('/', '_').replace('\\', '_')
        nombre_limpio = nombre_limpio.replace('(', '_').replace(')', '_').replace(',', '_')
        nombre_limpio = nombre_limpio.replace('.', '_').replace(':', '_').replace(';', '_').replace('-', '_')
        
        while '__' in nombre_limpio:
            nombre_limpio = nombre_limpio.replace('__', '_')
        
        nombre_limpio = nombre_limpio.strip('_')[:50]
        
        # Reducir peso (máx. 1600 px, JPG calidad 85) antes de subir
        from utils.imagenes import optimizar_imagen
        datos, extension, content_type = optimizar_imagen(archivo_subido.getvalue())

        base = f"{clave_caso}/imagenes/{clave_caso}_{identificador_medico}_{nombre_limpio}"
        ruta_storage = f"{base}.{extension}"
        
        # Reemplazar la imagen anterior de este mismo estudio (en cualquier formato)
        try:
            supabase.storage.from_("casos_clinicos").remove([f"{base}.png", f"{base}.jpg"])
        except:
            pass
        
        # Subir
        supabase.storage.from_("casos_clinicos").upload(
            path=ruta_storage,
            file=datos,
            file_options={"content-type": content_type}
        )
        
        url_publica = supabase.storage.from_("casos_clinicos").get_public_url(ruta_storage)
        return url_publica
        
    except Exception as e:
        print(f"❌ Error al subir imagen: {e}")
        return None

def eliminar_imagen_caso(clave_caso, identificador_medico, nombre_estudio):
    """Elimina una imagen de Supabase Storage."""
    if not supabase or not clave_caso or not identificador_medico or not nombre_estudio:
        return False
    
    try:
        nombre_estudio_limpio = nombre_estudio.replace(' ', '_').replace('/', '_').replace('\\', '_')
        base = f"{clave_caso}/imagenes/{clave_caso}_{identificador_medico}_{nombre_estudio_limpio}"
        
        supabase.storage.from_("casos_clinicos").remove([f"{base}.png", f"{base}.jpg"])
        return True
        
    except Exception as e:
        return False


# ==================== VALIDACIÓN DE ESTUDIOS ====================

def validar_nombre_estudio_unico(nombre, estudios_actuales, nombre_original=None):
    """Verifica que el nombre del estudio no se duplique"""
    if nombre_original and nombre == nombre_original:
        return True
    return nombre not in estudios_actuales


def crear_estudio_vacio_imagen(nombre):
    """Crea la estructura inicial de un estudio de imagen"""
    return {"tipo": "imagen", "imagen_url": None, "parametros": {}}


def crear_estudio_vacio_parametros(nombre):
    """Crea la estructura inicial de un estudio de valores"""
    return {"tipo": "parametros", "imagen_url": None, "parametros": {}}


# ==================== NAVEGACIÓN ====================

def ir_a_paso(numero_paso):
    """Navega al paso especificado del flujo (crear o editar)."""
    modo = obtener_modo()
    if modo == 'editar':
        st.session_state['pagina'] = f'editar_caso_paso_{numero_paso}'
    else:
        st.session_state['pagina'] = f'crear_caso_paso_{numero_paso}'
    st.rerun()


def cancelar_creacion():
    """Cancela el flujo actual y vuelve al panel médico."""
    limpiar_caso()
    if KEY_MODO in st.session_state:
        del st.session_state[KEY_MODO]
    if 'clave_caso_editando' in st.session_state:
        del st.session_state['clave_caso_editando']
    st.session_state['pagina'] = 'panel_medico'
    st.rerun()


# ==================== COMPETENCIAS DEL PERFIL DE EGRESO ====================

COMPETENCIAS = {
    "BÁSICAS": {
        "Comunicación": [
            "1. Supera los obstáculos comunicativos en los intercambios de conversación.",
            "3. Manifiesta habilidades de lectura e interpretación de textos con un enfoque crítico.",
            "8. Emplea herramientas analíticas en la interpretación de resultados de investigación y construcción de alternativas.",
            "10. Interactúa en medios convencionales y virtuales aplicando diversas estrategias de comunicación."
        ],
        "Emprendimiento": [
            "1. Genera y desarrolla proyectos de bienes y servicios que contribuyan a la solución de problemas.",
            "2. Demuestra habilidades de creatividad e innovación al desarrollar estrategias.",
            "5. Muestra una actitud proactiva y positiva ante los retos y oportunidades."
        ],
        "Sociocultural": [
            "3. Interactúa con diferentes grupos sociales respetando su dignidad y los derechos de las personas.",
            "5. Manifiesta interés por la diversidad cultural y étnica reconociendo la interculturalidad."
        ],
        "Solución de Problemas": [
            "2. Analiza críticamente los diferentes componentes de un problema y sus interrelaciones.",
            "4. Identifica soluciones con base en diferentes fuentes de información confiables.",
            "6. Utiliza y promueve el empleo de diferentes métodos y/o estrategias de solución.",
            "7. Propone soluciones creativas e innovadoras asumiendo una actitud responsable."
        ],
        "Trabajo en Equipo y Liderazgo": [
            "1. Identifica habilidades pertinentes para el emprendimiento considerando las metas.",
            "3. Interactúa con diversas personas privilegiando el diálogo en la solución de conflictos.",
            "6. Desarrolla una cultura de trabajo grupal hacia el logro de una meta común.",
            "8. Demuestra respeto, tolerancia, responsabilidad y pluralidad en el trabajo grupal."
        ],
        "Información Digital": [
            "1. Identifica las necesidades de información que contribuyen al logro de metas.",
            "2. Elige fuentes de información y las discrimina por su relevancia y confiabilidad.",
            "3. Emplea recursos digitales y TAC para gestionar, localizar y clasificar información."
        ]
    },
    "PROFESIONALES": {
        "Cultura en Salud": [
            "3. Determina, practica y promueve estilos de vida saludable.",
            "4. Promueve el mejoramiento de la calidad de vida humana atendiendo a indicadores.",
            "5. Demuestra una actitud de servicio y de participación comunitaria."
        ],
        "Elementos Conceptuales Básicos": [
            "4. Explica la salud y la enfermedad como un continum de la vida humana.",
            "5. Relaciona los elementos salud y enfermedad con la persona y su ambiente.",
            "7. Explica los principios básicos de la bioética relacionados con su desempeño profesional."
        ],
        "Prestación de Servicios de Salud": [
            "1. Se integra en el trabajo inter y multidisciplinario para la atención a la salud.",
            "3. Desarrolla programas, proyectos y acciones educativas, preventivas y curativas.",
            "5. Realiza las acciones pertinentes para la solución de los problemas de salud.",
            "7. Replantea los problemas y alternativas de solución."
        ]
    },
    "ESPECÍFICAS": {
        "Salud Pública y Sistemas de Salud": [
            "1. Clasifica, ordena y explica los factores causales de los principales problemas de salud.",
            "2. Promueve el mejoramiento de la calidad de vida humana.",
            "3. Aplica actividades de protección específica para la Salud.",
            "4. Aplica y promueve estilos de vida saludable.",
            "5. Analiza e interpreta las características determinantes de los estilos de vida.",
            "6. Muestra una actitud de servicio y de participación comunitaria."
        ],
        "Diagnóstico y Manejo de Patologías": [
            "1. Aplica el interrogatorio estructurado al paciente sobre su estado de salud.",
            "2. Examina al paciente en forma completa y sistemática.",
            "3. Muestra el tipo de seguimiento que se realizará al paciente.",
            "4. Clasifica la patología de forma general y/o específica.",
            "5. Aplica tratamiento o reclasifica y deriva a otro nivel de competencia.",
            "6. Informa al paciente y/o familiares sobre el padecimiento.",
            "10. Reconoce y valora la necesidad de los distintos estudios auxiliares de diagnóstico.",
            "11. Interpreta la información proporcionada por la evaluación clínica."
        ],
        "Promoción y Prevención de la Salud": [
            "1. Planea programas de promoción y prevención de la salud.",
            "2. Promueve la participación de la comunidad para prevenir los riesgos.",
            "4. Muestra interés hacia la enseñanza de otros compañeros, personal y familia."
        ],
        "Investigación Biomédica": [
            "1. Realiza lectura crítica de la bibliografía pertinente.",
            "2. Interpreta los resultados de la investigación."
        ],
        "Administración de la Práctica Médica": [
            "1. Analiza el fundamento constitucional de la Ley General de Salud.",
            "2. Es veraz y objetivo en la recolección de la información proporcionada.",
            "3. Se muestra honesto y veraz al informar acerca del estado de salud del paciente."
        ]
    }
}


# ==================== CSS COMPARTIDO ====================

def aplicar_css_panel():
    """Aplica el CSS del panel médico a las escenas de crear caso"""
    st.markdown("""
    <style>
        .stApp { background-color: #F1F2F5 !important; }
        .medico-title { text-align: center; color: #252A38; font-family: 'Poppins', sans-serif; font-size: 42px; font-weight: 700; margin-top: 1rem; margin-bottom: 2rem; }
        .section-title { color: #252A38; font-family: 'Poppins', sans-serif; font-size: 24px; font-weight: 600; margin-top: 1.5rem; margin-bottom: 1rem; border-left: 4px solid #70257E; padding-left: 1rem; }
        .caso-nuevo-title { color: #252A38; font-family: 'Poppins', sans-serif; font-size: 28px; font-weight: 600; margin-bottom: 1.5rem; border-left: 4px solid #70257E; padding-left: 1rem; }
        
        .stButton button[type="primary"] { background-color: #70257E !important; color: #FFFFFF !important; border: 2px solid #70257E !important; font-weight: bold !important; }
        .stButton button[type="primary"]:hover { background-color: #70257E !important; }
        .stButton button:not([type="primary"]) { background-color: #E5E7EC !important; color: #303442 !important; border: 1px solid #E5E7EC !important; }
        
        .st-key-btn_siguiente_crear_caso button { background-color: #70257E !important; color: #FFFFFF !important; border: 2px solid #70257E !important; font-weight: bold !important; }
        .st-key-btn_siguiente_crear_caso button:hover { background-color: #70257E !important; color: #FFFFFF !important; }
        .st-key-btn_siguiente_crear_caso button:focus { background-color: #70257E !important; color: #FFFFFF !important; box-shadow: 0 0 0 3px rgba(112, 37, 126, 0.3) !important; }

        .stTextInput input, .stTextInput textarea { background-color: #FFFFFF !important; border: 2px solid #70257E !important; border-radius: 8px !important; color: #303442 !important; }
        .stTextInput input:focus, .stTextInput textarea:focus { border-color: #70257E !important; box-shadow: 0 0 0 2px rgba(112, 37, 126, 0.3) !important; outline: none !important; }
        
        .stSelectbox > div > div { background-color: #FFFFFF !important; border: 2px solid #70257E !important; border-radius: 8px !important; color: #303442 !important; }
        .stSelectbox > div > div:hover { border-color: #70257E !important; }
        .stSelectbox > div > div:focus-within { border-color: #70257E !important; box-shadow: 0 0 0 2px rgba(112, 37, 126, 0.3) !important; }
        .stSelectbox div[role="listbox"] { background-color: #FFFFFF !important; }
        .stSelectbox div[role="option"] { background-color: #FFFFFF !important; color: #303442 !important; }
        .stSelectbox div[role="option"]:hover { background-color: #E5E7EC !important; }
        
        textarea { background-color: #FFFFFF !important; border: 2px solid #70257E !important; border-radius: 8px !important; color: #303442 !important; }
        textarea:focus { border-color: #70257E !important; box-shadow: 0 0 0 2px rgba(112, 37, 126, 0.3) !important; outline: none !important; }
        
        .stCheckbox label { color: #303442 !important; font-weight: 500 !important; }
        
        .stRadio > div { background-color: #FFFFFF !important; padding: 10px 15px !important; border-radius: 8px !important; border: 2px solid #70257E !important; }
        .stRadio label { color: #303442 !important; font-weight: 500 !important; }
        
        hr { border-color: #E5E7EC !important; border-width: 1px !important; }
        
        .info-paso { background-color: #FFFFFF; padding: 10px 15px; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #70257E; color: #303442; font-family: 'Poppins', sans-serif; }
        .info-paso small { color: #626779; }
    </style>
    """, unsafe_allow_html=True)