# components/modal_estudios.py
import streamlit as st
from pathlib import Path
from utils.estudios import listar_estudios_disponibles, obtener_valores_estudio, estudio_tiene_imagen, obtener_imagen_estudio
from utils.supabase_client import supabase, SUPABASE_URL


def mostrar_modal_estudios(caso_paciente, matricula, tiempo_inicio_examen_global, modulo_seleccionado, escena="primer_modulo"):
    """Muestra el panel de estudios"""
    
    # CSS específico para hacer que este panel se vea secundario
    st.markdown("""
    <style>
        .titulo-secundario {
            font-size: 22px !important;
            font-weight: 600 !important;
            color: #252A38 !important;
            margin-bottom: 1rem !important;
            border-bottom: 2px solid #E5E7EC;
            padding-bottom: 0.5rem;
        }
        .subtitulo-panel {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #303442 !important;
            margin-top: 1rem !important;
            margin-bottom: 0.5rem !important;
        }
        .texto-estudio {
            font-size: 14px !important;
            color: #626779 !important;
        }
        .resultado-titulo {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #252A38 !important;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)

    key_estudios = f'estudios_solicitados_{escena}_{modulo_seleccionado}'
    if key_estudios not in st.session_state:
        st.session_state[key_estudios] = []
    
    estudios_disponibles = listar_estudios_disponibles(caso_paciente)
    estudios_solicitados = st.session_state[key_estudios]
    
    # Título con clase CSS personalizada (más pequeño)
    st.markdown('<div class="titulo-secundario">Panel de Estudios</div>', unsafe_allow_html=True)
    
    if estudios_solicitados:
        st.markdown('<div class="subtitulo-panel">Estudios ya solicitados:</div>', unsafe_allow_html=True)
        for estudio in estudios_solicitados:
            st.markdown(f'<div class="texto-estudio">• {estudio}</div>', unsafe_allow_html=True)
        st.markdown("---")
    
    # ===== VALIDACIÓN: SI EL CASO NO TIENE ESTUDIOS CARGADOS =====
    if not estudios_disponibles:
        st.warning("No hay estudios disponibles para este caso.")
    else:
        # ===== SIN LÍMITE: mostrar todos los estudios que aún no se solicitan =====
        opciones = [e for e in estudios_disponibles if e not in estudios_solicitados]
        
        if opciones:
            with st.form(key=f"form_estudios_{escena}_{modulo_seleccionado}"):
                estudio_seleccionado = st.selectbox("Selecciona un estudio:", opciones)
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Solicitar Estudio", use_container_width=True)
                with col2:
                    cancelar = st.form_submit_button("Cerrar Panel", use_container_width=True)
                
                if submitted:
                    st.session_state[key_estudios].append(estudio_seleccionado)
                    # Guardar como evidencia para el médico evaluador (no afecta si falla)
                    try:
                        from utils.guardar_historial import guardar_estudios_solicitados
                        guardar_estudios_solicitados(matricula, modulo_seleccionado, caso_paciente,
                                                     st.session_state[key_estudios])
                    except Exception as e:
                        print(f"⚠️ No se guardaron los estudios solicitados: {e}")
                    st.rerun()
                
                if cancelar:
                    st.session_state[f'modal_estudios_abierto_{escena}_{modulo_seleccionado}'] = False
                    st.rerun()
        else:
            st.success("Ya has solicitado todos los estudios disponibles.")
            if st.button("Cerrar Panel", key=f"cerrar_{escena}_{modulo_seleccionado}", use_container_width=True):
                st.session_state[f'modal_estudios_abierto_{escena}_{modulo_seleccionado}'] = False
                st.rerun()
    
    # ===== MOSTRAR RESULTADOS DE ESTUDIOS =====
    if estudios_solicitados:
        st.markdown("---")
        st.markdown('<div class="titulo-secundario">Resultados de estudios</div>', unsafe_allow_html=True)
        
        for estudio in estudios_solicitados:
            with st.container():
                st.markdown(f'<div class="resultado-titulo">{estudio}</div>', unsafe_allow_html=True)
                
                # 1. OBTENER DATOS DEL ESTUDIO
                datos_estudio = obtener_valores_estudio(caso_paciente, estudio)
                
                if datos_estudio:
                    es_imagen = datos_estudio.get('tipo') == 'imagen'
                    
                    if es_imagen:
                        url_imagen = datos_estudio.get('imagen_url')
                        if url_imagen:
                            try:
                                st.image(url_imagen, width=350) # Un poco más pequeña la imagen
                            except Exception as e:
                                st.error(f"No se pudo cargar la imagen: {e}")
                        else:
                            st.info("No hay imagen disponible para este estudio")
                    
                    # 3. MOSTRAR PARÁMETROS con letra más chica
                    parametros = datos_estudio.get('parametros', {})
                    if parametros:
                        for parametro, datos in parametros.items():
                            valor = datos.get('valor', 'N/A')
                            unidad = datos.get('unidad', '')
                            st.markdown(f'<div class="texto-estudio"><b>{parametro}:</b> <i>{valor} {unidad}</i></div>', unsafe_allow_html=True)
                else:
                    st.warning(f"No hay datos disponibles para {estudio}")
            
            st.markdown("---")


def abrir_modal_estudios(escena="primer_modulo", modulo_seleccionado=1):
    """Abre el panel de estudios"""
    st.session_state[f'modal_estudios_abierto_{escena}_{modulo_seleccionado}'] = True


def limpiar_estudios_solicitados(escena="primer_modulo", modulo_seleccionado=1):
    """Limpia la lista de estudios solicitados"""
    key_estudios = f'estudios_solicitados_{escena}_{modulo_seleccionado}'
    if key_estudios in st.session_state:
        del st.session_state[key_estudios]
    
    modal_key = f'modal_estudios_abierto_{escena}_{modulo_seleccionado}'
    if modal_key in st.session_state:
        del st.session_state[modal_key]