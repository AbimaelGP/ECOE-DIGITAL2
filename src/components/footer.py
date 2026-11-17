import streamlit as st

def mostrar_footer():
    """Créditos al final de la página (no flotan sobre el contenido)."""
    st.markdown("""
    <style>
        .footer {
            text-align: center;
            color: #8A8FA0;
            font-size: 12px;
            line-height: 1.5;
            font-family: 'Poppins', sans-serif;
            margin-top: 4rem;
            padding: 1.5rem 1rem 0.5rem;
            border-top: 1px solid #E5E7EC;
        }
    </style>
    <div class="footer">©2026. Desarrollada por Natalia Acevedo, Maribel Aguilar, Carla Alvarado, Paulina González, Dr. Abimael Guzmán Pando & Dra. Haydeé Parra Acosta. <br> Laboratorio de Investigación en Inteligencia Artificial y Computación Médica (LIIACOM), Facultad de Medicina y Ciencias Biomédicas, UACH.</div>
    """, unsafe_allow_html=True)
