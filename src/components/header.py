import streamlit as st

def mostrar_header():
    """Muestra los logos en la parte superior de todas las escenas"""
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        try:
            st.image("data/recursos/logouni.svg", width=150)
        except:
            st.image("https://via.placeholder.com/150x80?text=UNI", width=150)
    with col3:
        try:
            st.image("data/recursos/logofacu.svg", width=150)
        except:
            st.image("https://via.placeholder.com/150x80?text=FACU", width=150)