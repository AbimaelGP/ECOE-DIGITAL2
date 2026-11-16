# components/boton_cerrar_sesion.py
import streamlit as st
from utils.actividad_estudiante import finalizar_sesion_estudiante

def mostrar_boton_cerrar_sesion():
    """Muestra un boton para cerrar sesion con confirmacion y registro"""
    
    if 'confirmar_cerrar' not in st.session_state:
        st.session_state['confirmar_cerrar'] = False
    
    matricula = st.session_state.get('identificador', 'desconocido')
    tipo_usuario = st.session_state.get('tipo_usuario', '')
    session_id_guardado = st.session_state.get('session_id', None)
    
    # Usamos la misma proporción [2, 1.2, 2] para alinear con el botón de continuar
    col1, col2, col3 = st.columns([2, 1.2, 2])
    
    with col2:
        if st.button("Cerrar sesión", key="boton_cerrar_sesion_principal", use_container_width=True):
            st.session_state['confirmar_cerrar'] = True
            
        if st.session_state.get('confirmar_cerrar', False):
            with st.popover("Confirmar cierre de sesión", use_container_width=True):
                st.markdown("¿Estás seguro de que deseas cerrar sesión?")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Sí", key="confirmar_si", use_container_width=True):
                        if tipo_usuario == 'estudiante' and matricula and matricula != 'desconocido':
                            finalizar_sesion_estudiante(matricula, session_id_guardado)
                        
                        st.session_state.clear()
                        st.rerun()
                with col_b:
                    if st.button("Cancelar", key="confirmar_no", use_container_width=True):
                        st.session_state['confirmar_cerrar'] = False
                        st.rerun()