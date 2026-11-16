# escenas/crear_caso/paso_5_solucion.py
import streamlit as st
from datetime import datetime, timezone
from escenas.crear_caso.utils import (
    aplicar_css_panel, inicializar_caso, obtener_caso, actualizar_caso,
    ir_a_paso, cancelar_creacion, limpiar_caso,
    obtener_sprite_segun_edad_sexo,
    es_modo_editar, obtener_clave_caso_editando,
    KEY_MODO
)
from utils.supabase_client import supabase

LIMITE_PREGUNTAS = 10

def mostrar():
    """Paso 5: Solución del caso (preguntas e indicaciones)"""
    
    aplicar_css_panel()
    inicializar_caso()
    
    caso = obtener_caso()
    modo_editar = es_modo_editar()
    clave_editando = obtener_clave_caso_editando()
    
    # ===== BOTÓN CANCELAR =====
    col_cancelar, col_espacio = st.columns([1, 5])
    with col_cancelar:
        if st.button("Cancelar", key="btn_cancelar_paso5", use_container_width=True):
            cancelar_creacion()
    
    # ===== HEADER =====
    titulo = "Editar Caso" if modo_editar else "Crear Caso Nuevo"
    st.markdown(f'<h1 class="medico-title">{titulo}</h1>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="info-paso">
        <strong>Paso 5 de 5:</strong> Solución del Caso<br>
        <small>Caso: {caso.get('id_caso', '')} - {caso.get('nombre_caso', '')}</small>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ===== INICIALIZAR VARIABLES =====
    if 'preguntas_caso' not in caso or caso['preguntas_caso'] is None:
        actualizar_caso('preguntas_caso', [])
        caso['preguntas_caso'] = []
        
    if 'instrucciones_caso' not in caso or caso['instrucciones_caso'] is None:
        actualizar_caso('instrucciones_caso', '')
        caso['instrucciones_caso'] = ''
    
    # ============================================================
    # 1. PREGUNTAS (ARRIBA, FUERA DEL FORM)
    # ============================================================
    st.markdown('<div class="section-title">Preguntas del Caso</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-paso">
        <strong>Información:</strong> Añade preguntas para la evaluación del caso. 
        <br><small><em>Recomendación:</em> puedes incluir una pregunta donde pidas el Diagnóstico y otra para el Tratamiento.</small>
    </div>
    """, unsafe_allow_html=True)
    
    _renderizar_seccion_preguntas(caso)
    
    st.markdown("---")
    
    # ============================================================
    # 2. FORMULARIO PRINCIPAL (SOLO INDICACIONES + BOTONES)
    # ============================================================
    with st.form(key="form_paso_5"):
        st.markdown('<div class="section-title">Indicaciones para el Estudiante</div>', unsafe_allow_html=True)
        
        instrucciones_caso = st.text_area(
            "Indicaciones para el caso *",
            value=caso.get('instrucciones_caso', ''),
            height=100,
            placeholder="Escribe las instrucciones que se le darán al estudiante al iniciar el caso.",
            key="paso5_instrucciones"
        )
        
        st.markdown("---")
        
        # ===== BOTONES DENTRO DEL FORM (Al final) =====
        col_btn1, col_btn2, col_btn3 = st.columns([3, 1, 1])
        with col_btn2:
            atras = st.form_submit_button("Atrás", use_container_width=True)
        with col_btn3:
            with st.container(key="btn_siguiente_crear_caso"):
                texto_boton = "Guardar Cambios" if modo_editar else "Guardar Caso"
                guardar = st.form_submit_button(texto_boton, use_container_width=True, type="primary")
        
        if atras:
            _guardar_datos_paso5(instrucciones_caso)
            ir_a_paso(4)
        
        if guardar:
            if not instrucciones_caso or not instrucciones_caso.strip():
                st.error("Las indicaciones para el caso son obligatorias.")
            else:
                _guardar_datos_paso5(instrucciones_caso)
                
                accion = "actualizando" if modo_editar else "guardando"
                with st.spinner(f"{accion.capitalize()} caso completo..."):
                    exito, mensaje = _guardar_caso_completo()
                
                if exito:
                    clave_mostrar = clave_editando if modo_editar else caso.get('id_caso', '')
                    accion_mostrar = "actualizado" if modo_editar else "creado"
                    st.success(f"Caso {clave_mostrar} {accion_mostrar} exitosamente")
                    
                    limpiar_caso()
                    if KEY_MODO in st.session_state:
                        del st.session_state[KEY_MODO]
                    if 'clave_caso_editando' in st.session_state:
                        del st.session_state['clave_caso_editando']
                    
                    st.session_state['pagina'] = 'panel_medico'
                    st.rerun()
                else:
                    st.error(f"Error al guardar caso: {mensaje}")


def _renderizar_seccion_preguntas(caso):
    """Renderiza la sección de preguntas con botón de añadir"""
    preguntas = caso.get('preguntas_caso', []) or []
    
    col_boton, col_info = st.columns([1, 3])
    with col_boton:
        disabled = len(preguntas) >= LIMITE_PREGUNTAS
        if st.button(f"+ Añadir Pregunta", key="btn_add_pregunta", use_container_width=True, disabled=disabled):
            preguntas.append({"pregunta": "", "respuesta_esperada": ""})
            actualizar_caso('preguntas_caso', preguntas)
            st.rerun()
    
    with col_info:
        st.caption(f"Preguntas añadidas: **{len(preguntas)}/{LIMITE_PREGUNTAS}**")
    
    if len(preguntas) >= LIMITE_PREGUNTAS:
        st.warning(f"Has alcanzado el límite de {LIMITE_PREGUNTAS} preguntas.")
    
    if not preguntas:
        st.info("Aún no has añadido ninguna pregunta.")
        return
    
    st.markdown("---")
    
    ids_a_eliminar = []
    
    for i, pregunta_data in enumerate(preguntas):
        with st.container(border=True):
            col_num, col_eliminar = st.columns([5, 1])
            with col_num:
                st.markdown(f"**Pregunta {i + 1}**")
            with col_eliminar:
                if st.button("🗑️", key=f"btn_eliminar_pregunta_{i}", use_container_width=True):
                    ids_a_eliminar.append(i)
            
            nueva_pregunta = st.text_input(
                "Pregunta *",
                value=pregunta_data.get('pregunta', ''),
                placeholder="Ej: ¿Qué signos vitales solicitarías primero?",
                key=f"pregunta_texto_{i}"
            )
            
            nueva_respuesta = st.text_area(
                "Respuesta esperada (NO se muestra al estudiante) *",
                value=pregunta_data.get('respuesta_esperada', ''),
                height=80,
                placeholder="Ej: Frecuencia cardíaca, presión arterial, frecuencia respiratoria y temperatura.",
                key=f"pregunta_respuesta_{i}"
            )
            
            preguntas[i]['pregunta'] = nueva_pregunta
            preguntas[i]['respuesta_esperada'] = nueva_respuesta
    
    actualizar_caso('preguntas_caso', preguntas)
    
    if ids_a_eliminar:
        for idx in sorted(ids_a_eliminar, reverse=True):
            preguntas.pop(idx)
        actualizar_caso('preguntas_caso', preguntas)
        st.rerun()


def _guardar_datos_paso5(instrucciones_caso):
    actualizar_caso('instrucciones_caso', instrucciones_caso.strip())


def _guardar_caso_completo():
    """Guarda el caso completo en Supabase"""
    if not supabase:
        return False, "Supabase no conectado"
    
    caso = obtener_caso()
    modo_editar = es_modo_editar()
    clave_editando = obtener_clave_caso_editando()
    
    try:
        if modo_editar:
            clave_caso = clave_editando
        else:
            clave_caso = caso.get('id_caso', '')
        
        especialidad = caso.get('especialidad', '')
        
        if not modo_editar:
            check = supabase.table("casos_clinicos").select("clave_caso").eq("clave_caso", clave_caso).execute()
            if check.data:
                return False, f"La clave {clave_caso} ya existe"
        
        codigo = clave_caso[:2] if len(clave_caso) >= 2 else "XX"
        
        # ===== DATA =====
        data = {
            "nombre": caso.get('nombre', ''),
            "edad": caso.get('edad', 18),
            "sexo": caso.get('sexo', 'Femenino'),
            "motivo_consulta": caso.get('motivo_consulta', ''),
            "descripcion": caso.get('descripcion', ''),
            "antecedentes": caso.get('antecedentes', ''),
            "medicamentos_actuales": caso.get('medicamentos_actuales', ''),
            "nombre_caso": caso.get('nombre_caso', ''),
            "instrucciones": {
                "instrucciones_caso": caso.get('instrucciones_caso', ''),
                "guion_paciente": caso.get('guion_paciente', ''),
            },
            "visibilidad": {
                "sprite": caso.get('visible_sprite', True),
                "nombre": caso.get('visible_nombre', True),
                "edad": caso.get('visible_edad', True),
                "sexo": caso.get('visible_sexo', True),
                "motivo_consulta": caso.get('visible_motivo', True),
                "descripcion": caso.get('visible_descripcion', True),
                "antecedentes": caso.get('visible_antecedentes', True),
                "medicamentos_actuales": caso.get('visible_medicamentos', True),
            }
        }
        
        # ===== SOLUCION =====
        preguntas = caso.get('preguntas_caso', []) or []
        preguntas_validas = [
            p for p in preguntas 
            if p.get('pregunta', '').strip() and p.get('respuesta_esperada', '').strip()
        ]
        
        solucion = {
            "diagnostico_correcto": caso.get('diagnostico_correcto', ''),
            "diagnostico_alternativo": caso.get('diagnostico_alternativo', ''),
            "tratamiento_esperado": caso.get('tratamiento_esperado', ''),
            "errores_criticos": caso.get('errores_criticos', ''),
            "preguntas": preguntas_validas,
        }
        
        # ===== COMPETENCIAS =====
        competencias_seleccionadas = caso.get('competencias_seleccionadas', [])
        
        # ===== ESTUDIOS =====
        valores_estudios = caso.get('valores_estudios', {}) or {}
        
        # ===== SPRITE =====
        sprite_url = caso.get('sprite_url')
        if not sprite_url:
            edad = caso.get('edad', 18)
            sexo = caso.get('sexo', 'Femenino')
            try:
                edad_int = int(edad) if str(edad).isdigit() else 18
            except:
                edad_int = 18
            sprite_url = obtener_sprite_segun_edad_sexo(edad_int, sexo)
        
        # ===== PAYLOAD =====
        payload = {
            "clave_caso": clave_caso,
            "especialidad": especialidad,
            "especialidad_codigo": codigo,
            "responsable": caso.get('responsable', ''),
            "data": data,
            "solucion": solucion,
            "tipo_caso": caso.get('tipo_caso', 'Estático'),
            "rubrica_competencias": competencias_seleccionadas,
            "valores_estudios": valores_estudios,
            "sprite_url": sprite_url,
            "fecha_actualizacion": datetime.now(timezone.utc).isoformat()
        }
        
        if modo_editar:
            payload_update = {k: v for k, v in payload.items() if k != 'clave_caso'}
            response = supabase.table("casos_clinicos").update(payload_update).eq("clave_caso", clave_caso).execute()
            return True, "Caso actualizado exitosamente"
        else:
            response = supabase.table("casos_clinicos").insert(payload).execute()
            return True, "Caso creado exitosamente"
        
    except Exception as e:
        print(f"❌ Error guardando caso: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error: {str(e)}"