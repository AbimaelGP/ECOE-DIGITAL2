# escenas/crear_caso/paso_2_competencias.py
import streamlit as st
from escenas.crear_caso.utils import (
    aplicar_css_panel, inicializar_caso, obtener_caso, actualizar_caso,
    ir_a_paso, cancelar_creacion, es_modo_editar,
    COMPETENCIAS
)

# Límites de competencias para la rúbrica del caso
MIN_COMPETENCIAS = 5
MAX_COMPETENCIAS = 12


def mostrar():
    """Paso 2: Selección de competencias del perfil de egreso"""
    
    aplicar_css_panel()
    inicializar_caso()
    
    caso = obtener_caso()
    modo_editar = es_modo_editar()
    
    if not caso.get('nombre_caso'):
        st.warning("Debes completar el Paso 1 primero")
        if st.button("← Volver al Paso 1"):
            ir_a_paso(1)
        return
    
    col_cancelar, col_espacio = st.columns([1, 5])
    with col_cancelar:
        if st.button("← Cancelar", key="btn_cancelar_paso2", use_container_width=True):
            cancelar_creacion()
    
    titulo = "Editar Caso" if modo_editar else "Crear Caso Nuevo"
    st.markdown(f'<h1 class="medico-title">{titulo}</h1>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="info-paso">
        <strong>Paso 2 de 5:</strong> Competencias del Perfil de Egreso — al seleccionar dominios se genera automáticamente el formulario de evaluación docente<br>
        <small>Caso: {caso.get('id_caso', '')} - {caso.get('nombre_caso', '')}</small>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background-color: #FFFFFF; padding: 15px; border-radius: 8px; border-left: 4px solid #70257E; margin-bottom: 1.5rem; color: #303442;">
        <strong>Instrucción:</strong> Selecciona las competencias del perfil de egreso que deseas evaluar en este caso. 
        Toma en cuenta que el escenario tiene una duración máxima de 10 minutos.
    </div>
    """, unsafe_allow_html=True)
    
    # ===== INICIALIZAR COMPETENCIAS SELECCIONADAS =====
    if 'competencias_seleccionadas' not in caso or caso['competencias_seleccionadas'] is None:
        actualizar_caso('competencias_seleccionadas', [])
        caso['competencias_seleccionadas'] = []
        
    # Hacemos una copia local para iterar y guardar
    competencias_actuales = caso.get('competencias_seleccionadas', []).copy()
    
    # Helper para verificar si una competencia ya está seleccionada
    def esta_seleccionada(cat_principal, subcat, texto_comp):
        for c in competencias_actuales:
            if (c.get('texto') == texto_comp and 
                c.get('categoria') == cat_principal and 
                c.get('subcategoria') == subcat):
                return True
        return False

    col_izq, col_der = st.columns([1.15, 1], gap="large")
    with col_izq:
        # ===== RENDERIZAR COMPETENCIAS POR CATEGORÍA =====
        for categoria_principal, subcategorias in COMPETENCIAS.items():
            st.markdown(f'<div class="section-title">{categoria_principal}</div>', unsafe_allow_html=True)
        
            for subcategoria, lista_competencias in subcategorias.items():
                with st.expander(f"📌 {subcategoria}", expanded=False):
                    for comp in lista_competencias:
                        # Verificar si ya estaba seleccionada
                        valor_actual = esta_seleccionada(categoria_principal, subcategoria, comp)
                    
                        # Usamos una key única
                        key_checkbox = f"chk_{hash(categoria_principal+subcategoria+comp)}"
                    
                        # Renderizamos el checkbox
                        seleccionada_ahora = st.checkbox(
                            comp, 
                            value=valor_actual, 
                            key=key_checkbox
                        )
                    
                        # Lógica para actualizar la lista sin usar on_change
                        if seleccionada_ahora and not valor_actual:
                            # Se acaba de marcar -> Agregar
                            competencias_actuales.append({
                                "categoria": categoria_principal,
                                "subcategoria": subcategoria,
                                "texto": comp
                            })
                        elif not seleccionada_ahora and valor_actual:
                            # Se acaba de desmarcar -> Quitar
                            competencias_actuales = [c for c in competencias_actuales if not (
                                c.get('texto') == comp and 
                                c.get('categoria') == categoria_principal and 
                                c.get('subcategoria') == subcategoria
                            )]
    
    # Guardamos los cambios en el caso (siempre, para no perderlos)
    actualizar_caso('competencias_seleccionadas', competencias_actuales)

    # ===== VISTA PREVIA DEL FORMULARIO DE EVALUACIÓN DOCENTE =====
    with col_der:
        mostrar_vista_previa_formulario(competencias_actuales)

    st.markdown("---")
    
    # ===== BOTONES =====
    col_btn1, col_btn2, col_btn3 = st.columns([3, 1, 1])
    with col_btn2:
        if st.button("← Atrás", key="btn_atras_paso2", use_container_width=True):
            ir_a_paso(1)
            
    error_competencias = None
    with col_btn3:
        with st.container(key="btn_siguiente_crear_caso"):
            if st.button("Siguiente →", key="btn_siguiente_paso2", use_container_width=True, type="primary"):
                total_competencias = len(competencias_actuales)
                if total_competencias < MIN_COMPETENCIAS or total_competencias > MAX_COMPETENCIAS:
                    error_competencias = (
                        f"Debes seleccionar entre {MIN_COMPETENCIAS} y {MAX_COMPETENCIAS} competencias. "
                        f"Actualmente llevas {total_competencias}."
                    )
                else:
                    ir_a_paso(3)

    if error_competencias:
        st.error(error_competencias)

def mostrar_vista_previa_formulario(competencias):
    """Vista previa del formulario que llenará el médico evaluador."""
    from components import ui_evaluacion as ui
    from utils.evaluacion_dual import competencias_de_caso
    ui.css()
    criterios = competencias_de_caso(competencias)
    st.markdown(
        '<div class="ev-tarjeta" style="border:2px solid #70257E">'
        '<span style="font-weight:700;color:#70257E;font-size:17px">Vista previa · Formulario de evaluación docente</span> '
        '<span class="ev-badge" style="background:#FDE68A;color:#78350F">NUEVO</span><br>'
        f'<span style="font-size:12px;color:#626779">Generado con la Rúbrica General (5 niveles · escala 1–10) '
        f'para {len(criterios)} dominio(s) seleccionado(s)</span></div>', unsafe_allow_html=True)
    if not criterios:
        st.info("Marca al menos una competencia para generar el formulario.")
        return
    for c in criterios:
        st.markdown(
            f'<div class="ev-tarjeta"><span class="ev-dom">{ui.e(c["dominio"])}</span>'
            f'<span class="ev-crit" style="font-size:13px">{ui.e(c["texto"])}</span>'
            f'{ui.niveles_html(c["niveles"], mostrar_desc=False)}'
            '<div style="border:1px dashed #D1D5DB;border-radius:6px;padding:4px 8px;font-size:12px;color:#8A8FA0">'
            '💬 Comentario del médico sobre este criterio</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="ev-tarjeta"><b style="font-size:13px">Comentarios generales</b>'
                '<div style="border:1px dashed #D1D5DB;border-radius:6px;padding:4px 8px;font-size:12px;color:#8A8FA0;margin-top:4px">'
                '💬 Retroalimentación general para el estudiante</div></div>', unsafe_allow_html=True)
