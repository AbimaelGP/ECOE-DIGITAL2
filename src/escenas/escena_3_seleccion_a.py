# escenas/escena_3_seleccion_a.py
import streamlit as st
from utils.database import obtener_datos_estudiante
from utils.actividad_estudiante import actualizar_actividad_estudiante


# ==================== CONFIGURACIÓN ====================

# Mapeo de consultorios a imágenes
# Alterna entre las 2 imágenes que ya tienes
CONSULTORIOS = {
    1: {'abierto': 'data/recursos/consultorios1_primersector.png', 'cerrado': 'data/recursos/consultorios1_cerrados.png'},
    2: {'abierto': 'data/recursos/consultorios2_segundosector.png', 'cerrado': 'data/recursos/consultorios2_cerrados.png'},
    3: {'abierto': 'data/recursos/consultorios1_primersector.png', 'cerrado': 'data/recursos/consultorios1_cerrados.png'},
    4: {'abierto': 'data/recursos/consultorios2_segundosector.png', 'cerrado': 'data/recursos/consultorios2_cerrados.png'},
    5: {'abierto': 'data/recursos/consultorios1_primersector.png', 'cerrado': 'data/recursos/consultorios1_cerrados.png'},
    6: {'abierto': 'data/recursos/consultorios2_segundosector.png', 'cerrado': 'data/recursos/consultorios2_cerrados.png'},
}


# ==================== FUNCIONES AUXILIARES ====================

def _inicializar_completados(modulos):
    """Inicializa el diccionario de módulos completados si no existe"""
    if 'modulos_completados' not in st.session_state:
        st.session_state['modulos_completados'] = {}
    
    for modulo in modulos:
        num = modulo['numero']
        if num not in st.session_state['modulos_completados']:
            st.session_state['modulos_completados'][num] = False


def _todos_completados(modulos):
    """Retorna True si TODOS los módulos asignados están completados"""
    asignados = [m for m in modulos if m['asignado']]
    if not asignados:
        return False
    return all(st.session_state['modulos_completados'].get(m['numero'], False) for m in asignados)


def _renderizar_tarjeta(modulo, matricula):
    """Renderiza una tarjeta individual de módulo"""
    num = modulo['numero']
    nombre_especialidad = modulo['nombre']
    caso = modulo['caso']
    asignado = modulo['asignado']
    completado = st.session_state['modulos_completados'].get(num, False)
    
    # ===== TÍTULO DEL MÓDULO =====
    st.markdown(
        f'<p style="color: #70257E; font-size: 20px; font-weight: 600; text-align: center; margin-bottom: 0.5rem;">ÁREA {num}</p>',
        unsafe_allow_html=True
    )
    
    # ===== NOMBRE DE LA ESPECIALIDAD =====
    if asignado:
        color_especialidad = "#252A38"
        texto_especialidad = nombre_especialidad
    else:
        color_especialidad = "#626779"
        texto_especialidad = "No asignado"
    
    st.markdown(
        f'<p style="color: {color_especialidad}; font-size: 16px; font-weight: 500; text-align: center; margin-bottom: 0.75rem;">{texto_especialidad}</p>',
        unsafe_allow_html=True
    )
    
    # ===== BOTÓN / ESTADO =====
    if completado:
        # Módulo completado
        st.button(
            "Completado",
            key=f"mod{num}_completado",
            use_container_width=True,
            disabled=True
        )
    elif asignado:
        # Módulo asignado y no completado
        if st.button(f"Iniciar Área", key=f"mod{num}", use_container_width=True):
            st.session_state['modulo_seleccionado'] = num
            st.session_state['caso_seleccionado'] = caso
            actualizar_actividad_estudiante(matricula, "Resolviendo modulo", modulo=num)
            st.session_state['pagina'] = 'historial_clinico'
            st.rerun()
    else:
        # No asignado - sin botón, solo espacio
        st.markdown(
            '<div style="height: 40px;"></div>',
            unsafe_allow_html=True
        )
    
    # ===== IMAGEN DEL CONSULTORIO =====
    consultorio = CONSULTORIOS.get(num, CONSULTORIOS[1])
    ruta_imagen = consultorio['abierto'] if completado else consultorio['cerrado']
    
    try:
        st.image(ruta_imagen, use_container_width=True)
    except:
        st.write(f"[Consultorio {num}]")
    
    # ===== LEYENDA INFERIOR =====
    if completado:
        st.markdown(
            '<p style="color: #008A4B; text-align: center; font-weight: 600;">✓ Completado</p>',
            unsafe_allow_html=True
        )
    else:
        # Espacio en blanco para mantener alineación
        st.markdown(
            '<p style="text-align: center; color: transparent;">-</p>',
            unsafe_allow_html=True
        )


# ==================== FUNCIÓN PRINCIPAL ====================

def mostrar():
    """Muestra la pantalla de selección de módulo (soporta 1-6 módulos)"""
    
    matricula = st.session_state['identificador']
    tiempo_inicio = st.session_state.get('tiempo_inicio_examen', None)
    
    # Registrar actividad
    actualizar_actividad_estudiante(matricula, "seleccion_modulo")
    
    # ===== OBTENER DATOS DEL ESTUDIANTE =====
    datos = obtener_datos_estudiante(matricula)
    
    if not datos:
        st.error("No se pudieron cargar los datos del estudiante")
        return
    
    modulos = datos.get('modulos', [])
    
    # Inicializar session_state de completados
    _inicializar_completados(modulos)
    
    # ===== CSS =====
    st.markdown("""
    <style>
        .stApp {
            background: #F1F2F5;
        }
        .stButton > button {
            background-color: #70257E;
            color: #FFFFFF;
            font-family: 'Poppins', sans-serif;
            font-weight: 500;
            padding: 0.75rem 1rem;
            border-radius: 10px;
            border: none;
            width: 100%;
            margin-bottom: 0.5rem;
        }
        .stButton > button:hover {
            background-color: #70257E;
        }
        .stButton > button:disabled {
            background-color: #E5E7EC;
            color: #303442;
            cursor: not-allowed;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ===== NOMBRE DEL ESTUDIANTE =====
    nombre = st.session_state['nombre']
    st.markdown(f"""
    <div style="margin-top: 2rem; margin-bottom: 1rem;">
        <p style="color: #252A38; font-family: Poppins; font-size: 48px; font-weight: 700; margin: 0;">
            {nombre}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== TÍTULO =====
    st.markdown("""
    <div style="margin-top: 2rem; margin-bottom: 2rem;">
        <p style="color: #252A38; font-family: Poppins; font-size: 32px; font-weight: 600; text-align: center;">
            Selecciona el área correspondiente
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== 3 FILAS DE 2 COLUMNAS =====
    for fila in range(3):
        col_izq, col_der = st.columns(2)
        
        # Módulo de la izquierda (índice 0, 2, 4)
        idx_izq = fila * 2
        if idx_izq < len(modulos):
            with col_izq:
                _renderizar_tarjeta(modulos[idx_izq], matricula)
        
        # Módulo de la derecha (índice 1, 3, 5)
        idx_der = fila * 2 + 1
        if idx_der < len(modulos):
            with col_der:
                _renderizar_tarjeta(modulos[idx_der], matricula)
        
        # Espacio entre filas
        st.markdown("<br>", unsafe_allow_html=True)
    
    # ===== BOTÓN FINALIZAR EXAMEN =====
    if _todos_completados(modulos):
        # Terminó el circuito: se evalúa automáticamente aunque no presione "Finalizar Examen"
        if not st.session_state.get('evaluacion_lanzada', False):
            from utils.evaluacion_automatica import lanzar_evaluacion
            lanzar_evaluacion(st.session_state.get('identificador'), st.session_state.get('nombre'))
            st.session_state['evaluacion_lanzada'] = True
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1.2, 2])
        with col2:
            if st.button("Finalizar Examen", use_container_width=True):
                st.session_state['pagina'] = 'examen_final'
                st.rerun()