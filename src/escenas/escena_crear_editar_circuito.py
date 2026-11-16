# escenas/escena_crear_editar_circuito.py
import streamlit as st
from utils.supabase_client import supabase
from components.modal_historial import _renderizar_contenido_historial
from utils.casos import cargar_info_caso

# ==================== FUNCIONES DE SUPABASE ====================

def obtener_casos_disponibles():
    if not supabase: return []
    try:
        response = supabase.table("casos_clinicos").select("clave_caso, especialidad, data").execute()
        casos = []
        for caso in response.data:
            data = caso.get('data', {})
            casos.append({
                "clave_caso": caso.get('clave_caso', ''),
                "especialidad": caso.get('especialidad', ''),
                "titulo": data.get('nombre_caso', caso.get('clave_caso', ''))
            })
        return casos
    except Exception as e:
        print(f"Error al obtener casos: {e}")
        return []

def crear_circuito_supabase(datos):
    if not supabase: return False, "Supabase no conectado"
    try:
        datos_completos = {
            "nombre": datos.get("nombre", ""),
            "creado_por": datos.get("creado_por", ""),
            "activo": True
        }
        for i in range(1, 7):
            datos_completos[f"modulo_{i}"] = datos.get(f"modulo_{i}", "")
            datos_completos[f"caso_{i}"] = datos.get(f"caso_{i}", "")
        
        supabase.table("circuitos").insert(datos_completos).execute()
        return True, "Circuito creado exitosamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def actualizar_circuito_supabase(circuito_id, datos):
    if not supabase: return False, "Supabase no conectado"
    try:
        datos_actualizados = {"nombre": datos.get("nombre", ""), "creado_por": datos.get("creado_por", "")}
        for i in range(1, 7):
            datos_actualizados[f"modulo_{i}"] = datos.get(f"modulo_{i}", "")
            datos_actualizados[f"caso_{i}"] = datos.get(f"caso_{i}", "")
        
        supabase.table("circuitos").update(datos_actualizados).eq("id", circuito_id).execute()
        return True, "Circuito actualizado exitosamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def mostrar_previsualizacion_caso(clave_caso):
    if not supabase or not clave_caso: return
    try:
        response = supabase.table("casos_clinicos").select("*").eq("clave_caso", clave_caso).execute()
        if response.data and len(response.data) > 0:
            caso = response.data[0]
            data_paciente = caso.get('data', {})
            
            st.markdown("""
            <div style="background-color: #FFFFFF; border-radius: 8px; padding: 1rem; margin-top: 0.5rem; border-left: 4px solid #70257E; color: #303442;">
                <p style="margin: 0; font-weight: 600; color: #252A38;">Previsualizacion del caso</p>
                <p style="margin: 0.25rem 0; font-size: 14px;"><strong>Clave:</strong> {clave}</p>
                <p style="margin: 0.25rem 0; font-size: 14px;"><strong>Paciente:</strong> {nombre}</p>
                <p style="margin: 0.25rem 0; font-size: 14px;"><strong>Edad:</strong> {edad} años</p>
                <p style="margin: 0.25rem 0; font-size: 14px;"><strong>Sexo:</strong> {sexo}</p>
                <p style="margin: 0.25rem 0; font-size: 14px;"><strong>Motivo:</strong> {motivo}</p>
            </div>
            """.format(
                clave=caso.get('clave_caso', 'N/A'),
                nombre=data_paciente.get('nombre', 'No disponible'),
                edad=data_paciente.get('edad', 'N/A'),
                sexo=data_paciente.get('sexo', 'N/A'),
                motivo=data_paciente.get('motivo_consulta', 'No disponible')
            ), unsafe_allow_html=True)
    except Exception as e:
        st.warning("No se pudo cargar la previsualizacion del caso")

# ==================== MODAL NATIVO PARA VER CASO ====================

@st.dialog("Detalles del Caso", width="large")
def _modal_ver_caso_admin(clave_caso):
    """Modal directo para ver el caso (sin usar botones de otros componentes)"""
    
    # Ocultar la X de cerrar nativa
    st.markdown("""
    <style>
        div[data-testid="stDialog"] button[aria-label="Close"] {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    info_caso = cargar_info_caso(clave_caso)
    
    if info_caso:
        _renderizar_contenido_historial(
            info_caso, 
            clave_caso, 
            incluir_clave=True, 
            modo_admin=True
        )
    else:
        st.warning(f"No se pudo cargar la información del caso {clave_caso}")
    
    # Botón para cerrar el modal
    if st.button("Cerrar", key=f"cerrar_modal_ver_caso_{clave_caso}", use_container_width=True):
        st.session_state['caso_para_modal'] = None
        st.rerun()

# ==================== RENDERIZADO PRINCIPAL ====================

def mostrar():
    # CSS
    st.markdown("""
    <style>
        .stExpander { background-color: #FFFFFF !important; border-radius: 8px !important; border: 1px solid #E5E7EC !important; margin-bottom: 0.5rem !important; }
        .stExpander > div { background-color: #FFFFFF !important; }
        .stSelectbox > div > div { background-color: #FFFFFF !important; }
        .stSelectbox select { background-color: #FFFFFF !important; }
        
        .section-title { color: #252A38; font-family: 'Poppins'; font-size: 24px; font-weight: 600; margin-top: 1.5rem; margin-bottom: 1rem; border-left: 4px solid #70257E; padding-left: 1rem; }
        .card-title { color: #252A38; font-family: 'Poppins'; font-size: 18px; font-weight: 600; margin-bottom: 1rem; }
        
        .area-titulo { color: #70257E !important; font-weight: 600 !important; font-size: 16px !important; margin-bottom: 0 !important; }
    </style>
    """, unsafe_allow_html=True)

    circuito = st.session_state.get('editando_circuito', None)
    modo = "editar" if circuito else "crear"

    # Botón para regresar
    if st.button("← Volver al Panel", key="btn_volver_circuitos"):
        st.session_state['mostrar_formulario_circuito'] = False
        st.session_state['editando_circuito'] = None
        for i in range(1, 7):
            for k in [f'preview_caso_{i}', f'caso_seleccionado_clave_{i}', f'mostrar_casos_mod_{i}', f'ultima_especialidad_{i}', f'esp_mod_{i}', f'caso_mod_{i}']:
                if k in st.session_state: del st.session_state[k]
        if 'caso_para_modal' in st.session_state: del st.session_state['caso_para_modal']
        st.session_state['pagina'] = 'admin'
        st.rerun()

    if modo == "crear":
        st.markdown('<div class="section-title">Crear Nuevo Circuito</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="section-title">Editar Circuito: {circuito.get("nombre", "")}</div>', unsafe_allow_html=True)

    especialidades_disponibles = ["No asignar", "Medicina Familiar", "Medicina Interna", "Pediatría", "Ginecología y Obstetricia", "Cirugía", "Urgencias"]
    todos_los_casos = obtener_casos_disponibles()
    casos_por_especialidad = {}
    
    for caso in todos_los_casos:
        especialidad = caso.get('especialidad', '')
        if especialidad:
            if especialidad not in casos_por_especialidad:
                casos_por_especialidad[especialidad] = []
            casos_por_especialidad[especialidad].append(caso)
    
    if 'nombre_circuito_actual' not in st.session_state:
        st.session_state['nombre_circuito_actual'] = circuito.get("nombre", "") if circuito else ""

    st.text_input("Nombre del Circuito *", key="nombre_circuito_actual")
    st.markdown("---")
    st.markdown("### Configuración de Áreas")
    st.caption("Selecciona la especialidad y el caso para cada área del circuito")
    
    for i in range(1, 7):
        key_exp = f'mostrar_casos_mod_{i}'
        if key_exp not in st.session_state:
            if modo == "editar" and circuito:
                especialidad_actual = circuito.get(f"modulo_{i}", "")
                if especialidad_actual and especialidad_actual != "No asignar":
                    st.session_state[key_exp] = especialidad_actual
                else: st.session_state[key_exp] = ""
            else: st.session_state[key_exp] = ""
        
        with st.expander(f"Área {i}", expanded=False):
            st.markdown(f'<p class="area-titulo">Configurando Área {i}</p>', unsafe_allow_html=True)
            
            especialidad_actual = circuito.get(f"modulo_{i}", "") if circuito else ""
            caso_actual = circuito.get(f"caso_{i}", "") if circuito else ""
            try:
                index_actual = especialidades_disponibles.index(especialidad_actual) if especialidad_actual in especialidades_disponibles else 0
            except ValueError: index_actual = 0
            
            especialidad_seleccionada = st.selectbox("Especialidad", options=especialidades_disponibles, index=index_actual, key=f"esp_mod_{i}")
            
            if especialidad_seleccionada != st.session_state.get(f'ultima_especialidad_{i}', ''):
                st.session_state[f'mostrar_casos_mod_{i}'] = ""
                st.session_state[f'ultima_especialidad_{i}'] = especialidad_seleccionada
            
            col_btn_ver, col_espacio = st.columns([1, 3])
            with col_btn_ver:
                if st.button("Ver casos", key=f"ver_casos_btn_{i}"):
                    st.session_state[f'mostrar_casos_mod_{i}'] = especialidad_seleccionada
                    st.rerun()
            
            if modo == "editar" and circuito:
                especialidad_guardada = circuito.get(f"modulo_{i}", "")
                if especialidad_guardada and especialidad_guardada != "No asignar":
                    if st.session_state.get(f'mostrar_casos_mod_{i}', '') == "":
                        st.session_state[f'mostrar_casos_mod_{i}'] = especialidad_guardada
            
            if especialidad_seleccionada == "No asignar":
                st.caption("Este área no será utilizada en el circuito")
                st.session_state[f'caso_seleccionado_clave_{i}'] = ""
            else:
                casos_filtrados = casos_por_especialidad.get(especialidad_seleccionada, [])
                if casos_filtrados and st.session_state.get(f'mostrar_casos_mod_{i}', '') == especialidad_seleccionada:
                    opciones_casos = [{"clave": "", "label": "Seleccionar caso"}]
                    for caso in casos_filtrados:
                        opciones_casos.append({"clave": caso['clave_caso'], "label": f"{caso['clave_caso']} - {caso.get('titulo', caso['clave_caso'])}"})
                    
                    caso_index = 0
                    for idx, opt in enumerate(opciones_casos):
                        if opt["clave"] == caso_actual: caso_index = idx; break
                    
                    caso_seleccionado = st.selectbox("Caso", options=opciones_casos, index=caso_index, format_func=lambda x: x["label"], key=f"caso_mod_{i}")
                    
                    if caso_seleccionado and caso_seleccionado["clave"]:
                        st.session_state[f'caso_seleccionado_clave_{i}'] = caso_seleccionado["clave"]
                    else: st.session_state[f'caso_seleccionado_clave_{i}'] = ""
                    
                    if caso_seleccionado and caso_seleccionado["clave"]:
                        # Botón que llena el session_state con la clave
                        if st.button("Ver caso completo", key=f"btn_abrir_modal_{i}"):
                            st.session_state['caso_para_modal'] = caso_seleccionado["clave"]
                            st.rerun()
                        
                        if st.session_state.get(f'preview_caso_{i}', '') == caso_seleccionado["clave"]:
                            st.markdown("---")
                            mostrar_previsualizacion_caso(caso_seleccionado["clave"])
                            if st.button("Cerrar", key=f"cerrar_preview_btn_{i}"):
                                st.session_state[f'preview_caso_{i}'] = ''
                                st.rerun()
                elif casos_filtrados:
                    st.caption(f"Presiona 'Ver casos' para mostrar los casos de {especialidad_seleccionada}")
                    st.session_state[f'caso_seleccionado_clave_{i}'] = ""
                else:
                    st.caption("No hay casos disponibles para esta especialidad")
                    st.session_state[f'caso_seleccionado_clave_{i}'] = ""
    
    st.markdown("---")
    
    # ===== BOTONES FINALES =====
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Cancelar", key="btn_cancelar_circuito", use_container_width=True):
            st.session_state['mostrar_formulario_circuito'] = False
            st.session_state['editando_circuito'] = None
            for i in range(1, 7):
                for k in [f'preview_caso_{i}', f'caso_seleccionado_clave_{i}', f'mostrar_casos_mod_{i}', f'ultima_especialidad_{i}', f'esp_mod_{i}', f'caso_mod_{i}']:
                    if k in st.session_state: del st.session_state[k]
            if 'nombre_circuito_actual' in st.session_state: del st.session_state['nombre_circuito_actual']
            if 'caso_para_modal' in st.session_state: del st.session_state['caso_para_modal']
            st.session_state['pagina'] = 'admin'
            st.rerun()
            
    with col_btn2:
        if st.button("Guardar Circuito", key="btn_guardar_circuito", use_container_width=True, type="primary"):
            nombre = st.session_state.get('nombre_circuito_actual', '')
            if not nombre.strip(): 
                st.error("El nombre del circuito es obligatorio")
            else:
                creado_por = st.session_state.get('identificador', 'admin')
                datos = {"nombre": nombre, "creado_por": creado_por}
                for i in range(1, 7):
                    especialidad_key = f"esp_mod_{i}"
                    if especialidad_key in st.session_state:
                        especialidad = st.session_state[especialidad_key]
                        datos[f"modulo_{i}"] = especialidad
                        if especialidad == "No asignar": datos[f"caso_{i}"] = ""
                        else: datos[f"caso_{i}"] = st.session_state.get(f'caso_seleccionado_clave_{i}', '')
                    else:
                        datos[f"modulo_{i}"] = ""
                        datos[f"caso_{i}"] = ""
                
                exito, mensaje = crear_circuito_supabase(datos) if modo == "crear" else actualizar_circuito_supabase(circuito['id'], datos)
                
                if exito:
                    st.success(mensaje)
                    st.session_state['mostrar_formulario_circuito'] = False
                    st.session_state['editando_circuito'] = None
                    for i in range(1, 7):
                        for k in [f'preview_caso_{i}', f'caso_seleccionado_clave_{i}', f'mostrar_casos_mod_{i}', f'ultima_especialidad_{i}', f'esp_mod_{i}', f'caso_mod_{i}']:
                            if k in st.session_state: del st.session_state[k]
                    if 'nombre_circuito_actual' in st.session_state: del st.session_state['nombre_circuito_actual']
                    if 'caso_para_modal' in st.session_state: del st.session_state['caso_para_modal']
                    st.session_state['pagina'] = 'admin'
                    st.rerun()
                else: st.error(mensaje)

    # ===== RENDERIZAR EL MODAL SI HAY UN CASO SELECCIONADO =====
    if st.session_state.get('caso_para_modal'):
        _modal_ver_caso_admin(st.session_state['caso_para_modal'])