import streamlit as st

def mostrar():
    """Muestra la página de evaluación de exámenes"""
    
    # CSS
    st.markdown("""
    <style>
        .stApp {
            background-color: #F1F2F5 !important;
        }
        .stApp > div:first-child {
            background-color: #F1F2F5 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #70257E !important;
        }
        [data-testid="stSidebar"] * {
            color: #FFFFFF !important;
        }
        .evaluacion-title {
            text-align: center;
            color: #252A38;
            font-family: 'Poppins', sans-serif;
            font-size: 42px;
            font-weight: 700;
            margin-top: 1rem;
            margin-bottom: 2rem;
        }
        .section-title {
            color: #252A38;
            font-family: 'Poppins', sans-serif;
            font-size: 24px;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            border-left: 4px solid #70257E;
            padding-left: 1rem;
        }
        .stButton button {
            border-radius: 8px !important;
            font-weight: 500 !important;
        }
        .stButton button[key="btn_regresar"] {
            background-color: #E5E7EC !important;
            color: #303442 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Titulo
    st.markdown('<h1 class="evaluacion-title">Evaluación de Exámenes</h1>', unsafe_allow_html=True)
    
    # Mensaje de construcción
    st.markdown("""
    <div style="background-color: #FFFFFF; padding: 3rem; border-radius: 12px; border: 2px solid #70257E; text-align: center; margin-top: 2rem;">
        <h2 style="color: #252A38; margin-bottom: 1rem;">🚧 Sección en construcción</h2>
        <p style="color: #303442; font-size: 18px;">Próximamente estará disponible el chatbot evaluador</p>
        <p style="color: #626779; font-size: 14px;">Esta herramienta permitirá evaluar el desempeño de los estudiantes de forma interactiva</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Botón Regresar
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("Regresar", use_container_width=True, key="btn_regresar"):
            st.session_state['pagina'] = 'admin'
            st.rerun()
    
    # Sidebar    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**Administrador:** {st.session_state.get('nombre', 'Admin')}")
        st.markdown(f"**ID:** {st.session_state.get('identificador', '')}")
        st.markdown("---")
        st.markdown("**Evaluación de Exámenes**")
        
        if st.button("Cerrar sesión", use_container_width=True):
            for key in ['autenticado', 'tipo_usuario', 'identificador', 'nombre', 'permisos', 'pagina']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()