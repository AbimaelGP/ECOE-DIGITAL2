# escenas/escena_historial_clinico.py
import streamlit as st
from datetime import datetime
from utils.casos import cargar_info_caso, obtener_sprite_url
from utils.actividad_estudiante import actualizar_actividad_estudiante
from utils.supabase_client import SUPABASE_URL

# Sprite genérico cuando el sprite está oculto
SPRITE_GENERICO = f"{SUPABASE_URL}/storage/v1/object/public/sprites/paciente_avatar.png"
TEXTO_OCULTO = "No disponible, no han sido recolectados."


def _aplicar_visibilidad(info):
    """Aplica la visibilidad a los datos del paciente"""
    visibilidad = info.get('visibilidad', {}) or {}
    
    def es_visible(campo):
        return visibilidad.get(campo, True)
    
    datos = {
        'nombre': info.get('nombre', 'Paciente') if es_visible('nombre') else TEXTO_OCULTO,
        'edad': info.get('edad', 'No especificada') if es_visible('edad') else TEXTO_OCULTO,
        'sexo': info.get('sexo', 'No especificado') if es_visible('sexo') else TEXTO_OCULTO,
        'motivo_consulta': info.get('motivo_consulta', 'No especificado') if es_visible('motivo_consulta') else TEXTO_OCULTO,
        'descripcion': info.get('descripcion', 'No disponible') if es_visible('descripcion') else TEXTO_OCULTO,
        'antecedentes': info.get('antecedentes', 'No disponibles') if es_visible('antecedentes') else TEXTO_OCULTO,
        'medicamentos_actuales': info.get('medicamentos_actuales', 'No refiere tratamiento actual') if es_visible('medicamentos_actuales') else TEXTO_OCULTO,
    }
    
    # Sprite
    if es_visible('sprite'):
        datos['sprite_url'] = info.get('sprite_url')
    else:
        datos['sprite_url'] = SPRITE_GENERICO
    
    return datos


def mostrar(caso_id, modulo_seleccionado, escena_destino="primer_modulo"):
    """
    Muestra el historial clínico del paciente (con visibilidad aplicada y soporte para 3 tipos de casos)
    """
    
    matricula = st.session_state['identificador']
    tiempo_inicio_examen = st.session_state.get('tiempo_inicio_examen', None)
    
    # Cargar información del caso
    info = cargar_info_caso(caso_id)
    
    # CSS
    st.markdown("""
    <style>
        .stApp {
            background: #F1F2F5;
        }
        .historial-titulo {
            color: #70257E;
            font-size: 36px;
            font-weight: 600;
            margin-bottom: 1.5rem;
            text-align: center;
        }
        .seccion-titulo {
            color: #70257E;
            font-size: 20px;
            font-weight: 600;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            border-bottom: 2px solid #70257E;
            display: inline-block;
        }
        .descripcion-texto {
            color: #303442;
            line-height: 1.5;
            text-align: justify;
            background-color: #FFFFFF;
            border-radius: 20px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .aviso {
            background-color: #FFFFFF;
            border-left: 4px solid #70257E;
            padding: 1rem;
            margin-top: 1.5rem;
            border-radius: 10px;
            color: #303442;
            font-size: 16px;
            text-align: center;
        }
        .stButton > button {
            background-color: #70257E;
            color: #FFFFFF;
            font-family: 'Poppins', sans-serif;
            font-weight: 500;
            padding: 0.75rem 2rem;
            border-radius: 10px;
            border: none;
            width: 250px;
        }
        .stButton > button:hover {
            background-color: #70257E;
        }
        .button-container {
            display: flex;
            justify-content: center;
            margin-top: 2rem;
            margin-bottom: 2rem;
        }
        .sprite-centrado {
            display: flex;
            justify-content: center;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Título
    st.markdown('<div class="historial-titulo">Historial clínico del Paciente</div>', unsafe_allow_html=True)
    
    texto_boton = "Continuar" # Valor por defecto por si falla la carga
    
    if info:
        # ===== APLICAR VISIBILIDAD =====
        datos = _aplicar_visibilidad(info)
        
        # Primera sección: Sprite y datos
        st.markdown('<div class="info-paciente">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 2])
        
        with col1:
            st.markdown('<div class="sprite-centrado">', unsafe_allow_html=True)
            
            # Usar el sprite ya filtrado por visibilidad
            if datos.get('sprite_url'):
                try:
                    st.image(datos['sprite_url'], width=200)
                except Exception as e:
                    print(f"Error al cargar sprite: {e}")
                    st.write("🖼️")
            else:
                st.write("🖼️")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<p><strong style="color: #252A38;">Nombre:</strong> {datos["nombre"]}</p>', unsafe_allow_html=True)
            edad_texto = f'{datos["edad"]} años' if datos['edad'] != TEXTO_OCULTO else datos['edad']
            st.markdown(f'<p><strong style="color: #252A38;">Edad:</strong> {edad_texto}</p>', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'<p><strong style="color: #252A38;">Sexo:</strong> {datos["sexo"]}</p>', unsafe_allow_html=True)
            st.markdown(f'<p><strong style="color: #252A38;">Motivo de consulta:</strong> {datos["motivo_consulta"]}</p>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Segunda sección: Descripción
        st.markdown('<div class="seccion-titulo">Descripción</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="descripcion-texto">{datos["descripcion"]}</div>', unsafe_allow_html=True)
        
        # Tercera sección: Antecedentes médicos
        st.markdown('<div class="seccion-titulo">Antecedentes médicos</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="descripcion-texto">{datos["antecedentes"]}</div>', unsafe_allow_html=True)
        
        # Cuarta sección: Medicamentos Actuales
        st.markdown('<div class="seccion-titulo">Medicamentos Actuales</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="descripcion-texto">{datos["medicamentos_actuales"]}</div>', unsafe_allow_html=True)
        
        # ===== QUINTA SECCIÓN: INSTRUCCIONES (SIEMPRE VISIBLES) =====
        instrucciones = info.get('instrucciones', {}) or {}
        instrucciones_caso = instrucciones.get('instrucciones_caso', '')
        
        if instrucciones_caso:
            st.markdown('<div class="seccion-titulo">Instrucciones para el caso</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="descripcion-texto">{instrucciones_caso}</div>', unsafe_allow_html=True)
        
     # ===== AVISO DINÁMICO SEGÚN EL TIPO DE CASO =====
        tipo_caso = info.get('tipo_caso', 'Paciente Virtual')
        
        if tipo_caso == "Paciente Virtual":
            texto_aviso = "Solo podrás comunicarte con el paciente virtual una ocasión. Toma el tiempo necesario para indagar.<br>Podrás solicitar estudios si consideras necesario para dar tu diagnóstico."
            texto_boton = "Continuar al chat"
        elif tipo_caso == "Paciente Estandarizado":
            texto_aviso = "El paciente estará presente en la sala. Realiza tu exploración clínica.<br>Podrás solicitar estudios si consideras necesario para dar tu diagnóstico."
            texto_boton = "Continuar con el paciente"
        else: # Estático
            texto_aviso = "Analiza el caso clínico presentado.<br>Podrás solicitar estudios si consideras necesario para dar tu diagnóstico."
            texto_boton = "Continuar al diagnóstico"

        # Usamos st.markdown directamente con unsafe_allow_html=True
        st.markdown(f"""
        <div class="aviso">
            {texto_aviso}
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.error(f"No se pudo cargar la información del caso {caso_id}")
    
     # Botón para continuar
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Usamos [1, 1, 1] para que coincida exactamente con el tamaño del botón de Cerrar sesión
    col1, col2, col3 = st.columns([2, 1.2, 2])
    with col2:
        if st.button(texto_boton, key="continuar_chat", use_container_width=True):            
            st.session_state['pagina'] = escena_destino
            st.rerun()