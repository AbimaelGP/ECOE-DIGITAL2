# components/background.py
import streamlit as st
import base64
from pathlib import Path

def set_background(image_path="data/recursos/background.png"):
    """Establece una imagen de fondo para toda la app"""
    
    img_path = Path(image_path)
    
    # Verificar si la imagen existe
    if not img_path.exists():
        st.warning(f"No se encontró la imagen en: {img_path.absolute()}")
        return
    
    # Convertir imagen a base64
    with open(img_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode()
    
    # Aplicar fondo con CSS
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: #F1F2F5 !important;
        }}
    </style>
    """, unsafe_allow_html=True)