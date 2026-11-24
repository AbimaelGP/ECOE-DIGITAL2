# escenas/crear_caso/paso_3_estudios.py
import streamlit as st
from escenas.crear_caso.utils import (
    aplicar_css_panel, inicializar_caso, obtener_caso, actualizar_caso,
    ir_a_paso, cancelar_creacion,
    es_modo_editar,
    UNIDADES_DISPONIBLES,
    subir_imagen_caso,
    eliminar_imagen_caso,
    validar_nombre_estudio_unico,
    crear_estudio_vacio_imagen,
    crear_estudio_vacio_parametros,
)


LIMITE_ESTUDIOS = 4


# ==================== SESSION STATE AUXILIAR ====================

def _inicializar_estado_modal():
    if 'paso3_mostrar_modal' not in st.session_state:
        st.session_state.paso3_mostrar_modal = None
    if 'paso3_estudio_en_edicion' not in st.session_state:
        st.session_state.paso3_estudio_en_edicion = None
    if 'modal_parametros_temp' not in st.session_state:
        st.session_state.modal_parametros_temp = None
    if 'param_counter' not in st.session_state:
        st.session_state.param_counter = 0


def _cerrar_modal():
    st.session_state.paso3_mostrar_modal = None
    st.session_state.paso3_estudio_en_edicion = None
    st.session_state.modal_parametros_temp = None


# ==================== FUNCIÓN PRINCIPAL ====================

def mostrar():
    """Paso 3: Construcción de estudios personalizados"""
    
    aplicar_css_panel()
    inicializar_caso()
    _inicializar_estado_modal()
    
    caso = obtener_caso()
    modo_editar = es_modo_editar()
    
    # ===== VERIFICAR QUE EL PASO 2 ESTÉ COMPLETO =====
    if not caso.get('nombre') or not caso.get('edad'):
        st.warning("Debes completar el Paso 2 primero")
        if st.button("Volver al Paso 2"):
            ir_a_paso(2)
        return
    
    # ===== BOTÓN CANCELAR =====
    col_cancelar, col_espacio = st.columns([1, 5])
    with col_cancelar:
        if st.button("Cancelar", key="btn_cancelar_paso3", use_container_width=True):
            cancelar_creacion()
    
    # ===== HEADER =====
    titulo = "Editar Caso" if modo_editar else "Crear Caso Nuevo"
    st.markdown(f'<h1 class="medico-title">{titulo}</h1>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="info-paso">
        <strong>Paso 3 de 4:</strong> Estudios del Caso<br>
        <small>Caso: {caso.get('id_caso', '')} - {caso.get('nombre_caso', '')}</small>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ===== INICIALIZAR ESTRUCTURA =====
    if 'estudios_incluidos' not in caso or caso['estudios_incluidos'] is None:
        actualizar_caso('estudios_incluidos', [])
        caso['estudios_incluidos'] = []
    
    if 'valores_estudios' not in caso or caso['valores_estudios'] is None:
        actualizar_caso('valores_estudios', {})
        caso['valores_estudios'] = {}
    
    estudios_actuales = caso.get('valores_estudios', {})
    total_estudios = len(estudios_actuales)
    
    # ===== INFO =====
    st.markdown(f"""
    <div class="info-paso">
        <strong>Información:</strong> Crea los estudios que formarán parte de este caso. 
        Puedes añadir hasta {LIMITE_ESTUDIOS} estudios. Estudios actuales: <strong>{total_estudios}/{LIMITE_ESTUDIOS}</strong>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== BOTONES DE AÑADIR =====
    st.markdown('<div class="section-title">Añadir Estudio</div>', unsafe_allow_html=True)
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    with col_btn1:
        if st.button("+ Añadir Estudio de Imagen", key="btn_add_imagen", use_container_width=True, disabled=(total_estudios >= LIMITE_ESTUDIOS)):
            st.session_state.paso3_mostrar_modal = "imagen"
            st.session_state.paso3_estudio_en_edicion = None
            st.session_state.modal_parametros_temp = None
            st.rerun()
    
    with col_btn2:
        if st.button("+ Añadir Estudio de Valores", key="btn_add_parametros", use_container_width=True, disabled=(total_estudios >= LIMITE_ESTUDIOS)):
            st.session_state.paso3_mostrar_modal = "parametros"
            st.session_state.paso3_estudio_en_edicion = None
            st.session_state.modal_parametros_temp = None
            st.rerun()
    
    if total_estudios >= LIMITE_ESTUDIOS:
        st.warning(f"Has alcanzado el límite de {LIMITE_ESTUDIOS} estudios. Elimina uno para añadir más.")
    
    st.markdown("---")
    
    # ===== MODAL DE CREAR/EDITAR ESTUDIO =====
    if st.session_state.paso3_mostrar_modal == "imagen":
        _renderizar_modal_estudio_imagen(caso)
    elif st.session_state.paso3_mostrar_modal == "parametros":
        _renderizar_modal_estudio_parametros(caso)
    
    # ===== LISTA DE ESTUDIOS ACTUALES =====
    st.markdown('<div class="section-title">Estudios del Caso</div>', unsafe_allow_html=True)
    
    if not estudios_actuales:
        st.info("Aún no has añadido ningún estudio. Usa los botones de arriba para crear uno.")
    else:
        for nombre_estudio, datos_estudio in list(estudios_actuales.items()):
            _renderizar_tarjeta_estudio(nombre_estudio, datos_estudio, caso)
    
    # ===== BOTONES NAVEGACIÓN =====
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([3, 1, 1])
    with col_btn2:
        if st.button("Atrás", key="btn_atras_paso3", use_container_width=True):
            ir_a_paso(3)
    with col_btn3:
        with st.container(key="btn_siguiente_crear_caso"):
            if st.button("Siguiente", key="btn_siguiente_paso3", use_container_width=True, type="primary"):
                ir_a_paso(5)


# ==================== TARJETAS DE ESTUDIOS ====================

def _renderizar_tarjeta_estudio(nombre_estudio, datos_estudio, caso):
    """Renderiza una tarjeta con la info del estudio"""
    
    es_imagen = datos_estudio.get('tipo') == 'imagen'
    imagen_url = datos_estudio.get('imagen_url')
    parametros = datos_estudio.get('parametros', {})
    
    with st.container(border=True):
        col_titulo, col_editar, col_eliminar = st.columns([5, 1, 1])
        
        with col_titulo:
            tipo_texto = "Imagen" if es_imagen else f"{len(parametros)} valores"
            st.markdown(f"**{nombre_estudio}**")
        
        with col_editar:
            if st.button("Editar", key=f"btn_editar_estudio_{nombre_estudio}", use_container_width=True):
                st.session_state.paso3_mostrar_modal = datos_estudio.get('tipo', 'parametros')
                st.session_state.paso3_estudio_en_edicion = nombre_estudio
                # Para parámetros, precargar los datos
                if datos_estudio.get('tipo') == 'parametros':
                    st.session_state.modal_parametros_temp = None  # Se cargará en el modal
                st.rerun()
        
        with col_eliminar:
            if st.button("Eliminar", key=f"btn_eliminar_estudio_{nombre_estudio}", use_container_width=True):
                _eliminar_estudio(nombre_estudio)
        
        # Preview
        if es_imagen:
            if imagen_url:
                try:
                    st.image(imagen_url, width=200)
                except:
                    st.caption("Imagen no disponible")
            else:
                st.caption("⚠️ Sin imagen. Edita el estudio para subir una.")
        else:
            if parametros:
                for param, datos_p in parametros.items():
                    st.caption(f"• {param}: {datos_p.get('valor', '')} {datos_p.get('unidad', '')}")


def _eliminar_estudio(nombre_estudio):
    """Elimina un estudio del caso"""
    caso = obtener_caso()
    valores = caso.get('valores_estudios', {})
    
    if nombre_estudio in valores:
        del valores[nombre_estudio]
        actualizar_caso('valores_estudios', valores)
        
        incluidos = caso.get('estudios_incluidos', [])
        if nombre_estudio in incluidos:
            incluidos.remove(nombre_estudio)
            actualizar_caso('estudios_incluidos', incluidos)
        
        st.success(f"Estudio '{nombre_estudio}' eliminado")
        st.rerun()


# ==================== MODAL: ESTUDIO DE IMAGEN ====================

def _renderizar_modal_estudio_imagen(caso):
    """Modal para crear/editar un estudio de imagen"""
    
    nombre_original = st.session_state.paso3_estudio_en_edicion
    editando = nombre_original is not None
    estudios_actuales = caso.get('valores_estudios', {})
    clave_caso = caso.get('id_caso', '')
    identificador_medico = caso.get('responsable', '')
    
    with st.container(border=True):
        st.markdown(f"### {'Editar' if editando else 'Nuevo'} Estudio de Imagen")
        
        nombre_estudio = st.text_input(
            "Nombre del estudio *",
            value=nombre_original if editando else "",
            placeholder="Ej: Rayos X de Tórax",
            key="modal_imagen_nombre"
        )
        
        # Preview de imagen actual
        if editando and nombre_original in estudios_actuales:
            img_url = estudios_actuales[nombre_original].get('imagen_url')
            if img_url:
                try:
                    st.image(img_url, width=200, caption="Imagen actual")
                except:
                    pass
        
        archivo_subido = st.file_uploader(
            "Subir imagen *",
            type=['png', 'jpg', 'jpeg'],
            key="modal_imagen_uploader"
        )
        
        if archivo_subido:
            st.caption(f"📎 Archivo seleccionado: {archivo_subido.name}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cancelar", key="btn_cancelar_modal_imagen", use_container_width=True):
                _cerrar_modal()
                st.rerun()
        with col2:
            if st.button("Guardar estudio", key="btn_guardar_modal_imagen", use_container_width=True, type="primary"):
                _guardar_estudio_imagen(nombre_estudio, nombre_original, archivo_subido, caso)


def _guardar_estudio_imagen(nombre_estudio, nombre_original, archivo_subido, caso):
    """Guarda (crea o edita) un estudio de imagen (maneja renombrado y actualización de imagen)"""
    
    nombre_estudio = nombre_estudio.strip()
    
    if not nombre_estudio:
        st.error("El nombre del estudio es obligatorio")
        return
    
    estudios_actuales = caso.get('valores_estudios', {})
    
    if not validar_nombre_estudio_unico(nombre_estudio, estudios_actuales, nombre_original):
        st.error(f"Ya existe un estudio con el nombre '{nombre_estudio}'")
        return
    
    clave_caso = caso.get('id_caso', '')
    identificador_medico = caso.get('responsable', '')
    
    # ===== DETECTAR CAMBIOS =====
    editando = nombre_original is not None and nombre_original in estudios_actuales
    renombrado = editando and (nombre_original != nombre_estudio)
    nueva_imagen = archivo_subido is not None
    
    # ===== CASO 1: NUEVO ESTUDIO =====
    if not editando:
        datos = crear_estudio_vacio_imagen(nombre_estudio)
        
        if not archivo_subido:
            st.error("Debes subir una imagen para el nuevo estudio")
            return
        
        with st.spinner("Subiendo imagen..."):
            url = subir_imagen_caso(archivo_subido, clave_caso, identificador_medico, nombre_estudio)
        
        if url:
            datos['imagen_url'] = url
        else:
            st.error("Error al subir la imagen")
            return
    
    # ===== CASO 2: EDITANDO ESTUDIO EXISTENTE =====
    else:
        datos_viejos = estudios_actuales[nombre_original]
        datos = datos_viejos.copy()
        datos['tipo'] = 'imagen'
        datos.setdefault('parametros', {})
        
        url_imagen_vieja = datos_viejos.get('imagen_url')
        
        # ---- Subcaso 2a: Renombrado + imagen nueva ----
        if renombrado and nueva_imagen:
            # 1. Eliminar imagen vieja de Storage
            if url_imagen_vieja:
                with st.spinner("Eliminando imagen anterior..."):
                    eliminar_imagen_caso(clave_caso, identificador_medico, nombre_original)
            
            # 2. Subir nueva imagen con nombre nuevo
            with st.spinner("Subiendo nueva imagen..."):
                url = subir_imagen_caso(archivo_subido, clave_caso, identificador_medico, nombre_estudio)
            
            if url:
                datos['imagen_url'] = url
            else:
                st.error("Error al subir la nueva imagen")
                return
        
        # ---- Subcaso 2b: Solo renombrado (sin imagen nueva) ----
        elif renombrado and not nueva_imagen:
            if url_imagen_vieja:
                # Copiar la imagen al nuevo nombre (descargar + subir)
                with st.spinner("Actualizando nombre de imagen..."):
                    # Descargar la imagen actual
                    try:
                        from utils.imagenes import ruta_desde_url
                        nombre_viejo_limpio = nombre_original.replace(' ', '_').replace('/', '_').replace('\\', '_')
                        ruta_vieja = ruta_desde_url(url_imagen_vieja) or \
                            f"{clave_caso}/imagenes/{clave_caso}_{identificador_medico}_{nombre_viejo_limpio}.png"
                        extension = ruta_vieja.rsplit('.', 1)[-1].lower()
                        content_type = "image/jpeg" if extension in ("jpg", "jpeg") else f"image/{extension}"
                        
                        # Descargar bytes
                        archivo_bytes = supabase.storage.from_("casos_clinicos").download(ruta_vieja)
                        
                        # Subir con el nuevo nombre (mismo formato que la imagen original)
                        nombre_nuevo_limpio = nombre_estudio.replace(' ', '_').replace('/', '_').replace('\\', '_')
                        ruta_nueva = f"{clave_caso}/imagenes/{clave_caso}_{identificador_medico}_{nombre_nuevo_limpio}.{extension}"
                        
                        supabase.storage.from_("casos_clinicos").upload(
                            path=ruta_nueva,
                            file=archivo_bytes,
                            file_options={"content-type": content_type}
                        )
                        
                        # Eliminar la vieja
                        supabase.storage.from_("casos_clinicos").remove([ruta_vieja])
                        
                        # Actualizar URL
                        url_nueva = supabase.storage.from_("casos_clinicos").get_public_url(ruta_nueva)
                        datos['imagen_url'] = url_nueva
                        
                        print(f"✅ Imagen renombrada: {nombre_original} → {nombre_estudio}")
                        
                    except Exception as e:
                        print(f"⚠️ Error al renombrar imagen: {e}")
                        st.warning("No se pudo renombrar la imagen, pero el estudio se actualizará")
        
        # ---- Subcaso 2c: Solo imagen nueva (sin renombrar) ----
        elif not renombrado and nueva_imagen:
            # Sobreescribir la imagen existente (mismo nombre)
            with st.spinner("Actualizando imagen..."):
                url = subir_imagen_caso(archivo_subido, clave_caso, identificador_medico, nombre_estudio)
            
            if url:
                datos['imagen_url'] = url
            else:
                st.error("Error al actualizar la imagen")
                return
        
        # ---- Subcaso 2d: Solo cambió el nombre, sin imagen ni nada ----
        # (no hacer nada, mantener los datos actuales)
    
    # ===== ACTUALIZAR EL DICCIONARIO =====
    if renombrado and nombre_original in estudios_actuales:
        del estudios_actuales[nombre_original]
        
        incluidos = caso.get('estudios_incluidos', [])
        if nombre_original in incluidos:
            incluidos.remove(nombre_original)
            if nombre_estudio not in incluidos:
                incluidos.append(nombre_estudio)
            actualizar_caso('estudios_incluidos', incluidos)
    
    estudios_actuales[nombre_estudio] = datos
    
    incluidos = caso.get('estudios_incluidos', [])
    if nombre_estudio not in incluidos:
        incluidos.append(nombre_estudio)
        actualizar_caso('estudios_incluidos', incluidos)
    
    actualizar_caso('valores_estudios', estudios_actuales)
    _cerrar_modal()
    st.success(f"Estudio '{nombre_estudio}' guardado")
    st.rerun()


# ==================== MODAL: ESTUDIO DE PARÁMETROS ====================

def _renderizar_modal_estudio_parametros(caso):
    """Modal para crear/editar un estudio de valores"""
    
    nombre_original = st.session_state.paso3_estudio_en_edicion
    editando = nombre_original is not None
    estudios_actuales = caso.get('valores_estudios', {})
    
    # Inicializar parámetros temporales
    if st.session_state.modal_parametros_temp is None:
        if editando and nombre_original in estudios_actuales:
            # Cargar parámetros existentes (convertir a formato con IDs)
            params_existentes = estudios_actuales[nombre_original].get('parametros', {})
            st.session_state.modal_parametros_temp = {}
            for i, (nombre_p, datos_p) in enumerate(params_existentes.items()):
                param_id = f"param_edit_{i}"
                st.session_state.modal_parametros_temp[param_id] = {
                    "nombre": nombre_p,
                    "valor": datos_p.get('valor', ''),
                    "unidad": datos_p.get('unidad', '')
                }
            if not st.session_state.modal_parametros_temp:
                # Si no había ninguno, empezar con 1 vacío
                st.session_state.modal_parametros_temp = {"param_0": {"nombre": "", "valor": "", "unidad": ""}}
        else:
            st.session_state.modal_parametros_temp = {"param_0": {"nombre": "", "valor": "", "unidad": ""}}
    
    with st.container(border=True):
        st.markdown(f"### {'Editar' if editando else 'Nuevo'} Estudio de Valores")
        
        nombre_estudio = st.text_input(
            "Nombre del estudio *",
            value=nombre_original if editando else "",
            placeholder="Ej: Biometría Hemática",
            key="modal_parametros_nombre"
        )
        
        st.markdown("---")
        st.markdown("**Valores del estudio**")
        
        parametros_temp = st.session_state.modal_parametros_temp
        ids_a_eliminar = []
        
        # Encabezados
        col_h1, col_h2, col_h3, col_h4 = st.columns([3, 2, 2, 1])
        with col_h1:
            st.caption("**Nombre**")
        with col_h2:
            st.caption("**Magnitud**")
        with col_h3:
            st.caption("**Unidad**")
        with col_h4:
            st.caption("**X**")
        
        for param_id in list(parametros_temp.keys()):
            datos = parametros_temp[param_id]
            col_nombre, col_valor, col_unidad, col_eliminar = st.columns([3, 2, 2, 1])
            
            with col_nombre:
                datos['nombre'] = st.text_input(
                    "Nombre",
                    value=datos.get('nombre', ''),
                    key=f"param_nombre_{param_id}",
                    label_visibility="collapsed",
                    placeholder="Ej: Hemoglobina"
                )
            with col_valor:
                datos['valor'] = st.text_input(
                    "Magnitud",
                    value=datos.get('valor', ''),
                    key=f"param_valor_{param_id}",
                    label_visibility="collapsed",
                    placeholder="Ej: 14.5"
                )
            with col_unidad:
                unidad_actual = datos.get('unidad', '')
                idx_unidad = UNIDADES_DISPONIBLES.index(unidad_actual) if unidad_actual in UNIDADES_DISPONIBLES else 0
                datos['unidad'] = st.selectbox(
                    "Unidad",
                    options=UNIDADES_DISPONIBLES,
                    index=idx_unidad,
                    key=f"param_unidad_{param_id}",
                    label_visibility="collapsed"
                )
            with col_eliminar:
                if len(parametros_temp) > 1:
                    if st.button("🗑️", key=f"param_eliminar_{param_id}", use_container_width=True):
                        ids_a_eliminar.append(param_id)
        
        # Eliminar los marcados
        if ids_a_eliminar:
            for pid in ids_a_eliminar:
                del parametros_temp[pid]
            st.rerun()
        
        # Botón + para añadir más
        if len(parametros_temp) < 20:
            if st.button("+ Añadir valor", key="btn_add_parametro", use_container_width=True):
                st.session_state.param_counter += 1
                nuevo_id = f"param_{st.session_state.param_counter}"
                parametros_temp[nuevo_id] = {"nombre": "", "valor": "", "unidad": ""}
                st.rerun()
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cancelar", key="btn_cancelar_modal_parametros", use_container_width=True):
                _cerrar_modal()
                st.rerun()
        with col2:
            if st.button("Guardar estudio", key="btn_guardar_modal_parametros", use_container_width=True, type="primary"):
                _guardar_estudio_parametros(nombre_estudio, nombre_original, parametros_temp, caso)


def _guardar_estudio_parametros(nombre_estudio, nombre_original, parametros_temp, caso):
    """Guarda (crea o edita) un estudio de parámetros"""
    
    nombre_estudio = nombre_estudio.strip()
    
    if not nombre_estudio:
        st.error("El nombre del estudio es obligatorio")
        return
    
    # Construir parámetros válidos
    parametros_validos = {}
    for param_id, datos in parametros_temp.items():
        nombre_param = datos.get('nombre', '').strip()
        if not nombre_param:
            continue
        
        if nombre_param in parametros_validos:
            st.error(f"El valor '{nombre_param}' está duplicado")
            return
        
        parametros_validos[nombre_param] = {
            "valor": datos.get('valor', '').strip(),
            "unidad": datos.get('unidad', '')
        }
    
    if not parametros_validos:
        st.error("Debes añadir al menos 1 valor con nombre")
        return
    
    estudios_actuales = caso.get('valores_estudios', {})
    
    if not validar_nombre_estudio_unico(nombre_estudio, estudios_actuales, nombre_original):
        st.error(f"Ya existe un estudio con el nombre '{nombre_estudio}'")
        return
    
    nuevo_estudio = {
        "tipo": "parametros",
        "imagen_url": None,
        "parametros": parametros_validos
    }
    
    if nombre_original and nombre_original != nombre_estudio and nombre_original in estudios_actuales:
        del estudios_actuales[nombre_original]
        
        incluidos = caso.get('estudios_incluidos', [])
        if nombre_original in incluidos:
            incluidos.remove(nombre_original)
            if nombre_estudio not in incluidos:
                incluidos.append(nombre_estudio)
            actualizar_caso('estudios_incluidos', incluidos)
    
    estudios_actuales[nombre_estudio] = nuevo_estudio
    
    incluidos = caso.get('estudios_incluidos', [])
    if nombre_estudio not in incluidos:
        incluidos.append(nombre_estudio)
        actualizar_caso('estudios_incluidos', incluidos)
    
    actualizar_caso('valores_estudios', estudios_actuales)
    _cerrar_modal()
    st.success(f"Estudio '{nombre_estudio}' guardado")
    st.rerun()