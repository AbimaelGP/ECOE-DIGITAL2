import streamlit as st

def mostrar_footer():
    """Muestra el footer en la parte inferior de todas las escenas"""
    st.markdown("""
    <style>
        .footer {
            text-align: center;
            left:0;
            color: #626779;
            padding: 2rem;
            font-size: 14px;
            font-family: 'Poppins', sans-serif;
            position: fixed;
            bottom: 0;
            width: 100%;
        }
    </style>
    <div class="footer">©2026. Desarrollada por Natalia Acevedo, Maribel Aguilar, Carla Alvarado, Paulina González, Dr. Abimael Guzmán Pando & Dra. Haydeé Parra Acosta. <br> Laboratorio de Investigación en Inteligencia Artificial y Computación Médica (LIIACOM), Facultad de Medicina y Ciencias Biomédicas, UACH.</div>
    """, unsafe_allow_html=True)