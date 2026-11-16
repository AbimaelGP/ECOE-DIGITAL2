# escenas/escena_panel_medico.py
import streamlit as st
from datetime import datetime
import pandas as pd
import json
from utils.supabase_client import supabase, SUPABASE_URL
import os
import shutil
from pathlib import Path
from utils.pdf_caso import generar_pdf_caso
from utils.casos import cargar_info_caso, formatear_fecha_inteligente


# ==================== FUNCIONES PARA SPRITES ====================

def obtener_sprite_segun_edad_sexo(edad, sexo):
    """
    Retorna la URL pública del sprite correspondiente según edad y sexo
    desde Supabase Storage (sprite automático)
    """
    if edad < 12:
        categoria = "ninos"
    elif edad < 20:
        categoria = "adolescentes"
    elif edad < 60:
        categoria = "adultos"
    else:
        categoria = "adulto_mayor"
   
    if sexo.lower() in ["femenino", "femenino"]:
        genero = "femenino"
    else:
        genero = "masculino"
   
    url = f"{SUPABASE_URL}/storage/v1/object/public/sprites/{categoria}_{genero}.png"
    return url


def obtener_sprites_disponibles():
    """Retorna la lista de todos los sprites disponibles con sus URLs"""
    return [
        {"nombre": "Niño", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/ninos_masculino.png"},
        {"nombre": "Niña", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/ninos_femenino.png"},
        {"nombre": "Adolescente M", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adolescentes_masculino.png"},
        {"nombre": "Adolescente F", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adolescentes_femenino.png"},
        {"nombre": "Adulto M", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adultos_masculino.png"},
        {"nombre": "Adulto F", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adultos_femenino.png"},
        {"nombre": "Adulto Mayor M", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adulto_mayor_masculino.png"},
        {"nombre": "Adulto Mayor F", "url": f"{SUPABASE_URL}/storage/v1/object/public/sprites/adulto_mayor_femenino.png"}
    ]


def mostrar_selector_sprite():
    """Muestra un selector de sprites en un popover"""
    sprites = obtener_sprites_disponibles()
   
    if 'sprite_seleccionado' not in st.session_state:
        st.session_state.sprite_seleccionado = None
   
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
           
            if st.button(f"Seleccionar", key=f"sprite_sel_{idx}"):
                st.session_state.sprite_seleccionado = sprite['url']
                st.success("Imagen seleccionada")
                st.rerun()
           
            if st.session_state.sprite_seleccionado == sprite['url']:
                st.markdown('')


# ==================== FUNCIONES DE SUPABASE ====================

def obtener_medico_supabase(identificador):
    if not supabase:
        return None
   
    try:
        response = supabase.table("perfiles_medicos").select("*").eq("identificador", identificador).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error al obtener médico: {e}")
        return None


def obtener_casos_medico_supabase(identificador_medico, modulo_asignado):
    if not supabase:
        return []
   
    try:
        response = supabase.table("casos_clinicos").select("*").eq("responsable", identificador_medico).execute()
        casos = []
        for caso in response.data:
            if modulo_asignado in caso.get('especialidad', ''):
                casos.append(caso)
        return casos
    except Exception as e:
        print(f"Error al obtener casos: {e}")
        return []


def obtener_siguiente_numero_caso(codigo):
    if not supabase:
        return 1
   
    try:
        response = supabase.table("casos_clinicos").select("clave_caso").like("clave_caso", f"{codigo}%").order("clave_caso", desc=True).limit(1).execute()
        if response.data and len(response.data) > 0:
            ultima_clave = response.data[0]['clave_caso']
            try:
                numero = int(ultima_clave[len(codigo):])
                return numero + 1
            except ValueError:
                return 1
        return 1
    except Exception as e:
        print(f"Error al obtener siguiente número: {e}")
        return 1


def obtener_valores_estudios_predeterminados():
    return {
        "Biometria Hematica": {
            "parametros": {
                "Hemoglobina": {"valor": 14.5, "unidad": "g/dL"},
                "Hematocrito": {"valor": 42, "unidad": "%"},
                "Leucocitos": {"valor": 7.5, "unidad": "x10³/µL"},
                "Plaquetas": {"valor": 250, "unidad": "x10³/µL"}
            }
        },
        "Prueba de glucosa en sangre": {
            "parametros": {
                "Glucosa": {"valor": 90, "unidad": "mg/dL"}
            }
        },
        "Troponinas": {
            "parametros": {
                "Troponina I": {"valor": 0.02, "unidad": "ng/mL"}
            }
        },
        "Pruebas de funcion pulmonar": {
            "parametros": {
                "FEV1": {"valor": 3.5, "unidad": "L"},
                "FVC": {"valor": 4.2, "unidad": "L"},
                "Relacion FEV1/FVC": {"valor": 83, "unidad": "%"}
            }
        },
        "Electrocardiograma": {
            "tipo": "imagen",
            "parametros": {}
        },
        "EGO": {
            "parametros": {
                "Proteinas": {"valor": "Negativo", "unidad": "mg/dL"},
                "Leucocitos": {"valor": 2, "unidad": "por campo"},
                "Densidad": {"valor": 1.020, "unidad": ""},
                "pH": {"valor": 6.0, "unidad": ""},
                "Glucosa": {"valor": "Negativo", "unidad": ""}
            }
        },
        "Rayos X de Torax": {
            "tipo": "imagen",
            "parametros": {}
        },
        "Ecocardiograma": {
            "tipo": "imagen",
            "parametros": {}
        },
        "Radiografia de Abdomen": {
            "tipo": "imagen",
            "parametros": {}
        },
        "Tomografia Abdominal": {
            "tipo": "imagen",
            "parametros": {}
        }
    }

def guardar_caso_completo_supabase(clave_caso, especialidad, responsable, nombre, edad, sexo,
                                   motivo_consulta, descripcion, antecedentes,
                                   medicamentos_actuales, valores_estudios):
    if not supabase:
        return False, "Supabase no conectado"
    
    try:
        check = supabase.table("casos_clinicos").select("clave_caso").eq("clave_caso", clave_caso).execute()
        if check.data:
            return False, f"La clave {clave_caso} ya existe"
        
        codigo = clave_caso[:2] if len(clave_caso) >= 2 else "XX"
        
        # ===== RECUPERAR URLs DE IMÁGENES =====
        urls_imagenes = {}
        if 'imagenes_subidas' in st.session_state:
            for key, url in st.session_state.imagenes_subidas.items():
                if key.startswith(f"{clave_caso}_"):
                    nombre_estudio = key.replace(f"{clave_caso}_", "")
                    urls_imagenes[nombre_estudio] = url
            # Limpiar después de recuperar
            del st.session_state.imagenes_subidas
        
        data_paciente = {
            "nombre": nombre,
            "edad": edad,
            "sexo": sexo,
            "motivo_consulta": motivo_consulta,
            "descripcion": descripcion,
            "antecedentes": antecedentes,
            "medicamentos_actuales": medicamentos_actuales
        }
        
        sprite_url = st.session_state.get('sprite_seleccionado')
        if not sprite_url:
            sprite_url = obtener_sprite_segun_edad_sexo(edad, sexo)
        
        data = {
            "clave_caso": clave_caso,
            "especialidad": especialidad,
            "especialidad_codigo": codigo,
            "responsable": responsable,
            "data": data_paciente,
            "valores_estudios": valores_estudios,
            "imagenes_estudios": urls_imagenes,
            "sprite_url": sprite_url,
            "fecha_actualizacion": datetime.now().strftime('%Y-%m-%d')
        }
        
        response = supabase.table("casos_clinicos").insert(data).execute()
        return True, "Caso creado exitosamente"
    except Exception as e:
        print(f"❌ Error guardando caso: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error: {str(e)}"

def eliminar_caso_supabase(clave_caso):
    if not supabase:
        return False, "Supabase no conectado"
   
    try:
        supabase.table("casos_clinicos").delete().eq("clave_caso", clave_caso).execute()
        return True, "Caso eliminado"
    except Exception as e:
        return False, f"Error: {str(e)}"


def obtener_caso_por_clave(clave_caso):
    if not supabase:
        return None
   
    try:
        response = supabase.table("casos_clinicos").select("*").eq("clave_caso", clave_caso).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error al obtener caso: {e}")
        return None

def actualizar_caso_supabase(clave_caso, datos_actualizados):
    if not supabase:
        return False, "Supabase no conectado"
    
    try:
        caso_actual = obtener_caso_por_clave(clave_caso)
        
        # ===== SPRITE =====
        sprite_seleccionado = st.session_state.get('sprite_seleccionado')
        if sprite_seleccionado:
            datos_actualizados['sprite_url'] = sprite_seleccionado
        
        if not sprite_seleccionado:
            data_actual = caso_actual.get('data', {})
            edad_actual = data_actual.get('edad')
            sexo_actual = data_actual.get('sexo')
            
            data_nuevo = datos_actualizados.get('data', {})
            edad_nuevo = data_nuevo.get('edad')
            sexo_nuevo = data_nuevo.get('sexo')
            
            if edad_nuevo is not None and sexo_nuevo is not None and (edad_nuevo != edad_actual or sexo_nuevo != sexo_actual):
                sprite_url = obtener_sprite_segun_edad_sexo(edad_nuevo, sexo_nuevo)
                datos_actualizados['sprite_url'] = sprite_url
        
        # ===== IMÁGENES =====
        if 'imagenes_editadas' in st.session_state:
            imagenes_actuales = caso_actual.get('imagenes_estudios', {})
            for key, url in st.session_state.imagenes_editadas.items():
                if key.startswith(f"{clave_caso}_"):
                    nombre_estudio = key.replace(f"{clave_caso}_", "")
                    imagenes_actuales[nombre_estudio] = url
            datos_actualizados['imagenes_estudios'] = imagenes_actuales
            del st.session_state.imagenes_editadas
        
        datos_actualizados['fecha_actualizacion'] = datetime.now().strftime('%Y-%m-%d')
        
        response = supabase.table("casos_clinicos").update(datos_actualizados).eq("clave_caso", clave_caso).execute()
        return True, "Caso actualizado exitosamente"
    except Exception as e:
        print(f"Error al actualizar caso: {e}")
        return False, f"Error: {str(e)}"

def guardar_imagen_estudio(archivo_subido, clave_caso, nombre_estudio):
    if not archivo_subido:
        return None
   
    carpeta_destino = Path(f"data/casos_clinicos/{clave_caso}/imagenes")
    carpeta_destino.mkdir(parents=True, exist_ok=True)
   
    extension = archivo_subido.name.split('.')[-1]
    nombre_archivo = f"{clave_caso}_{nombre_estudio.replace(' ', '_')}.{extension}"
    ruta_completa = carpeta_destino / nombre_archivo
   
    with open(ruta_completa, "wb") as f:
        f.write(archivo_subido.getbuffer())
   
    return str(ruta_completa)


def obtener_imagen_estudio(clave_caso, nombre_estudio):
    carpeta = Path(f"data/casos_clinicos/{clave_caso}/imagenes")
    if not carpeta.exists():
        return None
   
    patron = f"{clave_caso}_{nombre_estudio.replace(' ', '_')}.*"
    archivos = list(carpeta.glob(patron))
   
    if archivos:
        return str(archivos[0])
    return None


# ==================== MOSTRAR DASHBOARD ====================

def mostrar():
    """Muestra el dashboard del médico"""
       # ===== LEER IMAGEN DE FONDO EN BASE64 =====
    import base64
    ruta_imagen = Path("data/recursos/fondo_inicio.png")
    
    if ruta_imagen.exists():
        with open(ruta_imagen, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        bg_image_css = f'background-image: url("data:image/png;base64,{encoded_string}") !important;'
    else:
        print("⚠️ Advertencia: No se encontró data/recursos/fondo_inicio.png")
        bg_image_css = 'background-color: #F1F2F5 !important;'
        
    # CSS
    st.markdown(f"""
    <style>        
        /* Fondo general con la imagen */
        .stApp {{
            {bg_image_css}
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}
       
        [data-testid="stSidebar"] {{
            background-color: #70257E !important;
        }}
        [data-testid="stSidebar"] * {{
            color: #FFFFFF !important;
        }}
       
        .medico-title {{
            text-align: center;
            color: #252A38;
            font-family: 'Poppins', sans-serif;
            font-size: 42px;
            font-weight: 700;
            margin-top: 1rem;
            margin-bottom: 2rem;
            text-shadow: 1px 1px 4px rgba(255,255,255,0.8); /* Sombra para legibilidad */
        }}
       
        .section-title {{
            color: #252A38;
            font-family: 'Poppins', sans-serif;
            font-size: 24px;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            border-left: 4px solid #70257E;
            padding-left: 1rem;
            text-shadow: 1px 1px 4px rgba(255,255,255,0.8);
        }}

        /* ===== BOTÓN AÑADIR CASO (MORADO) ===== */
        .st-key-contenedor_boton_anadir button {{
            background-color: #70257E !important;
            color: #FFFFFF !important;
            border: 2px solid #70257E !important;
            font-weight: bold !important;
            border-radius: 8px !important;
        }}
        .st-key-contenedor_boton_anadir button:hover {{
            background-color: #5B1E66 !important;
            border-color: #5B1E66 !important;
        }}

        /* ===== BOTONES EDITAR Y ELIMINAR (GRIS) ===== */
        .st-key-contenedor_boton_editar button,
        .st-key-contenedor_boton_eliminar button {{
            background-color: #E5E7EC !important;
            color: #303442 !important;
            border: none !important;
            border-radius: 6px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
        }}
        .st-key-contenedor_boton_editar button:hover,
        .st-key-contenedor_boton_eliminar button:hover {{
            background-color: #D1D5DB !important;
        }}
       
        .stTextInput input,
        .stSelectbox select,
        .stTextInput textarea,
        .stNumberInput input {{
            background-color: #FFFFFF !important;
            border: 2px solid #70257E !important;
            border-radius: 8px !important;
        }}
        .stTextInput input:focus,
        .stSelectbox select:focus,
        .stNumberInput input:focus {{
            border-color: #70257E !important;
            box-shadow: 0 0 0 2px rgba(112, 37, 126, 0.3) !important;
            outline: none !important;
        }}
       
        textarea {{
            background-color: #FFFFFF !important;
            border: 2px solid #70257E !important;
            border-radius: 8px !important;
        }}
        textarea:focus {{
            border-color: #70257E !important;
            box-shadow: 0 0 0 2px rgba(112, 37, 126, 0.3) !important;
            outline: none !important;
        }}
       
        .caso-nuevo-title {{
            color: #252A38;
            font-family: 'Poppins', sans-serif;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 1.5rem;
            border-left: 4px solid #70257E;
            padding-left: 1rem;
        }}
       
        .stButton button[type="primary"] {{
            background-color: #70257E !important;
            color: #FFFFFF !important;
            border: 2px solid #70257E !important;
            font-weight: bold !important;
        }}
        .stButton button[type="primary"]:hover {{
            background-color: #5B1E66 !important;
            border-color: #5B1E66 !important;
        }}
       
        .stTextInput input:disabled {{
            background-color: #E5E7EC !important;
            border: 2px solid #E5E7EC !important;
            color: #626779 !important;
        }}
       
        hr {{
            border-color: #70257E !important;
            border-width: 1px !important;
        }}
       
        div[data-testid="stPopover"] {{
            border: 2px solid #70257E !important;
            background-color: #FFFFFF !important;
            border-radius: 10px !important;
        }}
       
        .stAlert {{
            border: none !important;
            background-color: #FFFFFF !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Titulo
    st.markdown('<h1 class="medico-title">Perfil de Médico</h1>', unsafe_allow_html=True)
   
    identificador_medico = st.session_state.get('identificador', '')
   
    medico_data = obtener_medico_supabase(identificador_medico)
    modulo_asignado = medico_data.get('modulo_asignado', 'No asignado') if medico_data else 'No asignado'

    # ===== PESTAÑAS DEL PERFIL MÉDICO =====
    opciones_vista = ["Casos Clínicos", "Evaluar Estudiantes"]
    vista_inicial = 1 if st.session_state.pop("medico_tab", None) == "evaluar" else None
    if vista_inicial is not None:
        st.session_state["medico_vista"] = opciones_vista[vista_inicial]
    vista = st.radio("Vista", opciones_vista, horizontal=True, key="medico_vista", label_visibility="collapsed")

    if vista == "Evaluar Estudiantes":
        from escenas import escena_medico_evaluar
        escena_medico_evaluar.mostrar_lista()
    else:
        st.markdown('<div class="section-title">Casos Clínicos</div>', unsafe_allow_html=True)
    
        col_add1, col_add2, col_add3 = st.columns([3, 1, 1])
        with col_add3:
            with st.container(key="contenedor_boton_anadir"):
                if st.button("+ Añadir caso", use_container_width=True, key="btn_anadir_caso"):
                    from escenas.crear_caso.utils import iniciar_modo_crear
                    iniciar_modo_crear()
                    st.session_state['pagina'] = 'crear_caso_paso_1'
                    st.rerun()
    
        st.markdown("---")
       
        casos = obtener_casos_medico_supabase(identificador_medico, modulo_asignado)
    
        if casos:
            with st.container():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([0.8, 2.2, 1.6, 1.1, 0.8, 1, 1])

                with col1:
                    st.markdown("**Clave**")
                with col2:
                    st.markdown("**Descripción**")
                with col3:
                    st.markdown("**Área**")
                with col4:
                    st.markdown("**Fecha Actualizado**")
                with col5:
                    st.markdown("**Editar**")
                with col6:
                    st.markdown("**Eliminar**")
                with col7:
                    st.markdown("**Descargar**")
            
                st.markdown("---")
            
                for caso in casos:
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([0.8, 2.2, 1.6, 1.1, 0.8, 1, 1])
                
                    data_paciente = caso.get('data', {})
                    descripcion = data_paciente.get('descripcion', 'Sin descripción')
                
                    with col1:
                        st.markdown(f"{caso['clave_caso']}")
                    with col2:
                        st.markdown(f'<span style="font-size: 12px; color: #626779;">{descripcion}</span>', unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"{caso['especialidad']}")
                    with col4:
                        fecha_raw = caso.get('fecha_actualizacion', '')
                        fecha_formateada = formatear_fecha_inteligente(fecha_raw)
                        st.markdown(f"{fecha_formateada}")
                    with col5:
                        with st.container(key=f"contenedor_boton_editar_{caso['clave_caso']}"):
                            if st.button("Editar", key=f"editar_{caso['clave_caso']}", use_container_width=True):
                                from escenas.crear_caso.utils import iniciar_modo_editar
                                exito = iniciar_modo_editar(caso['clave_caso'])
                                if exito:
                                    st.session_state['pagina'] = 'editar_caso_paso_1'
                                    st.rerun()
                                else:
                                    st.error(f"No se pudo cargar el caso {caso['clave_caso']} para editar")
                    with col6:
                        with st.container(key=f"contenedor_boton_eliminar_{caso['clave_caso']}"):
                            with st.popover("Eliminar", use_container_width=True):
                                st.warning(f"¿Eliminar caso '{data_paciente.get('nombre', caso['clave_caso'])}'?")
                                col_si, col_no = st.columns(2)
                                with col_si:
                                    if st.button("Sí", key=f"confirmar_si_{caso['clave_caso']}", use_container_width=True):
                                        exito, mensaje = eliminar_caso_supabase(caso['clave_caso'])
                                        if exito:
                                            st.success("Caso eliminado")
                                            st.rerun()
                                        else:
                                            st.error(mensaje)
                                with col_no:
                                    if st.button("No", key=f"confirmar_no_{caso['clave_caso']}", use_container_width=True):
                                        st.rerun()
                
                    with col7:
                        with st.container(key=f"contenedor_boton_pdf_{caso['clave_caso']}"):
                            # Generar PDF al hacer clic (lazy)
                            if st.button("PDF", key=f"pdf_{caso['clave_caso']}", use_container_width=True):
                                with st.spinner("Generando PDF..."):
                                    try:
                                        info_caso = cargar_info_caso(caso['clave_caso'])
                                        if not info_caso:
                                            st.error("No se pudo cargar la información del caso")
                                        else:
                                            pdf_buffer = generar_pdf_caso(caso['clave_caso'], info_caso)
                                            st.session_state[f'pdf_bytes_{caso["clave_caso"]}'] = pdf_buffer.getvalue()
                                            st.session_state[f'pdf_ready_{caso["clave_caso"]}'] = True
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"Error generando PDF: {e}")
                        
                            # Mostrar botón de descarga si el PDF ya está listo
                            if st.session_state.get(f'pdf_ready_{caso["clave_caso"]}', False):
                                st.download_button(
                                    label="⬇ Descargar",
                                    data=st.session_state[f'pdf_bytes_{caso["clave_caso"]}'],
                                    file_name=f"{caso['clave_caso']}_{data_paciente.get('nombre_caso', 'caso').replace(' ', '_')}.pdf",
                                    mime="application/pdf",
                                    key=f"download_{caso['clave_caso']}",
                                    use_container_width=True,
                                )
                
                    st.markdown("---")
        else:
            st.info("No tienes casos creados. Presiona '+ Añadir caso' para crear uno.")
   
    # Sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**Médico:** {st.session_state.get('nombre', 'Médico')}")
        st.markdown(f"**ID:** {st.session_state.get('identificador', '')}")
        st.markdown(f"**Área Asignada:** {modulo_asignado}")
        st.markdown("---")
       
        if st.button("Cerrar sesión", use_container_width=True):
            for key in ['autenticado', 'tipo_usuario', 'identificador', 'nombre', 'permisos', 'pagina']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def subir_imagen_supabase(archivo_subido, clave_caso, nombre_estudio):
    """
    Sube una imagen a Supabase Storage y retorna la URL pública
    """
    if not supabase or not archivo_subido:
        return None
    
    try:
        extension = archivo_subido.name.split('.')[-1].lower()
        nombre_archivo = f"{clave_caso}_{nombre_estudio.replace(' ', '_')}.{extension}"
        ruta_storage = f"casos_clinicos/{clave_caso}/imagenes/{nombre_archivo}"
        
        supabase.storage.from_("casos_clinicos").upload(
            path=ruta_storage,
            file=archivo_subido.getvalue(),
            file_options={"content-type": archivo_subido.type}
        )
        
        url_publica = supabase.storage.from_("casos_clinicos").get_public_url(ruta_storage)
        return url_publica
        
    except Exception as e:
        print(f"❌ Error al subir imagen: {e}")
        return None