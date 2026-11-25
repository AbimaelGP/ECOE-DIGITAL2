# components/modal_historial.py
import streamlit as st
from utils.casos import cargar_info_caso
from utils.supabase_client import SUPABASE_URL

# URL del sprite genérico cuando el sprite está oculto
SPRITE_GENERICO = f"{SUPABASE_URL}/storage/v1/object/public/sprites/paciente_avatar.png"

TEXTO_OCULTO = "No disponible, no han sido recolectados."


def _normalizar_visibilidad(visibilidad):
    """Devuelve el dict de visibilidad aunque venga como texto JSON o None."""
    if isinstance(visibilidad, str):
        try:
            import json
            visibilidad = json.loads(visibilidad)
        except Exception:
            visibilidad = {}
    return visibilidad if isinstance(visibilidad, dict) else {}


def _valor_visible(valor):
    """Interpreta el flag de visibilidad: solo es visible si es verdadero.
    (False, 0, "false", "no", "0", "oculto" → oculto; ausente → visible)."""
    if valor is None:
        return True
    if isinstance(valor, str):
        return valor.strip().lower() not in ("false", "0", "no", "oculto", "f", "")
    return bool(valor)


# ==================== FUNCIONES AUXILIARES ====================

def _aplicar_visibilidad(info_caso):
    """Aplica la visibilidad a los datos del paciente (modo estudiante).
    Lo marcado como oculto NUNCA se devuelve: se sustituye por TEXTO_OCULTO."""
    visibilidad = _normalizar_visibilidad(info_caso.get('visibilidad'))
    
    def es_visible(campo):
        return _valor_visible(visibilidad.get(campo))
    
    datos = {
        'nombre': info_caso.get('nombre', 'No disponible') if es_visible('nombre') else TEXTO_OCULTO,
        'edad': info_caso.get('edad', 'No disponible') if es_visible('edad') else TEXTO_OCULTO,
        'sexo': info_caso.get('sexo', 'No disponible') if es_visible('sexo') else TEXTO_OCULTO,
        'motivo_consulta': info_caso.get('motivo_consulta', 'No disponible') if es_visible('motivo_consulta') else TEXTO_OCULTO,
        'descripcion': info_caso.get('descripcion', 'No disponible') if es_visible('descripcion') else TEXTO_OCULTO,
        'antecedentes': info_caso.get('antecedentes', 'No disponibles') if es_visible('antecedentes') else TEXTO_OCULTO,
        'medicamentos_actuales': info_caso.get('medicamentos_actuales', 'No refiere tratamiento actual') if es_visible('medicamentos_actuales') else TEXTO_OCULTO,
    }
    
    if es_visible('sprite'):
        datos['sprite_url'] = info_caso.get('sprite_url')
    else:
        datos['sprite_url'] = SPRITE_GENERICO
    
    return datos


def _aplicar_visibilidad_admin(info_caso):
    """
    Para el ADMIN: NO aplica visibilidad. Muestra todos los datos reales.
    Retorna también el diccionario de visibilidad para mostrar badges.
    """
    visibilidad = info_caso.get('visibilidad', {}) or {}
    
    return {
        'nombre': info_caso.get('nombre', 'No disponible'),
        'edad': info_caso.get('edad', 'No disponible'),
        'sexo': info_caso.get('sexo', 'No disponible'),
        'motivo_consulta': info_caso.get('motivo_consulta', 'No disponible'),
        'descripcion': info_caso.get('descripcion', 'No disponible'),
        'antecedentes': info_caso.get('antecedentes', 'No disponibles'),
        'medicamentos_actuales': info_caso.get('medicamentos_actuales', 'No refiere tratamiento actual'),
        'sprite_url': info_caso.get('sprite_url'),
        'visibilidad': visibilidad,
    }


def _renderizar_contenido_historial(info_caso, caso_paciente, incluir_clave=False, modo_admin=False):
    """
    Renderiza el contenido del historial clínico.
    - modo_admin=False: Aplica visibilidad (vista del estudiante)
    - modo_admin=True: Muestra todo + badges + guión + solución (vista del admin)
    """
    if not info_caso:
        st.warning(f"No se pudo cargar la información del caso {caso_paciente}")
        return
    
    # ===== APLICAR VISIBILIDAD SEGÚN EL MODO =====
    if modo_admin:
        datos = _aplicar_visibilidad_admin(info_caso)
        visibilidad = datos.get('visibilidad', {})
    else:
        datos = _aplicar_visibilidad(info_caso)
        visibilidad = {}
    
    # ===== SPRITE =====
    if datos.get('sprite_url'):
        try:
            st.image(datos['sprite_url'], width=150)
        except:
            pass
    
    # ===== CLAVE DEL CASO (solo si aplica) =====
    if incluir_clave:
        st.markdown(f"**Clave del caso:** {caso_paciente}")
        st.markdown(f"**Especialidad:** {info_caso.get('especialidad', 'No especificada')}")
        st.markdown("---")
    
    # ===== HELPER: renderizar campo con badge (modo admin) =====
    def render_campo(label, valor, campo_key=None):
        if modo_admin and campo_key:
            visible = visibilidad.get(campo_key, True)
            if visible:
                badge = ' <span style="background-color: #FFFFFF; color: #008A4B; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">VISIBLE</span>'
            else:
                badge = ' <span style="background-color: #f8d7da; color: #721c24; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">OCULTO</span>'
            st.markdown(f"**{label}:** {valor}{badge}", unsafe_allow_html=True)
        else:
            st.markdown(f"**{label}:** {valor}")
    
    # ===== DATOS DEL PACIENTE =====
    render_campo("Nombre", datos['nombre'], 'nombre')
    
    edad_texto = datos['edad']
    if edad_texto not in [TEXTO_OCULTO, 'No disponible', 'No especificada']:
        edad_texto = f"{edad_texto} años"
    render_campo("Edad", edad_texto, 'edad')
    
    render_campo("Sexo", datos['sexo'], 'sexo')
    render_campo("Motivo de consulta", datos['motivo_consulta'], 'motivo_consulta')
    
    st.markdown("---")
    render_campo("Descripción", datos['descripcion'], 'descripcion')
    
    st.markdown("---")
    render_campo("Antecedentes", datos['antecedentes'], 'antecedentes')
    
    st.markdown("---")
    render_campo("Medicamentos actuales", datos['medicamentos_actuales'], 'medicamentos_actuales')
    
    # ===== INSTRUCCIONES DEL CASO (siempre visibles para el estudiante) =====
    instrucciones = info_caso.get('instrucciones', {}) or {}
    instrucciones_caso = instrucciones.get('instrucciones_caso', '')
    
    if instrucciones_caso:
        st.markdown("---")
        if modo_admin:
            st.markdown("**Instrucciones para el caso:** (siempre visible)")
        else:
            st.markdown("**Instrucciones para el caso:**")
        st.markdown(instrucciones_caso)
    
    # ===== EXTRA PARA ADMIN: guión y solución =====
    if modo_admin:
        guion_paciente = instrucciones.get('guion_paciente', '')
        if guion_paciente:
            st.markdown("---")
            st.markdown("**Guión del paciente:** (siempre oculto para el estudiante)")
            st.markdown(guion_paciente)
        
        solucion = info_caso.get('solucion', {}) or {}
        if solucion:
            st.markdown("---")
            st.markdown("### Solución del Caso")
            st.markdown("*(siempre oculta para el estudiante)*")
            
            if solucion.get('diagnostico_correcto'):
                st.markdown(f"**Diagnóstico correcto:** {solucion['diagnostico_correcto']}")
            if solucion.get('diagnostico_alternativo'):
                st.markdown(f"**Diagnóstico alternativo:** {solucion['diagnostico_alternativo']}")
            if solucion.get('tratamiento_esperado'):
                st.markdown(f"**Tratamiento esperado:** {solucion['tratamiento_esperado']}")
            if solucion.get('errores_criticos'):
                st.markdown(f"**Errores críticos:** {solucion['errores_criticos']}")
            if solucion.get('rubrica_url'):
                st.markdown(f"[Ver rúbrica]({solucion['rubrica_url']})")
            
            preguntas = solucion.get('preguntas', [])
            if preguntas:
                st.markdown("**Preguntas de evaluación:**")
                for i, p in enumerate(preguntas, 1):
                    st.markdown(f"{i}. {p.get('pregunta', '')}")
                    st.caption(f"   Respuesta esperada: {p.get('respuesta_esperada', '')}")


# ==================== MODALES ====================

def mostrar_historial_dialog(info_caso, caso_paciente, key_suffix, titulo="Historial Clínico del Paciente", modo_admin=False):
    """Muestra un diálogo con el historial clínico del paciente"""
    
    dialog_key = f"historial_dialog_{key_suffix}"
    
    @st.dialog(titulo, width="large")
    def _dialog():
        # ===== OCULTAR LA X SOLO EN MODO ADMIN (para forzar el uso del botón) =====
        # En modo estudiante, dejamos la X visible para que puedan cerrar sin bugs
        if modo_admin:
            st.markdown("""
            <style>
                div[data-testid="stDialog"] button[aria-label="Close"] {
                    display: none !important;
                }
            </style>
            """, unsafe_allow_html=True)
        
        _renderizar_contenido_historial(
            info_caso, caso_paciente,
            incluir_clave=False,
            modo_admin=modo_admin
        )
        
        # ===== BOTÓN CERRAR SOLO EN MODO ADMIN =====
        # En modo estudiante NO mostramos botón (usan la X nativa)
        if modo_admin:
            if st.button("Cerrar", key=f"cerrar_historial_{key_suffix}", use_container_width=True):
                st.session_state[dialog_key] = False
                st.rerun()
    
    _dialog()


def boton_ver_historial(info_caso, caso_paciente, key_suffix, modo_admin=False):
    """Muestra el botón para ver el historial clínico"""
    
    dialog_key = f"historial_dialog_{key_suffix}"
    
    if dialog_key not in st.session_state:
        st.session_state[dialog_key] = False
    
    # ===== BOTÓN PARA ABRIR =====
    if st.button("Ver Historial Clínico", key=f"btn_historial_{key_suffix}", use_container_width=True):
        st.session_state[dialog_key] = True
        st.rerun()
    
    # ===== MOSTRAR MODAL SI ESTÁ ACTIVO =====
    if st.session_state.get(dialog_key, False):
        mostrar_historial_dialog(
            info_caso, caso_paciente, key_suffix,
            modo_admin=modo_admin
        )


def ver_caso_modal(clave_caso, key_suffix, dentro_formulario=False, modo_admin=False):
    """
    Función para ver un caso específico en un modal.
    - dentro_formulario: usa form_submit_button si True
    - modo_admin: si True, muestra todo (para admins)
    """
    
    info_caso = cargar_info_caso(clave_caso)
    
    if not info_caso:
        st.warning(f"No se pudo cargar el caso {clave_caso}")
        return
    
    dialog_key = f"ver_caso_dialog_{key_suffix}"
    
    if dialog_key not in st.session_state:
        st.session_state[dialog_key] = False
    
    # ===== BOTÓN PARA ABRIR =====
    if dentro_formulario:
        if st.form_submit_button("Ver caso", key=f"btn_ver_caso_{key_suffix}"):
            st.session_state[dialog_key] = True
            st.rerun()
    else:
        if st.button("Ver caso", key=f"btn_ver_caso_{key_suffix}", use_container_width=True):
            st.session_state[dialog_key] = True
            st.rerun()
    
    # ===== MOSTRAR MODAL SI ESTÁ ACTIVO =====
    if st.session_state.get(dialog_key, False):
        
        @st.dialog(f"Caso: {clave_caso}", width="large")
        def _ver_caso_dialog():
            # ===== OCULTAR LA X SOLO EN MODO ADMIN =====
            if modo_admin:
                st.markdown("""
                <style>
                    div[data-testid="stDialog"] button[aria-label="Close"] {
                        display: none !important;
                    }
                </style>
                """, unsafe_allow_html=True)
            
            _renderizar_contenido_historial(
                info_caso, clave_caso,
                incluir_clave=True,
                modo_admin=modo_admin
            )
            
            # ===== BOTÓN CERRAR SOLO EN MODO ADMIN =====
            if modo_admin:
                if st.button("Cerrar", key=f"cerrar_ver_caso_{key_suffix}", use_container_width=True):
                    st.session_state[dialog_key] = False
                    st.rerun()
        
        _ver_caso_dialog()