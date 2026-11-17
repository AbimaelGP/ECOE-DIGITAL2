# escenas/escena_modulo.py
import streamlit as st
from utils.database import obtener_datos_estudiante, actualizar_estatus_estudiante
from utils.casos import cargar_info_caso, obtener_sprite_url
from utils.actividad_estudiante import actualizar_actividad_estudiante
from datetime import datetime, timedelta
from utils.horario import ahora as ahora_local
from utils.supabase_client import SUPABASE_URL


# ==================== FRAGMENTO DEL TEMPORIZADOR ====================

@st.fragment(run_every=1)
def mostrar_temporizador_flotante(modulo_seleccionado):
    """Fragmento que se actualiza cada segundo mostrando el temporizador en un modal flotante."""
    
    clave_limite = f'tiempo_limite_modulo_{modulo_seleccionado}'
    
    if clave_limite not in st.session_state:
        return
    
    tiempo_limite = st.session_state[clave_limite]
    ahora = ahora_local()
    tiempo_restante = (tiempo_limite - ahora).total_seconds()
    
    if tiempo_restante < 0:
        tiempo_restante = 0
    
    # Guardar el tiempo restante en la base (cada pocos segundos) para poder retomar tras un error
    try:
        from utils.progreso_examen import latido
        latido(st.session_state.get('identificador'), modulo_seleccionado, tiempo_restante)
    except Exception:
        pass
    
    minutos = int(tiempo_restante // 60)
    segundos = int(tiempo_restante % 60)
    
    if tiempo_restante <= 60:
        color = "#dc3545"
    elif tiempo_restante <= 300:
        color = "#ffc107"
    else:
        color = "#008A4B"
    
    porcentaje = min(100, max(0, (tiempo_restante / 600) * 100))
    hora_limite_str = tiempo_limite.strftime("%H:%M:%S")
    
    modal_html = f"""
    <style>
        #temporizador-modal-flotante {{
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 9999;
            background-color: #FFFFFF;
            border: 3px solid {color};
            border-radius: 12px;
            padding: 15px 25px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            font-family: 'Poppins', sans-serif;
            text-align: center;
            min-width: 200px;
            transition: border-color 0.3s ease;
        }}
        #temporizador-modal-flotante .titulo {{
            font-size: 12px; color: #626779; font-weight: 500; margin-bottom: 5px;
            letter-spacing: 1px; text-transform: uppercase;
        }}
        #temporizador-modal-flotante .tiempo {{
            font-size: 32px; font-weight: 700; color: {color};
            font-variant-numeric: tabular-nums; transition: color 0.3s ease;
        }}
        #temporizador-modal-flotante .limite {{
            font-size: 11px; color: #626779; margin-top: 5px;
        }}
        #temporizador-modal-flotante .barra {{
            width: 100%; height: 6px; background-color: #E5E7EC;
            border-radius: 3px; margin-top: 10px; overflow: hidden;
        }}
        #temporizador-modal-flotante .barra-interna {{
            height: 100%; background-color: {color}; width: {porcentaje}%;
            border-radius: 3px; transition: width 1s linear, background-color 0.3s ease;
        }}
    </style>
    <div id="temporizador-modal-flotante">
        <div class="titulo">Tiempo restante</div>
        <div class="tiempo">{minutos}:{segundos:02d}</div>
        <div class="limite">Límite: {hora_limite_str}</div>
        <div class="barra"><div class="barra-interna"></div></div>
    </div>
    """
    st.markdown(modal_html, unsafe_allow_html=True)


# ==================== FUNCIÓN AUXILIAR: VISIBILIDAD ====================

def _aplicar_visibilidad_escena(info_caso):
    """Aplica la visibilidad a los datos del paciente para la escena del módulo."""
    if not info_caso:
        return {}
    
    visibilidad = info_caso.get('visibilidad', {}) or {}
    
    def es_visible(campo):
        return visibilidad.get(campo, True)
    
    SPRITE_GENERICO = f"{SUPABASE_URL}/storage/v1/object/public/sprites/paciente_avatar.png"
    TEXTO_OCULTO = "No disponible."
    
    datos = {
        'nombre': info_caso.get('nombre', 'No disponible') if es_visible('nombre') else TEXTO_OCULTO,
        'edad': info_caso.get('edad', 'No disponible') if es_visible('edad') else TEXTO_OCULTO,
        'sexo': info_caso.get('sexo', 'No disponible') if es_visible('sexo') else TEXTO_OCULTO,
        'motivo_consulta': info_caso.get('motivo_consulta', 'No disponible') if es_visible('motivo_consulta') else TEXTO_OCULTO,
    }
    
    if es_visible('sprite'):
        datos['sprite_url'] = info_caso.get('sprite_url')
    else:
        datos['sprite_url'] = SPRITE_GENERICO
    
    return datos


# ==================== FUNCIÓN AUXILIAR: OBTENER INFO DEL MÓDULO ====================

def _obtener_info_modulo(matricula, modulo_seleccionado):
    """Obtiene el nombre y caso del módulo desde los datos del estudiante."""
    datos = obtener_datos_estudiante(matricula)
    
    if not datos:
        return "Área", ""
    
    modulos = datos.get('modulos', [])
    modulo_info = next((m for m in modulos if m['numero'] == modulo_seleccionado), None)
    
    if modulo_info:
        return modulo_info.get('nombre', 'Área'), modulo_info.get('caso', '')
    
    return "Área", ""


# ==================== FUNCIÓN PRINCIPAL ====================

def mostrar():
    """Muestra el módulo activo (funciona para cualquier módulo 1-6 y tipo de caso)"""
    
    # Importaciones locales para evitar el import circular
    from components.modal_estudios import abrir_modal_estudios, limpiar_estudios_solicitados, mostrar_modal_estudios
    from components.modal_diagnostico import abrir_modal_diagnostico, limpiar_diagnostico, mostrar_modal_diagnostico
    from components.modal_historial import _renderizar_contenido_historial
    
    matricula = st.session_state['identificador']
    tiempo_inicio_examen_global = st.session_state.get('tiempo_inicio_examen', None)
    modulo_seleccionado = st.session_state.get('modulo_seleccionado', 1)
    escena_key = f"modulo_{modulo_seleccionado}"
    
    # ===== LIMPIAR EL MODAL DE HISTORIAL (A PRUEBA DE BUGS) =====
    claves_a_limpiar = [
        f'historial_dialog_{escena_key}',
        f'ver_caso_dialog_{escena_key}',
        'show_historial_dialog'
    ]
    for clave in claves_a_limpiar:
        if clave in st.session_state:
            del st.session_state[clave]
    
    # ===== OBTENER INFO DEL MÓDULO (nombre y caso) =====
    nombre_modulo, caso_paciente = _obtener_info_modulo(matricula, modulo_seleccionado)
    
    if not caso_paciente:
        caso_paciente = st.session_state.get('caso_seleccionado', '')
    
    if not caso_paciente:
        st.error(f"No se encontró el caso para el área {modulo_seleccionado}")
        if st.button("Volver a selección"):
            st.session_state['pagina'] = 'seleccion_a'
            st.rerun()
        return
    
    st.session_state['caso_seleccionado'] = caso_paciente
    
    info_caso = cargar_info_caso(caso_paciente)
    tipo_caso = info_caso.get('tipo_caso', 'Paciente Virtual') if info_caso else 'Paciente Virtual'
    
    actualizar_actividad_estudiante(matricula, "Resolviendo modulo", modulo=modulo_seleccionado)
    
    # ===== CLAVES DINÁMICAS DEL TIMER =====
    clave_tiempo_inicio = f'tiempo_inicio_modulo_{modulo_seleccionado}'
    clave_tiempo_limite = f'tiempo_limite_modulo_{modulo_seleccionado}'
    clave_entrada = f'entrada_registrada_modulo_{modulo_seleccionado}'
    
    from utils import progreso_examen
    if clave_tiempo_inicio not in st.session_state:
        st.session_state[clave_tiempo_inicio] = ahora_local()
        st.session_state[clave_tiempo_limite] = ahora_local() + timedelta(minutes=10)
        progreso_examen.entrar_area(matricula, modulo_seleccionado, caso_paciente)
    
    tiempo_inicio = st.session_state[clave_tiempo_inicio]
    tiempo_limite = st.session_state[clave_tiempo_limite]
    ahora = ahora_local()
    
    # ===== VALIDACIÓN DE TIEMPO AGOTADO =====
    tiempo_restante = (tiempo_limite - ahora).total_seconds()
    if tiempo_restante <= 0:
        from utils.guardar_historial import guardar_historial_chat
        guardar_historial_chat(matricula, modulo_seleccionado, caso_paciente)
        
        for key in [clave_tiempo_inicio, clave_tiempo_limite, clave_entrada]:
            if key in st.session_state:
                del st.session_state[key]
        
        limpiar_estudios_solicitados(escena_key, modulo_seleccionado)
        limpiar_diagnostico(escena_key, modulo_seleccionado)
        
        if 'modulos_completados' not in st.session_state:
            st.session_state['modulos_completados'] = {}
        st.session_state['modulos_completados'][modulo_seleccionado] = True
        progreso_examen.terminar_area(matricula, modulo_seleccionado)
        # (Antes aquí se marcaba todo el examen como 'Finalizado' al agotarse UNA área; ahora se
        #  marca al terminar el examen completo, en la pantalla final.)
        
        st.session_state['pagina'] = 'seleccion_a'
        st.rerun()
        return
    
    # Guarda el tiempo restante para poder retomar si hay un error (cada pocos segundos)
    progreso_examen.latido(matricula, modulo_seleccionado, tiempo_restante)
    
    # ===== DATOS VISIBLES =====
    datos_visibles = _aplicar_visibilidad_escena(info_caso)
    
    sprite_url = datos_visibles.get('sprite_url')
    if not sprite_url:
        sprite_url = f"{SUPABASE_URL}/storage/v1/object/public/sprites/placeholder.png"
    
    # ===== CSS GLOBAL =====
    st.markdown("""
    <style>
        .stApp { background: #F1F2F5; }
        .stButton > button { background-color: #70257E; color: #FFFFFF; font-family: 'Poppins', sans-serif; font-weight: 500; padding: 0.75rem 1.5rem; border-radius: 10px; border: none; }
        .stButton > button:hover { background-color: #70257E; }
        
        .chat-message { display: flex; margin: 0.5rem 0; align-items: flex-start; }
        .chat-message-user { justify-content: flex-end; }
        .chat-message-bot { justify-content: flex-start; }
        .bubble-user { background-color: #70257E; color: #FFFFFF; border-radius: 20px 4px 20px 20px; padding: 0.5rem 1rem; max-width: 70%; font-size: 14px; line-height: 1.4; }
        .bubble-bot { background-color: #E5E7EC; color: #303442; border-radius: 4px 20px 20px 20px; padding: 0.5rem 1rem; max-width: 70%; font-size: 14px; line-height: 1.4; }
        .avatar-img { width: 40px; height: 40px; border-radius: 50%; margin: 0 0.5rem; flex-shrink: 0; object-fit: cover; border: 2px solid #E5E7EC; }
        
        /* Forzar la visibilidad del botón de Rerun */
        header[data-testid="stHeader"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ===== INFO DEL ESTUDIANTE =====
    nombre = st.session_state['nombre']
    
    st.markdown(f"""
    <div style="margin-top: 1rem; margin-bottom: 2rem;">
        <p style="color: #252A38; font-family: Poppins; font-size: 28px; font-weight: 600; margin: 0;">{nombre}</p>
        <p style="color: #252A38; font-family: Poppins; font-size: 24px; font-weight: 600; margin-top: 0.5rem;">Área {modulo_seleccionado}: {nombre_modulo}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== TIMER FLOTANTE =====
    mostrar_temporizador_flotante(modulo_seleccionado)
    
    # ===== ADVERTENCIA SI EL TIEMPO ES BAJO =====
    minutos_restantes = int(tiempo_restante // 60)
    if tiempo_restante <= 300:
        if tiempo_restante <= 60:
            st.warning(f"Quedan {int(tiempo_restante)} segundos para finalizar el área.")
        elif tiempo_restante <= 180:
            st.info(f"Quedan {minutos_restantes} minutos para finalizar el área.")
    
    # =========================================================================
    # VISTA PARA PACIENTE VIRTUAL (Con Chat y Sidebar)
    # =========================================================================
    if tipo_caso == "Paciente Virtual":
        
        # Barra lateral con el historial
        with st.sidebar:
            _renderizar_contenido_historial(
                info_caso, 
                caso_paciente, 
                incluir_clave=False, 
                modo_admin=False
            )
        
        # Chat en el área central
        st.markdown("### Chat con el Paciente")
        
        chat_key = f"chat_{caso_paciente}"
        audio_key = f'audio_{caso_paciente}'
        
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []
        
        chat_container = st.container(height=550, border=True)
        
        with chat_container:
            url_avatar_paciente = f"{SUPABASE_URL}/storage/v1/object/public/sprites/paciente_avatar.png"
            url_avatar_doctor = f"{SUPABASE_URL}/storage/v1/object/public/sprites/doctor_avatar.png"
            
            if len(st.session_state[chat_key]) == 0:
                st.markdown(f"""
                <div class="chat-message chat-message-bot">
                    <img src="{url_avatar_paciente}" class="avatar-img" />
                    <div class="bubble-bot">Hola Dr. Gracias por atenderme.</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                total_mensajes = len(st.session_state[chat_key])
                for i, msg in enumerate(st.session_state[chat_key]):
                    if msg["role"] == "assistant":
                        st.markdown(f"""
                        <div class="chat-message chat-message-bot">
                            <img src="{url_avatar_paciente}" class="avatar-img" />
                            <div class="bubble-bot">{msg["content"]}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if i == total_mensajes - 1 and audio_key in st.session_state and st.session_state[audio_key]:
                            st.audio(st.session_state[audio_key], format="audio/wav", autoplay=True)
                    else:
                        st.markdown(f"""
                        <div class="chat-message chat-message-user">
                            <div class="bubble-user">{msg["content"]}</div>
                            <img src="{url_avatar_doctor}" class="avatar-img" />
                        </div>
                        """, unsafe_allow_html=True)
        
        # Input del chat
        with st.form(key=f"chat_form_{caso_paciente}", clear_on_submit=True):
            col_input, col_submit = st.columns([5, 1])
            with col_input:
                pregunta = st.text_input(
                    "Escribe tu mensaje...",
                    key=f"chat_input_{caso_paciente}",
                    placeholder="Escribe tu pregunta al paciente...",
                    label_visibility="collapsed"
                )
            with col_submit:
                enviar = st.form_submit_button("Enviar")
            
            if enviar and pregunta:
                if (tiempo_limite - ahora_local()).total_seconds() <= 0:
                    st.error("El tiempo del área ha expirado. Serás redirigido al inicio.")
                    st.session_state['pagina'] = 'inicio_estudiante'
                    st.rerun()
                
                st.session_state[chat_key].append({"role": "user", "content": pregunta, "hora": ahora_local().isoformat()})
                
                from chatbot.adaptador_bot import responder_como_paciente
                from chatbot.prompt_constructor import crear_prompt_paciente
                
                prompt_key = f"prompt_{caso_paciente}"
                if prompt_key not in st.session_state:
                    st.session_state[prompt_key] = crear_prompt_paciente(caso_paciente)
                
                prompt = st.session_state[prompt_key]
                
                historial_para_ia = []
                for msg in st.session_state[chat_key]:
                    if msg["role"] == "user":
                        historial_para_ia.append({"role": "user", "content": msg["content"]})
                    else:
                        historial_para_ia.append({"role": "model", "content": msg["content"]})
                
                if len(historial_para_ia) <= 1:
                    historial_para_ia = None
                
                respuesta = responder_como_paciente(pregunta, prompt, historial_para_ia)
                
                st.session_state[chat_key].append({"role": "assistant", "content": respuesta, "hora": ahora_local().isoformat()})
                
                try:
                    from utils.voz_paciente import generar_audio_paciente
                    audio_bytes = generar_audio_paciente(respuesta, info_caso)
                    st.session_state[audio_key] = audio_bytes
                except Exception as e:
                    print(f"Error generando audio: {e}")
                
                from utils.guardar_historial import guardar_historial_chat
                guardar_historial_chat(matricula, modulo_seleccionado, caso_paciente)
                
                st.rerun()

        # =========================================================================
    # VISTA PARA PACIENTE ESTÁTICO O ESTANDARIZADO (Historial Completo al Centro)
    # =========================================================================
    else:
        # Ocultar la barra lateral (si existía)
        st.markdown(
            """
            <style>
                [data-testid="stSidebar"] {display: none;}
                [data-testid="collapsedControl"] {display: none;}
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        # Renderizamos el expediente formal
        _renderizar_ficha_estatica(info_caso, datos_visibles, sprite_url)           

    # ===== BOTONES DE ESTUDIOS Y DIAGNÓSTICO =====
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Pedir Estudios", key=f"pedir_estudios_m{modulo_seleccionado}", use_container_width=True):
                abrir_modal_estudios(escena_key, modulo_seleccionado)
                st.session_state['desplazar_a'] = 'panel-estudios'
                st.rerun()
        with col_b:
            if st.button("Responder preguntas", key=f"dar_diagnostico_m{modulo_seleccionado}", use_container_width=True):
                abrir_modal_diagnostico(escena_key, modulo_seleccionado)
                progreso_examen.marcar_preguntas(matricula, True)
                st.session_state['desplazar_a'] = 'panel-diagnostico'
                st.rerun()
    
    # ===== MODAL DE ESTUDIOS =====
    modal_key_estudios = f'modal_estudios_abierto_{escena_key}_{modulo_seleccionado}'
    if st.session_state.get(modal_key_estudios, False):
        st.markdown("---")
        st.markdown('<div id="panel-estudios"></div>', unsafe_allow_html=True)
        mostrar_modal_estudios(caso_paciente, matricula, tiempo_inicio_examen_global, modulo_seleccionado, escena_key)
    
    # ===== MODAL DE DIAGNÓSTICO =====
    modal_key_diagnostico = f'modal_diagnostico_abierto_{escena_key}_{modulo_seleccionado}'
    if st.session_state.get(modal_key_diagnostico, False):
        st.markdown("---")
        st.markdown('<div id="panel-diagnostico"></div>', unsafe_allow_html=True)
        mostrar_modal_diagnostico(caso_paciente, matricula, tiempo_inicio_examen_global, modulo_seleccionado, escena_key)

    # ===== LLEVAR LA VISTA AL PANEL RECIÉN ABIERTO (estaba quedando fuera de pantalla, bajo el chat) =====
    destino = st.session_state.pop('desplazar_a', None)
    if destino:
        import streamlit.components.v1 as components
        components.html(f"""
            <script>
              const irA = () => {{
                const el = window.parent.document.getElementById("{destino}");
                if (el) {{ el.scrollIntoView({{behavior: "smooth", block: "start"}}); return true; }}
                return false;
              }};
              let intentos = 0;
              const t = setInterval(() => {{ if (irA() || ++intentos > 20) clearInterval(t); }}, 150);
            </script>""", height=0)

    # ===== TERMINAR MÓDULO DESPUÉS DEL DIAGNÓSTICO =====
    if st.session_state.get('terminar_modulo_despues_diagnostico', False):
        st.session_state['terminar_modulo_despues_diagnostico'] = False
        
        ahora_verificacion = ahora_local()
        termino_fuera_tiempo = ahora_verificacion >= tiempo_limite
        
        from utils.guardar_historial import guardar_historial_chat
        guardar_historial_chat(matricula, modulo_seleccionado, caso_paciente)
        
        for key in [clave_tiempo_inicio, clave_tiempo_limite, clave_entrada]:
            if key in st.session_state:
                del st.session_state[key]
        
        limpiar_estudios_solicitados(escena_key, modulo_seleccionado)
        limpiar_diagnostico(escena_key, modulo_seleccionado)
        
        if 'modulos_completados' not in st.session_state:
            st.session_state['modulos_completados'] = {}
        st.session_state['modulos_completados'][modulo_seleccionado] = True
        progreso_examen.terminar_area(matricula, modulo_seleccionado)
        
        st.session_state['pagina'] = 'seleccion_a'
        st.rerun()

def _renderizar_ficha_estatica(info_caso, datos_visibles, sprite_url):
    """Renderiza el expediente clínico completo para casos estáticos/estandarizados."""
    
    if not info_caso:
        return

    # ===== DATOS GENERALES EN 2 COLUMNAS (Sprite + Info) =====
    col_sprite, col_info = st.columns([1, 4])
    
    with col_sprite:
        try:
            st.image(sprite_url, width=140)
        except:
            st.markdown('<div style="text-align: center; font-size: 50px;">👤</div>', unsafe_allow_html=True)
            
    with col_info:
        nombre = datos_visibles.get('nombre', 'No disponible')
        edad = datos_visibles.get('edad', 'No disponible')
        sexo = datos_visibles.get('sexo', 'No disponible')
        motivo = datos_visibles.get('motivo_consulta', 'No disponible')
        
        if edad not in ["No disponible.", "No disponible"]:
            edad = f"{edad} años"

        st.markdown(f"""
        <div style="margin-top: 1rem;">
            <p style="margin-bottom: 0.5rem; font-size: 16px;"><span style="font-weight: 600; color: #252A38;">Nombre:</span> {nombre}</p>
            <p style="margin-bottom: 0.5rem; font-size: 16px;"><span style="font-weight: 600; color: #252A38;">Edad:</span> {edad} &nbsp;&nbsp;&nbsp;&nbsp; <span style="font-weight: 600; color: #252A38;">Sexo:</span> {sexo}</p>
            <p style="margin-bottom: 0.5rem; font-size: 16px;"><span style="font-weight: 600; color: #252A38;">Motivo de consulta:</span> {motivo}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

    # ===== RESTO DE LA INFORMACIÓN (Texto principal) =====
    visibilidad = info_caso.get('visibilidad', {}) or {}
    def visible(campo): return visibilidad.get(campo, True)
    
    # Función auxiliar para imprimir secciones con estilo
    def render_seccion(titulo, texto):
        if texto:
            st.markdown(f"""
            <div style="margin-bottom: 1.5rem;">
                <h4 style="color: #70257E; margin-bottom: 0.5rem; font-size: 18px;">{titulo}</h4>
                <p style="font-size: 16px; line-height: 1.6; color: #303442; text-align: justify;">{texto}</p>
            </div>
            """, unsafe_allow_html=True)

    if visible('descripcion'):
        render_seccion("Descripción", info_caso.get('descripcion'))
        
    if visible('antecedentes'):
        render_seccion("Antecedentes", info_caso.get('antecedentes'))
        
    if visible('medicamentos_actuales'):
        render_seccion("Medicamentos Actuales", info_caso.get('medicamentos_actuales'))
        
    instrucciones = info_caso.get('instrucciones', {}) or {}
    if instrucciones.get('instrucciones_caso'):
        st.markdown("---")
        st.info(f"**Instrucciones para el caso:**\n{instrucciones.get('instrucciones_caso')}")