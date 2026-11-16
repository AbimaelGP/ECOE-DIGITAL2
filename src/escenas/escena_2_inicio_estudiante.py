# escenas/escena_2_inicio_estudiante.py
import streamlit as st
from datetime import datetime
import base64
from pathlib import Path
from utils.database import obtener_datos_estudiante, actualizar_estatus_estudiante
from utils.actividad_estudiante import actualizar_actividad_estudiante
from utils.supabase_client import supabase


def mostrar():
    """Muestra la pantalla de inicio del estudiante"""
    
    nombre = st.session_state['nombre']
    matricula = st.session_state['identificador']
    
    actualizar_actividad_estudiante(matricula, "inicio")
    
    # ===== OBTENER DATOS =====
    datos = obtener_datos_estudiante(matricula)
    
    # ===== CONSULTAR SI EL EXAMEN ESTÁ ACTIVO =====
    examen_activo = False
    try:
        if supabase:
            config_response = supabase.table("configuracion_examen").select("examen_activo").eq("id", 1).execute()
            if config_response.data:
                examen_activo = config_response.data[0].get('examen_activo', False)
    except Exception as e:
        print(f"Error al consultar configuracion_examen: {e}")
    
    # ===== LEER IMAGEN DE FONDO EN BASE64 =====
    ruta_imagen = Path("data/recursos/fondo_inicio.png")
    
    if ruta_imagen.exists():
        with open(ruta_imagen, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        bg_image_css = f'background-image: url("data:image/png;base64,{encoded_string}") !important;'
    else:
        print("⚠️ Advertencia: No se encontró data/recursos/fondo_inicio.png")
        bg_image_css = 'background-color: #F8F7FA !important;'
    
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

        /* Contenedor blanco semi-transparente para que resalte sobre el fondo */
        .contenedor-examen {{
            background-color: rgba(255, 255, 255, 0.95);
            padding: 2.5rem;
            border-radius: 20px;
            margin: 2rem 0;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
            border: 1px solid #F0EAF2;
            backdrop-filter: blur(5px);
        }}

        /* Botón principal (Iniciar Examen) */
        .stButton > button[kind="secondary"] {{
            background-color: #70257E !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            padding: 0.6rem 1rem !important;
            transition: all 0.3s ease !important;
        }}
        .stButton > button[kind="secondary"]:hover {{
            background-color: #5B1E66 !important;
            box-shadow: 0 4px 12px rgba(112, 37, 126, 0.4) !important;
        }}

        /* Botón secundario (Cerrar sesión) */
        .stButton > button {{
            background-color: #E5E7EC !important;
            color: #303442 !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 500 !important;
        }}
        .stButton > button:hover {{
            background-color: #D1D5DB !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Bienvenida
    st.markdown(f"""
    <div style="margin-top: 2rem;">
        <p style="color: #626779; font-family: Poppins; font-size: 28px; font-weight: 400; margin: 0; text-shadow: 1px 1px 3px rgba(255,255,255,0.8);">
            Te damos la bienvenida
        </p>
        <p style="color: #70257E; font-family: Poppins; font-size: 48px; font-weight: 700; margin: 0; text-shadow: 1px 1px 3px rgba(255,255,255,0.8);">
            {nombre}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if datos:
        # ===== ACCEDER A LOS CAMPOS DEL DICCIONARIO =====
        fecha_examen = datos.get('fecha_examen', '')
        hora_inicio = datos.get('hora_inicio', '')
        hora_fin = datos.get('hora_fin', '')
        clave_acceso = datos.get('clave_acceso', '')
        estatus = datos.get('estatus', 'Pendiente')
        
        ahora = datetime.now()
        
        # ===== PARSEAR FECHA Y HORA =====
        fecha_hora_inicio = None
        fecha_hora_fin = None
        
        formatos_fecha = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
        formatos_hora = ["%H:%M", "%H:%M:%S"]
        
        for fmt_fecha in formatos_fecha:
            for fmt_hora in formatos_hora:
                try:
                    fecha_hora_inicio = datetime.strptime(f"{fecha_examen} {hora_inicio}", f"{fmt_fecha} {fmt_hora}")
                    fecha_hora_fin = datetime.strptime(f"{fecha_examen} {hora_fin}", f"{fmt_fecha} {fmt_hora}")
                    break
                except:
                    continue
            if fecha_hora_inicio:
                break
        
        # Si no se pudo parsear, mostrar error
        if not fecha_hora_inicio:
            st.error(f"No se pudo interpretar la fecha del examen: '{fecha_examen}' '{hora_inicio}'")
            return
        
        # ===== VALIDAR PERIODO Y ESTADO =====
        if ahora >= fecha_hora_inicio and ahora <= fecha_hora_fin and estatus != 'Finalizado':
            
            # VALIDACIÓN: El administrador desactivó el examen
            if not examen_activo:
                st.markdown("""
                <div style="background-color: rgba(220,53,69,0.12); padding: 2rem; border-radius: 20px; margin: 2rem 0; text-align: center; border: 2px solid #dc3545; backdrop-filter: blur(5px);">
                    <p style="color: #721c24; font-size: 20px; font-weight: 500;">El examen está temporalmente desactivado por el administrador.</p>
                    <p style="color: #721c24; font-size: 16px;">Por favor, espera a que sea habilitado.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Examen activo
                st.markdown("""
                <div class="contenedor-examen">
                    <p style="color: #303442; font-size: 20px; font-weight: 500; margin: 0;">Tu examen está disponible ahora</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([2, 1.2, 2])
                with col2:
                    if st.button("Iniciar examen", key="btn_iniciar_examen", use_container_width=True, type="primary"):
                        st.session_state['popup_clave'] = True
                
                # Pop up de clave
                if st.session_state.get('popup_clave', False):
                    col1, col2, col3 = st.columns([2, 1.1, 2])
                    with col2:
                        with st.popover("Ingresa tu clave de acceso"):
                            st.markdown("Para comenzar, ingresa la clave proporcionada por tu asesor.")
                            clave_ingresada = st.text_input("Clave de acceso", type="password", key="input_clave_examen")
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("Confirmar", key="btn_confirmar_clave", use_container_width=True):
                                    if clave_ingresada == clave_acceso:
                                        actualizar_estatus_estudiante(matricula, 'Iniciado')
                                        st.session_state['popup_clave'] = False
                                        st.session_state['pagina'] = 'instrucciones'
                                        actualizar_actividad_estudiante(matricula, "instrucciones")
                                        st.rerun()
                                    else:
                                        st.error("Clave incorrecta")
                            with col_b:
                                if st.button("Cancelar", key="btn_cancelar_clave", use_container_width=True):
                                    st.session_state['popup_clave'] = False
                                    st.rerun()
        
        elif ahora < fecha_hora_inicio:
            st.markdown(f"""
            <div class="contenedor-examen">
                <p style="color: #303442; font-size: 18px;">Tu examen estará disponible el:</p>
                <p style="color: #252A38; font-size: 32px; font-weight: 700;">{fecha_examen}</p>
                <p style="color: #303442; font-size: 24px;">{hora_inicio} - {hora_fin}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="contenedor-examen">
                <p style="color: #303442; font-size: 20px;">El período para este examen ha finalizado.</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No tienes ningún examen programado.")