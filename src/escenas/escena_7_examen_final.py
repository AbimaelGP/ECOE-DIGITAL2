# escenas/escena_7_examen_final.py
import streamlit as st
from utils.database import obtener_datos_estudiante


def mostrar():
    """Muestra la pantalla final del examen (valida que todos los módulos estén completados)"""
    
    matricula = st.session_state['identificador']
    nombre = st.session_state['nombre']
    
    # ===== VALIDAR QUE TODOS LOS MÓDULOS ASIGNADOS ESTÉN COMPLETADOS =====
    datos = obtener_datos_estudiante(matricula)
    modulos_completados = st.session_state.get('modulos_completados', {})
    
    if not datos:
        st.error("No se pudieron cargar los datos del estudiante")
        return
    
    modulos_asignados = [m for m in datos.get('modulos', []) if m['asignado']]
    todos_completados = all(
        modulos_completados.get(m['numero'], False) 
        for m in modulos_asignados
    )
    
    # ===== SI NO ESTÁN COMPLETADOS, MOSTRAR ADVERTENCIA =====
    if not todos_completados:
        st.warning("Aún tienes áreas pendientes por completar.")
        
        # Mostrar cuáles faltan
        pendientes = [
            m for m in modulos_asignados 
            if not modulos_completados.get(m['numero'], False)
        ]
        
        st.markdown("**Áreas pendientes:**")
        for m in pendientes:
            st.markdown(f"- Área {m['numero']}: {m['nombre']}")
        
        st.markdown("---")
        if st.button("Volver a selección de áreas", use_container_width=True):
            st.session_state['pagina'] = 'seleccion_a'
            st.rerun()
        return
    
    # ===== SI TODO ESTÁ COMPLETADO, MOSTRAR PANTALLA FINAL =====
    if not st.session_state.get('examen_finalizado', False):
        st.session_state['examen_finalizado'] = True
    
    # CSS
    st.markdown("""
    <style>
        .stApp {
            background: #F1F2F5;
        }
        .final-container {
            background-color: #FFFFFF;
            border-radius: 20px;
            padding: 3rem;
            text-align: center;
            max-width: 600px;
            margin: 3rem auto;
        }
        .final-titulo {
            color: #252A38;
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 1rem;
        }
        .final-mensaje {
            color: #303442;
            font-size: 20px;
            margin-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="final-container">
        <div class="final-titulo">Examen finalizado</div>
        <div class="final-mensaje">
            {nombre}, has concluido todas las áreas.
        </div>
    </div>
    """, unsafe_allow_html=True)