import streamlit as st
from datetime import datetime
from pathlib import Path

# Importar componentes
from components.header import mostrar_header
from components.footer import mostrar_footer
from components.boton_cerrar_sesion import mostrar_boton_cerrar_sesion

# Importar escenas
from escenas import (
    escena_1_login,
    escena_2_inicio_estudiante,
    escena_3_seleccion_a,
    escena_3_1_instrucciones,
    escena_7_examen_final,
    escena_historial_clinico,
    escena_admin,
    escena_monitoreo,
    escena_evaluacion,
    panel_medico,
    escena_modulo,
    escena_crear_editar_circuito,
)

# Importar pasos de crear/editar caso (compartidos)
from escenas import escena_medico_evaluar
from utils.migraciones import aplicar_migraciones

from escenas.crear_caso import (
    paso_1_datos_basicos,
    paso_2_competencias,  # NUEVO
    paso_3_general,       # RENOMBRADO
    paso_4_estudios,      # RENOMBRADO
    paso_5_solucion, 
)

# Configuración de la página
st.set_page_config(
    page_title="ECOE - Sistema de Exámenes",
    page_icon="🏥",
    layout="wide"
)

# Migraciones de base de datos (solo agregan; se aplican una vez si existe DATABASE_URL)
aplicar_migraciones()

# Inicializar estado de sesión
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# CSS global
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Poppins', sans-serif;
    }

    .stApp {
        background-color: #F1F2F5;
        color: #303442;
    }

    /* Header superior de Streamlit (blanco para que no estorbe) */
    header[data-testid="stHeader"] {
        background-color: #FFFFFF !important;
    }

    /* Barra lateral BLANCA */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
    }

    /* Texto oscuro en la barra lateral para que sea legible */
    [data-testid="stSidebar"] * {
        color: #252A38 !important;
    }

    /* Títulos globales en morado */
    h1, h2, h3, h4, h5, h6 {
        color: #70257E !important;
    }

    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input,
    .stDateInput input,
    .stTimeInput input,
    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect [data-baseweb="select"] > div {
        background-color: #FFFFFF;
        border-color: #70257E;
        color: #303442;
    }

    .stButton button[kind="primary"],
    .stFormSubmitButton button[kind="primary"] {
        background-color: #70257E;
        border-color: #70257E;
        color: #FFFFFF;
    }

    .stButton button[kind="primary"]:hover,
    .stFormSubmitButton button[kind="primary"]:hover,
    .stButton button[kind="primary"]:focus,
    .stFormSubmitButton button[kind="primary"]:focus {
        background-color: #70257E;
        border-color: #70257E;
        color: #FFFFFF;
    }

    .stButton button,
    .stFormSubmitButton button {
        background-color: #E5E7EC;
        border-color: #E5E7EC;
        color: #303442;
    }

    .stButton button:hover,
    .stFormSubmitButton button:hover,
    .stButton button:focus,
    .stFormSubmitButton button:focus {
        background-color: #E5E7EC;
        border-color: #E5E7EC;
        color: #303442;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

# ============================================
# NAVEGACIÓN PRINCIPAL
# ============================================

# Mostrar header siempre (logos)
mostrar_header()

# Si no está autenticado, mostrar login
if not st.session_state['autenticado']:
    escena_1_login.mostrar()
    mostrar_footer()

# Si está autenticado, mostrar la escena correspondiente
else:
    pagina = st.session_state.get('pagina', 'inicio_estudiante')
    
    # Durante el examen del estudiante no se puede cerrar sesión (también oculta un botón "viejo"
    # que Streamlit deja visible mientras la pantalla de instrucciones se recarga cada segundo)
    from utils.progreso_examen import examen_en_curso
    if examen_en_curso() and pagina != 'examen_final':
        st.markdown("<style>.st-key-boton_cerrar_sesion_principal, .st-key-confirmar_si, .st-key-confirmar_no "
                    "{display: none !important;}</style>", unsafe_allow_html=True)
    
    if pagina == 'inicio_estudiante':
        escena_2_inicio_estudiante.mostrar()
    
    elif pagina == 'seleccion_a':
        escena_3_seleccion_a.mostrar()
    
    elif pagina == 'instrucciones':
        escena_3_1_instrucciones.mostrar()
    
    elif pagina == 'examen_final':
        escena_7_examen_final.mostrar()
    
    elif pagina == 'admin':
        escena_admin.mostrar()
    
    elif pagina == 'monitoreo':
        escena_monitoreo.mostrar()
    
    elif pagina == 'evaluacion':
        escena_evaluacion.mostrar()
    
    elif pagina == 'panel_medico': 
        panel_medico.mostrar()
    
    # ===== CREAR CASO (5 pasos) =====
    elif pagina == 'crear_caso_paso_1':
        paso_1_datos_basicos.mostrar()

    elif pagina == 'crear_caso_paso_2':
        paso_2_competencias.mostrar()

    elif pagina == 'crear_caso_paso_3':
        paso_3_general.mostrar()

    elif pagina == 'crear_caso_paso_4':
        paso_4_estudios.mostrar()

    elif pagina == 'crear_caso_paso_5':
        paso_5_solucion.mostrar()
    
    # ===== EDITAR CASO (5 pasos - mismos archivos) =====
    elif pagina == 'editar_caso_paso_1':
        paso_1_datos_basicos.mostrar()
    elif pagina == 'editar_caso_paso_2':
        paso_2_competencias.mostrar()
    elif pagina == 'editar_caso_paso_3':
        paso_3_general.mostrar()
    elif pagina == 'editar_caso_paso_4':
        paso_4_estudios.mostrar()
    elif pagina == 'editar_caso_paso_5':
        paso_5_solucion.mostrar()
    
    elif pagina == 'modulo_activo':
        escena_modulo.mostrar()

    # ===== OTRAS ESCENAS =====
    elif pagina == 'historial_clinico':
        caso_id = st.session_state.get('caso_seleccionado', 'MF0001')
        modulo_seleccionado = st.session_state.get('modulo_seleccionado', 1)
        
        escena_destino = "modulo_activo"  # ← siempre
        
        escena_historial_clinico.mostrar(caso_id, modulo_seleccionado, escena_destino)

    elif pagina == 'editar_circuito':
        escena_crear_editar_circuito.mostrar()

    # ===== EVALUACIÓN DOCENTE (MÉDICO) =====
    elif pagina == 'evaluacion_docente':
        escena_medico_evaluar.mostrar_formulario()

    elif pagina == 'medico_eval_chatbot':
        escena_medico_evaluar.mostrar_eval_chatbot()
        
    else:
        st.write(f"Escena no implementada: {pagina}")
    
    # Mostrar botón de cerrar sesión (no durante el examen del estudiante)
    from utils.progreso_examen import examen_en_curso
    if not examen_en_curso():
        mostrar_boton_cerrar_sesion()
    mostrar_footer()