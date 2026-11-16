# escenas/crear_caso/paso_3_general.py
import streamlit as st
from escenas.crear_caso.utils import (
    aplicar_css_panel, inicializar_caso, obtener_caso, actualizar_caso,
    obtener_sprite_segun_edad_sexo, obtener_sprites_disponibles,
    ir_a_paso, cancelar_creacion,
    es_modo_editar,
)


def mostrar():
    """Paso 3: Datos generales del paciente (sprite + información + guion)"""
    
    aplicar_css_panel()
    inicializar_caso()
    
    caso = obtener_caso()
    modo_editar = es_modo_editar()
    tipo_caso = caso.get('tipo_caso', 'Paciente Virtual')
    
    # ===== VERIFICAR QUE EL PASO 1 ESTÉ COMPLETO =====
    if not caso.get('nombre_caso'):
        st.warning("Debes completar el Paso 1 primero")
        if st.button("← Volver al Paso 1"):
            ir_a_paso(1)
        return
    
    # ===== BOTÓN CANCELAR (arriba izquierda) =====
    col_cancelar, col_espacio = st.columns([1, 5])
    with col_cancelar:
        if st.button("← Cancelar", key="btn_cancelar_paso3", use_container_width=True):
            cancelar_creacion()
    
    # ===== HEADER (dinámico según el modo) =====
    titulo = "Editar Caso" if modo_editar else "Crear Caso Nuevo"
    st.markdown(f'<h1 class="medico-title">{titulo}</h1>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="info-paso">
        <strong>Paso 3 de 5:</strong> Información General del Paciente<br>
        <small>Caso: {caso.get('id_caso', '')} - {caso.get('nombre_caso', '')}</small>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ===== SPRITE SELECTOR (FUERA DEL FORMULARIO) =====
    st.markdown('<div class="section-title">Imagen del Paciente</div>', unsafe_allow_html=True)
    
    if 'sprite_seleccionado' not in st.session_state:
        st.session_state.sprite_seleccionado = caso.get('sprite_url')
    if 'mostrar_selector_sprite' not in st.session_state:
        st.session_state.mostrar_selector_sprite = False
    
    col_sprite, col_visible_sprite, col_info = st.columns([1, 1, 2.5])
    
    with col_sprite:
        if st.session_state.sprite_seleccionado:
            try:
                st.image(st.session_state.sprite_seleccionado, width=120)
            except:
                st.info("🖼️")
        else:
            # Sprite por defecto según edad y sexo (o uno genérico)
            edad_actual = caso.get('edad', 18)
            sexo_actual = caso.get('sexo', 'Femenino')
            try:
                edad_int = int(edad_actual) if str(edad_actual).isdigit() else 18
            except:
                edad_int = 18
            ruta_sprite = obtener_sprite_segun_edad_sexo(edad_int, sexo_actual)
            try:
                st.image(ruta_sprite, width=120)
            except:
                st.info("🖼️")
    
    with col_visible_sprite:
        st.markdown("<br>", unsafe_allow_html=True)
        visible_sprite = st.checkbox(
            "Visible",
            value=caso.get('visible_sprite', True),
            key="paso3_visible_sprite"
        )
    
    with col_info:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.sprite_seleccionado:
            st.caption("Imagen personalizada seleccionada")
        else:
            st.caption("Imagen automática por defecto")
        
        if st.button("Seleccionar imagen", key="btn_seleccionar_sprite_paso3", use_container_width=True):
            st.session_state.mostrar_selector_sprite = True
            st.rerun()
    
    # Selector de sprites en popover
    if st.session_state.get('mostrar_selector_sprite', False):
        with st.popover("Abrir selector", use_container_width=True):
            mostrar_selector_sprite_paso3()
            if st.button("Cerrar selector", key="cerrar_selector_paso3", use_container_width=True):
                st.session_state.mostrar_selector_sprite = False
                st.rerun()
    
    st.markdown("---")
    
    # ===== FORMULARIO PRINCIPAL =====
    with st.form(key="form_paso_3"):
        st.markdown('<div class="section-title">Datos del Paciente</div>', unsafe_allow_html=True)
        
        # Nombre + Visible
        col1, col2 = st.columns([1, 1])
        with col1:
            nombre = st.text_input(
                "Nombre del Paciente *",
                value=caso.get('nombre', ''),
                placeholder="Ej: Juan Pérez",
                key="paso3_nombre"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            visible_nombre = st.checkbox(
                "Visible",
                value=caso.get('visible_nombre', True),
                key="paso3_visible_nombre"
            )
        
        # Edad + Visible | Sexo + Visible
        col1, col2, col3, col4 = st.columns([0.5, 0.3, 1, 0.5])
        with col1:
            edad = st.text_input(
                "Edad *",
                value=str(caso.get('edad', '')),
                placeholder="Ej: 25",
                key="paso3_edad"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            visible_edad = st.checkbox(
                "Visible",
                value=caso.get('visible_edad', True),
                key="paso3_visible_edad"
            )
        with col3:
            sexo = st.selectbox(
                "Sexo *",
                options=["Femenino", "Masculino", "Otro"],
                index=["Femenino", "Masculino", "Otro"].index(caso.get('sexo', 'Femenino')) if caso.get('sexo', 'Femenino') in ["Femenino", "Masculino", "Otro"] else 0,
                key="paso3_sexo"
            )
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            visible_sexo = st.checkbox(
                "Visible",
                value=caso.get('visible_sexo', True),
                key="paso3_visible_sexo"
            )
        
        # Motivo de consulta + Visible
        col1, col2 = st.columns([7, 1])
        with col1:
            motivo_consulta = st.text_area(
                "Motivo de Consulta *",
                value=caso.get('motivo_consulta', ''),
                height=70,
                key="paso3_motivo"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            visible_motivo = st.checkbox(
                "Visible",
                value=caso.get('visible_motivo', True),
                key="paso3_visible_motivo"
            )
        
        # Descripción + Visible
        col1, col2 = st.columns([7, 1])
        with col1:
            descripcion = st.text_area(
                "Descripción *",
                value=caso.get('descripcion', ''),
                height=100,
                key="paso3_descripcion"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            visible_descripcion = st.checkbox(
                "Visible",
                value=caso.get('visible_descripcion', True),
                key="paso3_visible_descripcion"
            )
        
        # Antecedentes + Visible 
        col1, col2 = st.columns([7, 1])
        with col1:
            antecedentes = st.text_area(
                "Antecedentes *",
                value=caso.get('antecedentes', ''),
                height=80,
                key="paso3_antecedentes"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            visible_antecedentes = st.checkbox(
                "Visible",
                value=caso.get('visible_antecedentes', True),
                key="paso3_visible_antecedentes"
            )
        
        # Medicamentos + Visible
        col1, col2 = st.columns([7, 1])
        with col1:
            medicamentos = st.text_area(
                "Medicamentos Actuales *",
                value=caso.get('medicamentos_actuales', ''),
                height=80,
                key="paso3_medicamentos"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            visible_medicamentos = st.checkbox(
                "Visible",
                value=caso.get('visible_medicamentos', True),
                key="paso3_visible_medicamentos"
            )
        
        st.markdown("---")
        
        # ===== GUION DEL PACIENTE (Solo si no es Estático) =====
        guion_paciente = ""
        
        if tipo_caso != "Estático":
            st.markdown('<div class="section-title">Guión del Paciente</div>', unsafe_allow_html=True)
            st.caption(f"El guión es necesario para el tipo de caso: **{tipo_caso}**.")
            
            guion_paciente = st.text_area(
                "Guión del paciente *",
                value=caso.get('guion_paciente', ''),
                height=150,
                placeholder="Escribe el guión que seguirá el paciente (o el contexto del caso). Puedes también incluir posibles preguntas y respuestas.",
                key="paso3_guion"
            )
            st.markdown("---")
        else:
            st.info("Este es un caso **Estático**, por lo que no requiere un guión de paciente.")
            guion_paciente = caso.get('guion_paciente', '') # Mantener por si acaso
            st.markdown("---")
        
        # ===== BOTONES =====
        col_btn1, col_btn2, col_btn3 = st.columns([3, 1, 1])
        with col_btn2:
            atras = st.form_submit_button("← Atrás", use_container_width=True)
        with col_btn3:
            with st.container(key="btn_siguiente_crear_caso"):
                siguiente = st.form_submit_button("Siguiente →", use_container_width=True, type="primary")
        
        if atras:
            # Guardar los datos actuales antes de salir
            _guardar_datos_paso3(
                st.session_state, nombre, edad, sexo, motivo_consulta, descripcion,
                antecedentes, medicamentos, guion_paciente,
                visible_sprite, visible_nombre, visible_edad, visible_sexo,
                visible_motivo, visible_descripcion, visible_antecedentes, visible_medicamentos
            )
            ir_a_paso(2) # Regresa a Competencias
        
        if siguiente:
            # Validar campos obligatorios
            errores = []
            if not nombre or not nombre.strip():
                errores.append("Nombre del Paciente")
            if not edad or not str(edad).strip():
                errores.append("Edad")
            if not str(edad).isdigit():
                errores.append("Edad debe ser un número")
            if not motivo_consulta or not motivo_consulta.strip():
                errores.append("Motivo de Consulta")
            if not descripcion or not descripcion.strip():
                errores.append("Descripción")
            if not antecedentes or not antecedentes.strip():
                errores.append("Antecedentes")
            if not medicamentos or not medicamentos.strip():
                errores.append("Medicamentos Actuales")
            
            # Validar guion solo si NO es estático
            if tipo_caso != "Estático":
                if not guion_paciente or not guion_paciente.strip():
                    errores.append("Guión del paciente")
            
            if errores:
                st.error(f"Faltan campos obligatorios: {', '.join(errores)}")
            else:
                # Guardar todos los datos
                _guardar_datos_paso3(
                    st.session_state, nombre, edad, sexo, motivo_consulta, descripcion,
                    antecedentes, medicamentos, guion_paciente,
                    visible_sprite, visible_nombre, visible_edad, visible_sexo,
                    visible_motivo, visible_descripcion, visible_antecedentes, visible_medicamentos
                )
                ir_a_paso(4) # Avanza a Estudios


def _guardar_datos_paso3(session_state, nombre, edad, sexo, motivo_consulta, descripcion,
                          antecedentes, medicamentos, guion_paciente,
                          visible_sprite, visible_nombre, visible_edad, visible_sexo,
                          visible_motivo, visible_descripcion, visible_antecedentes, visible_medicamentos):
    """Guarda todos los datos del paso 3 en session_state"""
    
    # Datos del paciente
    actualizar_caso('nombre', nombre.strip())
    actualizar_caso('edad', int(edad) if str(edad).isdigit() else 18)
    actualizar_caso('sexo', sexo)
    actualizar_caso('motivo_consulta', motivo_consulta.strip())
    actualizar_caso('descripcion', descripcion.strip())
    actualizar_caso('antecedentes', antecedentes.strip())
    actualizar_caso('medicamentos_actuales', medicamentos.strip())
    
    # Guion
    actualizar_caso('guion_paciente', guion_paciente.strip())
    
    # Visibilidad
    actualizar_caso('visible_sprite', visible_sprite)
    actualizar_caso('visible_nombre', visible_nombre)
    actualizar_caso('visible_edad', visible_edad)
    actualizar_caso('visible_sexo', visible_sexo)
    actualizar_caso('visible_motivo', visible_motivo)
    actualizar_caso('visible_descripcion', visible_descripcion)
    actualizar_caso('visible_antecedentes', visible_antecedentes)
    actualizar_caso('visible_medicamentos', visible_medicamentos)
    
    # Sprite
    if session_state.get('sprite_seleccionado'):
        actualizar_caso('sprite_url', session_state.sprite_seleccionado)


def mostrar_selector_sprite_paso3():
    """Muestra un selector de sprites dentro del flujo de crear caso"""
    sprites = obtener_sprites_disponibles()
    
    st.markdown("### Selecciona la imagen del paciente")
    st.caption("Elige el sprite que mejor represente al paciente")
    
    cols = st.columns(4)
    
    for idx, sprite in enumerate(sprites):
        col_idx = idx % 4
        with cols[col_idx]:
            try:
                st.image(sprite['url'], width=80)
            except:
                st.write("🖼️")
            
            if st.button("Seleccionar", key=f"sprite_sel_paso3_{idx}"):
                st.session_state.sprite_seleccionado = sprite['url']
                st.success("Imagen seleccionada")
                st.rerun()
            
            if st.session_state.get('sprite_seleccionado') == sprite['url']:
                st.markdown("Seleccionado")