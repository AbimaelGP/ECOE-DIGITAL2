# components/modal_ver_circuito.py
import streamlit as st
from utils.casos import cargar_info_caso
from utils.pdf_caso import generar_pdf_caso

COLOR_ASIGNADO = "#70257E"       # Morado principal
COLOR_SIN_CASO = "#8B95A5"       # Gris para módulos asignados pero sin caso
COLOR_VACIO = "#E5E7EC"          # Gris claro para "No asignado"

def mostrar_modal_ver_circuito(circuito):
    """Muestra un modal con el diseño visual del circuito (6 módulos)."""
    
    @st.dialog(f" ", width="large")
    def _dialog():
        # ===== OCULTAR LA X DE CERRAR NATIVA =====
        st.markdown("""
        <style>
            /* Ocultar el botón de cerrar (la tachita) del diálogo */
            div[data-testid="stDialog"] button[aria-label="Close"] {
                display: none !important;
            }
        </style>
        """, unsafe_allow_html=True)

        # ===== TÍTULO =====
        st.markdown(f"""
        <h1 style="text-align: center; color: #1a3a8a; font-family: Poppins, sans-serif; 
                   font-size: 36px; font-weight: 700; margin-bottom: 2rem;">
            Circuito {circuito.get('nombre', '')}
        </h1>
        """, unsafe_allow_html=True)
        
        # ===== CUADRÍCULA DE 6 MÓDULOS =====
        cols = st.columns(6)
        
        for i in range(1, 7):
            with cols[i - 1]:
                _renderizar_modulo_circuito(circuito, i)
        
        # ===== BOTÓN CERRAR =====
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Cerrar", key="cerrar_ver_circuito", use_container_width=True):
            st.session_state['mostrar_ver_circuito'] = False
            st.rerun()
    
    _dialog()

def _renderizar_modulo_circuito(circuito, num_modulo):
    """Renderiza un módulo individual con el diseño del circuito (sin interacción)"""
    
    nombre_modulo = circuito.get(f"modulo_{num_modulo}", "") or ""
    clave_caso = circuito.get(f"caso_{num_modulo}", "") or ""
    
    asignado = (
        nombre_modulo.strip() != ""
        and nombre_modulo.strip().lower() != "no asignar"
        and clave_caso.strip() != ""
    )
    
    tiene_modulo = (
        nombre_modulo.strip() != ""
        and nombre_modulo.strip().lower() != "no asignar"
    )
    
    # ===== TÍTULO DEL MÓDULO (arriba) =====
    st.markdown(f"""
    <div style="
        border: none;
        border-radius: 10px 10px 0 0;
        padding: 12px 5px;
        text-align: center;
        font-family: Poppins, sans-serif;
        font-size: 14px;
        font-weight: 600;
        background-color: white;
        margin-bottom: 0;
        min-height: 50px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    ">
        Área {num_modulo}
    </div>
    """, unsafe_allow_html=True)
    
    # ===== TARJETA DEBAJO =====
    if asignado:
        st.markdown(f"""
        <div style="
            background-color: {COLOR_ASIGNADO};
            padding: 15px 5px;
            text-align: center;
            font-family: Poppins, sans-serif;
            font-size: 12px;
            font-weight: 500;
            color: white;
            min-height: 80px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            line-height: 1.4;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        ">
            <div>{nombre_modulo}</div>
            <div style="margin-top: 5px; font-weight: 600;">{clave_caso}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # ===== NUEVO: BOTÓN DE DESCARGA DE PDF =====
        # Usamos keys únicas basadas en el ID del circuito y el módulo
        id_circuito = circuito.get('id', 'default')
        key_btn_pdf = f"btn_pdf_circuito_{id_circuito}_{num_modulo}"
        key_state_pdf = f"pdf_ready_{id_circuito}_{num_modulo}"
        key_bytes_pdf = f"pdf_bytes_{id_circuito}_{num_modulo}"
        
        # El botón se ve pequeño (font-size) para que quepa bien en la columna
        if st.button("PDF", key=key_btn_pdf, use_container_width=True):
            with st.spinner("Generando..."):
                try:
                    info_caso = cargar_info_caso(clave_caso)
                    if not info_caso:
                        st.error("No se cargó el caso")
                    else:
                        pdf_buffer = generar_pdf_caso(clave_caso, info_caso)
                        st.session_state[key_bytes_pdf] = pdf_buffer.getvalue()
                        st.session_state[key_state_pdf] = True
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        # Si el PDF ya se generó, mostramos el botón de descarga
        if st.session_state.get(key_state_pdf, False):
            # Intentamos obtener el nombre del caso para el archivo
            nombre_archivo = f"{clave_caso}_caso.pdf"
            if 'info_caso' in locals() and info_caso:
                nombre_caso = info_caso.get('nombre_caso', 'Caso')
                nombre_archivo = f"{clave_caso}_{nombre_caso.replace(' ', '_')}.pdf"
            
            st.download_button(
                label="⬇ Guardar",
                data=st.session_state[key_bytes_pdf],
                file_name=nombre_archivo,
                mime="application/pdf",
                key=f"download_{id_circuito}_{num_modulo}",
                use_container_width=True
            )
    
    elif tiene_modulo:
        st.markdown(f"""
        <div style="
            background-color: {COLOR_SIN_CASO};
            padding: 15px 5px;
            text-align: center;
            font-family: Poppins, sans-serif;
            font-size: 12px;
            font-weight: 500;
            color: white;
            min-height: 80px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        ">
            {nombre_modulo}
        </div>
        """, unsafe_allow_html=True)
    
    else:
        st.markdown(f"""
        <div style="
            background-color: {COLOR_VACIO};
            padding: 15px 5px;
            text-align: center;
            font-family: Poppins, sans-serif;
            font-size: 12px;
            font-weight: 500;
            color: #666;
            min-height: 80px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        ">
            No asignado
        </div>
        """, unsafe_allow_html=True)