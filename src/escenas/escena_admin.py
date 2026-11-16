# escenas/escena_admin.py
import streamlit as st

# IMPORTACIONES RELATIVAS (con el punto) para evitar el circular import
from . import escena_admin_areas
from . import escena_admin_creadores
from . import escena_admin_resultados
from . import escena_admin_evaluacion
from . import escena_admin_dual
from . import escena_admin_confiabilidad

def mostrar():
    # CSS Global del Administrador
    st.markdown("""
    <style>
        .stApp { background-color: #F1F2F5 !important; }
        .stApp > div:first-child { background-color: #F1F2F5 !important; }
        [data-testid="stSidebar"] { background-color: #70257E !important; }
        [data-testid="stSidebar"] * { color: #FFFFFF !important; }
        .admin-title {
            text-align: center; color: #252A38; font-family: 'Poppins', sans-serif;
            font-size: 42px; font-weight: 700; margin-top: 1rem; margin-bottom: 2rem;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 1rem; background-color: #FFFFFF; border-radius: 10px; padding: 0.5rem; }
        .stTabs [data-baseweb="tab"] { color: #626779; font-size: 18px !important; font-weight: 600 !important; padding: 0.5rem 2rem !important; }
        .stTabs [aria-selected="true"] { background-color: #70257E !important; color: #FFFFFF !important; border-radius: 8px; }
        .stButton button { border-radius: 8px !important; font-weight: 500 !important; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="admin-title">Perfil de Administrador</h1>', unsafe_allow_html=True)
    
    # Pestañas principales
    tab_areas, tab_creadores, tab_resultados, tab_evaluacion, tab_confiabilidad = st.tabs([
        "Áreas", 
        "Creadores de Casos", 
        "Resultados y Estadísticas", 
        "Evaluación",
        "Confiabilidad IA"
    ])
    
    with tab_areas:
        escena_admin_areas.mostrar()
        
    with tab_creadores:
        escena_admin_creadores.mostrar()
        
    with tab_resultados:
        escena_admin_resultados.mostrar()
        
    with tab_evaluacion:
        en_detalle = escena_admin_dual.mostrar()
        if not en_detalle:
            st.markdown("---")
            escena_admin_evaluacion.mostrar()

    with tab_confiabilidad:
        escena_admin_confiabilidad.mostrar()
    
    # Sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**Administrador:** {st.session_state.get('nombre', 'Admin')}")
        st.markdown(f"**ID:** {st.session_state.get('identificador', '')}")
        st.markdown("---")
        
        if st.button("Cerrar sesión", use_container_width=True):
            for key in ['autenticado', 'tipo_usuario', 'identificador', 'nombre', 'permisos', 'pagina']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()