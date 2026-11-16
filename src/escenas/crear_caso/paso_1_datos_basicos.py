# escenas/crear_caso/paso_1_datos_basicos.py
import streamlit as st
from escenas.crear_caso.utils import (
    aplicar_css_panel, inicializar_caso, obtener_caso, actualizar_caso,
    limpiar_caso, obtener_medico_supabase, obtener_siguiente_numero_caso,
    CODIGO_ESPECIALIDAD, TIPOS_CASO, ir_a_paso, cancelar_creacion,
    es_modo_editar, obtener_clave_caso_editando,
    KEY_CASO
)


def mostrar():
    """Paso 1: Datos básicos del caso (sirve para crear y editar)"""
    
    aplicar_css_panel()
    inicializar_caso()
    
    modo_editar = es_modo_editar()
    clave_editando = obtener_clave_caso_editando()
    
    identificador_medico = st.session_state.get('identificador', '')
    if not identificador_medico:
        st.error("No hay sesión activa de médico")
        return
    
    medico_data = obtener_medico_supabase(identificador_medico)
    if not medico_data:
        st.error("No se encontró el perfil del médico")
        return
    
    modulo_asignado = medico_data.get('modulo_asignado', 'No asignado')
    nombre_medico = st.session_state.get('nombre', 'Médico')
    
    # ===== CALCULAR ID AUTOMÁTICO =====
    if modulo_asignado not in CODIGO_ESPECIALIDAD:
        st.error(f"El área '{modulo_asignado}' no tiene código asignado.")
        return
    
    codigo = CODIGO_ESPECIALIDAD[modulo_asignado]
    
    caso_actual = obtener_caso()
    
    if modo_editar:
        id_caso = clave_editando
        if caso_actual.get('id_caso') != clave_editando:
            actualizar_caso('id_caso', clave_editando)
    else:
        if not caso_actual.get('id_caso'):
            siguiente_numero = obtener_siguiente_numero_caso(codigo)
            id_caso = f"{codigo}{siguiente_numero:04d}"
            actualizar_caso('id_caso', id_caso)
            actualizar_caso('especialidad', modulo_asignado)
            actualizar_caso('autor', nombre_medico)
            actualizar_caso('responsable', identificador_medico)
        else:
            id_caso = caso_actual.get('id_caso')
    
    # ===== BOTÓN CANCELAR =====
    col_cancelar, col_espacio = st.columns([1, 5])
    with col_cancelar:
        if st.button("← Cancelar", key="btn_cancelar_paso1", use_container_width=True):
            cancelar_creacion()
    
    # ===== HEADER =====
    titulo = "Editar Caso" if modo_editar else "Crear Caso Nuevo"
    st.markdown(f'<h1 class="medico-title">{titulo}</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-paso">
        <strong>Paso 1 de 5:</strong> Datos Básicos del Caso
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ===== FORMULARIO =====
    with st.form(key="form_paso_1"):
        st.markdown('<div class="section-title">Información General</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("ID del Caso", value=id_caso, disabled=True, key="paso1_id_caso")
        with col2:
            st.text_input("Área", value=modulo_asignado, disabled=True, key="paso1_estacion")
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Autor", value=nombre_medico, disabled=True, key="paso1_autor")
        with col2:
            st.text_input(
                "Nombre del Caso *",
                value=caso_actual.get('nombre_caso', ''),
                placeholder="Ej: Dolor torácico en adulto mayor",
                key="paso1_nombre_caso"
            )
        
        st.markdown("---")
        
        st.markdown('<div class="section-title">Tipo de Caso *</div>', unsafe_allow_html=True)
        
        tipo_caso_actual = caso_actual.get('tipo_caso', 'Paciente Virtual')
        index_tipo = TIPOS_CASO.index(tipo_caso_actual) if tipo_caso_actual in TIPOS_CASO else 0
        
        tipo_caso = st.radio(
            "Selecciona el tipo de caso:",
            options=TIPOS_CASO,
            index=index_tipo,
            key="paso1_tipo_caso",
            horizontal=True,
            help="Paciente Virtual: usa asistente IA | Paciente Estandarizado: actor humano | Estático: sin paciente"
        )
        
        st.markdown("---")
        
        col_btn1, col_btn2, col_btn3 = st.columns([3, 1, 1])
        with col_btn3:
            with st.container(key="btn_siguiente_crear_caso"):
                siguiente = st.form_submit_button("Siguiente →", use_container_width=True, type="primary")
        
        if siguiente:
            nombre_caso = st.session_state.get('paso1_nombre_caso', '').strip()
            
            if not nombre_caso:
                st.error("El nombre del caso es obligatorio")
            else:
                actualizar_caso('nombre_caso', nombre_caso)
                actualizar_caso('tipo_caso', tipo_caso)
                # Ahora el paso 2 será el de competencias/rúbricas
                ir_a_paso(2) 