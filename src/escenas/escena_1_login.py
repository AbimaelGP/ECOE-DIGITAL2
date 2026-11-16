# escenas/escena_1_login.py
import streamlit as st
import hashlib
import uuid
import os
import base64
from pathlib import Path
from components.background import set_background
from utils.actividad_estudiante import actualizar_actividad_estudiante
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Credenciales de Supabase no encontradas")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Conexion a Supabase establecida")

def verificar_credenciales_supabase(identificador, password):
    """Verifica credenciales usando Supabase"""
    if not supabase:
        return None
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        response = supabase.table("usuarios").select("*").eq("identificador", identificador).eq("password_hash", password_hash).execute()
        
        if response.data and len(response.data) > 0:
            usuario = response.data[0]
            return (usuario['tipo_usuario'], usuario['nombre'], usuario.get('permisos'))
        return None
    except Exception as e:
        print(f"Error en verificacion Supabase: {e}")
        return None

def mostrar():
    """Muestra la pantalla de inicio de sesion"""
    set_background()
    
    # ===== LEER IMAGEN DE FONDO EN BASE64 =====
    ruta_imagen = Path("data/recursos/fondo.png")
    
    if ruta_imagen.exists():
        with open(ruta_imagen, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        bg_image_css = f'background-image: url("data:image/png;base64,{encoded_string}") !important;'
    else:
        print("⚠️ Advertencia: No se encontró data/recursos/fondo.png")
        bg_image_css = 'background-color: #F1F2F5 !important;'
    
    # CSS especifico para login
    st.markdown(f"""
    <style>
        /* Ocultar el header de Streamlit para que la línea amarilla se vea completa */
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
            background: transparent !important;
        }}

        /* Fondo general con la imagen alineada arriba */
        .stApp {{
            {bg_image_css}
            background-size: cover !important;
            background-position: top center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}

        /* Contenedor del formulario semi-transparente */
        [data-testid="stForm"] {{
            background-color: rgba(255, 255, 255, 0.95) !important;
            border-radius: 15px !important;
            padding: 2rem !important;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important;
            border: 1px solid #E5E7EC !important;
            backdrop-filter: blur(5px);
            margin-top: 5vh;
        }}

        .login-title {{
            color: #626779;
            font-size: 20px;
            font-weight: 400;
            text-align: center;
            margin-bottom: 2rem;
        }}
        
        .main-title {{
            text-align: center;
            color: #70257E !important;
            font-family: 'Poppins', sans-serif;
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 2rem;
            margin-top: 2rem;
        }}

        /* Inputs de texto en blanco */
        .stTextInput > div > div > input {{
            background-color: #FFFFFF !important;
            border-radius: 8px;
            border: 1px solid #E5E7EC;
            padding: 0.75rem;
            color: #303442 !important;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: #70257E !important;
            box-shadow: 0 0 0 1px #70257E !important;
        }}

        /* Arreglar el botón del ojo (con doble llave para que Python no lo confunda) */
        [data-testid="stTextInput"] button {{
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }}
        
        [data-testid="stTextInput"] button svg {{
            fill: #70257E !important;
        }}

        /* Botón morado */
        .stButton > button, 
        .stFormSubmitButton > button {{
            background-color: #70257E !important;
            color: #FFFFFF !important;
            font-family: 'Poppins', sans-serif;
            font-weight: 500;
            padding: 0.75rem 2rem;
            border-radius: 8px;
            border: none;
            width: 100%;
            transition: all 0.3s ease;
        }}
        
        .stButton > button:hover,
        .stFormSubmitButton > button:hover {{
            background-color: #5B1E66 !important;
            box-shadow: 0 4px 12px rgba(112, 37, 126, 0.4) !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Titulo principal
    st.markdown('<h1 class="main-title">Examen Clínico Objetivo Estructurado</h1>', unsafe_allow_html=True)
    
    # Contenedor del login
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown('<p class="login-title">Iniciar sesión</p>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            identificador = st.text_input("Matrícula", placeholder="Ingresa tu matrícula")
            password = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña")
            
            if st.form_submit_button("Continuar", use_container_width=True):
                if identificador and password:
                    usuario = verificar_credenciales_supabase(identificador, password)
                    
                    if usuario:
                        tipo_usuario, nombre, permisos = usuario
                        session_id = str(uuid.uuid4())
                        
                        st.session_state['autenticado'] = True
                        st.session_state['tipo_usuario'] = tipo_usuario
                        st.session_state['identificador'] = identificador
                        st.session_state['nombre'] = nombre
                        st.session_state['permisos'] = permisos
                        st.session_state['session_id'] = session_id
                        
                        if tipo_usuario == 'estudiante':
                            st.session_state['pagina'] = 'inicio_estudiante'
                            actualizar_actividad_estudiante(identificador, "inicio")
                        elif tipo_usuario == 'administrador':
                            st.session_state['pagina'] = 'admin'
                        elif tipo_usuario == 'medico':
                            st.session_state['pagina'] = 'panel_medico'
                        else:
                            st.session_state['autenticado'] = False
                            st.error("Tipo de usuario no reconocido")
                        
                        st.success(f"¡Bienvenido {nombre}!")
                        st.rerun()
                    else:
                        st.error("Matrícula o contraseña incorrectos")
                else:
                    st.warning("Por favor ingresa ambos campos")