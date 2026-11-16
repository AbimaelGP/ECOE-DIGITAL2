# components/modal_diagnostico.py
import streamlit as st
from utils.guardar_historial import guardar_historial_preguntas
from utils.casos import cargar_info_caso


def mostrar_modal_diagnostico(caso_paciente, matricula, tiempo_inicio_examen_global, modulo_seleccionado, escena="primer_modulo"):
    """Muestra el panel de diagnóstico con preguntas (todos los campos obligatorios)"""
    
    # CSS específico para hacer que este panel se vea secundario
    st.markdown("""
    <style>
        .titulo-secundario-diag {
            font-size: 22px !important;
            font-weight: 600 !important;
            color: #252A38 !important;
            margin-bottom: 1rem !important;
            border-bottom: 2px solid #E5E7EC;
            padding-bottom: 0.5rem;
        }
        .seccion-diag {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #303442 !important;
            margin-top: 1.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        /* Reducir tamaño de los labels de los text_area */
        .stTextArea label p {
            font-size: 14px !important;
            font-weight: 500 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    key_diagnostico = f'diagnostico_realizado_{escena}_{modulo_seleccionado}'
    if key_diagnostico not in st.session_state:
        st.session_state[key_diagnostico] = False
    
    # ===== CARGAR PREGUNTAS DEL CASO =====
    info_caso = cargar_info_caso(caso_paciente)
    preguntas_caso = []
    if info_caso:
        solucion = info_caso.get('solucion', {}) or {}
        preguntas_caso = solucion.get('preguntas', []) or []
    
    # Título más pequeño
    st.markdown('<div class="titulo-secundario-diag">Panel de Diagnóstico</div>', unsafe_allow_html=True)
    st.caption("Todos los campos marcados con * son obligatorios.")
    
    with st.form(key=f"form_diagnostico_{escena}_{modulo_seleccionado}"):
        
        # Campos con subtítulos más pequeños
        st.markdown('<div class="seccion-diag">Diagnóstico *</div>', unsafe_allow_html=True)
        diagnostico = st.text_area("¿Cuál es tu diagnóstico?", height=100, label_visibility="collapsed")
        
        st.markdown('<div class="seccion-diag">Explicación *</div>', unsafe_allow_html=True)
        explicacion = st.text_area("Explica cómo llegaste a esa conclusión", height=100, label_visibility="collapsed")
        
        st.markdown('<div class="seccion-diag">Tratamiento *</div>', unsafe_allow_html=True)
        tratamiento = st.text_area("¿Qué tratamiento recomiendas?", height=100, label_visibility="collapsed")
        
        # ===== PREGUNTAS DEL CASO =====
        respuestas_preguntas = {}
        
        if preguntas_caso:
            st.markdown("---")
            st.markdown('<div class="seccion-diag" style="color: #252A38 !important; border-bottom: 1px solid #70257E; padding-bottom: 5px;">Preguntas del Caso</div>', unsafe_allow_html=True)
            
            for i, pregunta_data in enumerate(preguntas_caso):
                texto_pregunta = pregunta_data.get('pregunta', '')
                if not texto_pregunta:
                    continue
                
                st.markdown(f'<div class="seccion-diag">{texto_pregunta} *</div>', unsafe_allow_html=True)
                respuesta = st.text_area(
                    "Tu respuesta",
                    height=80,
                    key=f"respuesta_pregunta_{escena}_{modulo_seleccionado}_{i}",
                    label_visibility="collapsed"
                )
                respuestas_preguntas[texto_pregunta] = respuesta
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Guardar y Terminar", use_container_width=True, type="primary")
        with col2:
            cancelar = st.form_submit_button("Cerrar", use_container_width=True)
        
        if submitted:
            # ===== VALIDACIONES =====
            errores = []
            
            if not diagnostico or not diagnostico.strip():
                errores.append("Diagnóstico")
            if not explicacion or not explicacion.strip():
                errores.append("Explicación")
            if not tratamiento or not tratamiento.strip():
                errores.append("Tratamiento")
            
            preguntas_vacias = []
            for i, pregunta_data in enumerate(preguntas_caso):
                texto_pregunta = pregunta_data.get('pregunta', '')
                if not texto_pregunta:
                    continue
                
                respuesta_estudiante = respuestas_preguntas.get(texto_pregunta, '')
                if not respuesta_estudiante or not respuesta_estudiante.strip():
                    preguntas_vacias.append(f"Pregunta {i + 1}")
            
            if preguntas_vacias:
                errores.append(f"Respuestas faltantes en: {', '.join(preguntas_vacias)}")
            
            if errores:
                st.error(f"Faltan campos obligatorios: {', '.join(errores)}")
            else:
                respuestas = {
                    'diagnostico': diagnostico,
                    'explicacion': explicacion,
                    'tratamiento': tratamiento,
                    'respuestas_preguntas': respuestas_preguntas
                }
                
                exito, mensaje = guardar_historial_preguntas(
                    matricula=matricula,
                    modulo=modulo_seleccionado,
                    clave_caso=caso_paciente,
                    respuestas_diagnostico=respuestas
                )
                
                if exito:
                    st.success("Diagnóstico guardado exitosamente")
                    st.session_state[f'diagnostico_{escena}_{modulo_seleccionado}'] = respuestas
                    st.session_state[key_diagnostico] = True
                    st.session_state[f'modal_diagnostico_abierto_{escena}_{modulo_seleccionado}'] = False
                    st.session_state['terminar_modulo_despues_diagnostico'] = True
                    st.rerun()
                else:
                    st.error(f"Error al guardar diagnóstico: {mensaje}")
        
        if cancelar:
            st.session_state[f'modal_diagnostico_abierto_{escena}_{modulo_seleccionado}'] = False
            st.rerun()


def abrir_modal_diagnostico(escena="primer_modulo", modulo_seleccionado=1):
    """Abre el panel de diagnóstico"""
    st.session_state[f'modal_diagnostico_abierto_{escena}_{modulo_seleccionado}'] = True


def limpiar_diagnostico(escena="primer_modulo", modulo_seleccionado=1):
    """Limpia el diagnóstico al terminar el módulo"""
    key_diagnostico = f'diagnostico_realizado_{escena}_{modulo_seleccionado}'
    if key_diagnostico in st.session_state:
        del st.session_state[key_diagnostico]
    
    modal_key = f'modal_diagnostico_abierto_{escena}_{modulo_seleccionado}'
    if modal_key in st.session_state:
        del st.session_state[modal_key]
    
    diagnostico_key = f'diagnostico_{escena}_{modulo_seleccionado}'
    if diagnostico_key in st.session_state:
        del st.session_state[diagnostico_key]