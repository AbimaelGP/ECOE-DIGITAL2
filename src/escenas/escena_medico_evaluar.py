# escenas/escena_medico_evaluar.py
"""Pestaña 'Evaluar estudiantes' del médico, formulario de evaluación docente
(evaluación ciega) y vista de la evaluación del chatbot."""
import streamlit as st

from components import ui_evaluacion as ui
from utils import evaluacion_dual as ed


# ===================== LISTA DE ESTUDIANTES =====================

def mostrar_lista():
    ui.css()
    if not ed.tablas_dual_disponibles():
        st.warning("La evaluación docente aún no está activada en la base de datos. "
                   "Pide al administrador que aplique la migración 002.")
        return

    identificador = st.session_state.get("identificador", "")
    medico, filas = ed.filas_para_medico(identificador)
    st.markdown('<div class="ev-seccion">Estudiantes de mi circuito y área</div>', unsafe_allow_html=True)

    if not medico.get("circuito_asignado"):
        st.caption("No tienes un circuito asignado; se muestran todos los circuitos que incluyen tu área. "
                   "El administrador puede asignarte uno en 'Creadores de Casos'.")

    if not filas:
        st.info("Todavía no hay estudiantes asignados a estaciones de tu área.")
        return

    c1, c2, c3, c4 = st.columns(4)
    examenes = sorted({str(f["fecha_examen"]) for f in filas if f["fecha_examen"]})
    circuitos = sorted({f["circuito"] for f in filas})
    estaciones = sorted({f"Área {f['num_area']} · {f['area']}" for f in filas})
    f_exam = c1.selectbox("Examen (fecha)", ["Todos"] + examenes, key="mev_exam")
    f_circ = c2.selectbox("Circuito", ["Todos"] + circuitos, key="mev_circ")
    f_est = c3.selectbox("Área / estación", ["Todas"] + estaciones, key="mev_est")
    f_status = c4.selectbox("Estatus", ["Todos", "Pendientes", "Enviadas", "Borradores"], key="mev_status")

    def pasa(f):
        if f_exam != "Todos" and str(f["fecha_examen"]) != f_exam:
            return False
        if f_circ != "Todos" and f["circuito"] != f_circ:
            return False
        if f_est != "Todas" and f"Área {f['num_area']} · {f['area']}" != f_est:
            return False
        estatus = (f["mi_eval"] or {}).get("estatus")
        if f_status == "Pendientes" and estatus == "enviada":
            return False
        if f_status == "Enviadas" and estatus != "enviada":
            return False
        if f_status == "Borradores" and estatus != "borrador":
            return False
        return True

    vista = [f for f in filas if pasa(f)]
    enviadas = sum(1 for f in vista if (f["mi_eval"] or {}).get("estatus") == "enviada")
    st.markdown(
        f'<div style="text-align:right;margin:4px 0 10px">{ui.badge(f"{len(vista)} registros")} '
        f'{ui.badge(f"{enviadas} evaluados", "ok")} {ui.badge(f"{len(vista) - enviadas} pendientes", "pend")}</div>',
        unsafe_allow_html=True)

    pesos = [0.95, 2, 0.75, 0.95, 1.15, 2.4, 1.55, 1.35]
    cab = st.columns(pesos)
    for col, t in zip(cab, ["Matrícula", "Nombre", "Circuito", "Caso", "Modalidad", "IA Evaluadora", "Mi evaluación", ""]):
        col.markdown(f"**{t}**")
    st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)

    for i, f in enumerate(vista):
        mi = f["mi_eval"] or {}
        enviada = mi.get("estatus") == "enviada"
        cols = st.columns(pesos)
        cols[0].write(f["matricula"])
        cols[1].write(f["nombre"])
        cols[2].write(f["circuito"])
        cols[3].write(f["clave_caso"])
        cols[4].markdown(ui.badge_modalidad(f["modalidad"]), unsafe_allow_html=True)

        with cols[5]:
            if f["modalidad"] == "Estandarizado":
                st.markdown('<span style="color:#8A8FA0">No aplica</span>', unsafe_allow_html=True)
            elif not enviada:
                st.markdown('<span style="color:#8A8FA0">🔒 Oculta hasta evaluar</span>', unsafe_allow_html=True)
            elif f["eval_chatbot"]:
                a, b = st.columns([0.8, 2.2], vertical_alignment="center")
                a.markdown(f"**{ui.fmt(ed.nota_chatbot(f))}**")
                if b.button("Ver evaluación", key=f"mev_vb_{i}"):
                    st.session_state["ev_fila"] = f
                    st.session_state["pagina"] = "medico_eval_chatbot"
                    st.rerun()
            else:
                st.markdown('<span style="color:#8A8FA0">Sin evaluar aún</span>', unsafe_allow_html=True)

        with cols[6]:
            if enviada:
                st.markdown(f"**{ui.fmt(mi.get('calificacion'))}** {ui.badge('Enviada', 'ok')}", unsafe_allow_html=True)
            elif mi:
                st.markdown(ui.badge("Borrador", "gris"), unsafe_allow_html=True)
            elif not f["realizada"] and f["modalidad"] != "Estandarizado":
                st.markdown(ui.badge("Sin realizar", "gris"), unsafe_allow_html=True)
            else:
                st.markdown(ui.badge("Pendiente", "pend"), unsafe_allow_html=True)

        with cols[7]:
            if enviada or mi:
                etiqueta, tipo = "Ver / editar", "secondary"
            elif f["modalidad"] == "Estandarizado":
                etiqueta, tipo = "Evaluar en vivo", "primary"
            else:
                etiqueta, tipo = "Evaluar", "primary"
            if st.button(etiqueta, key=f"mev_ev_{i}", type=tipo, use_container_width=True):
                st.session_state["ev_fila"] = f
                st.session_state.pop("ev_form_cargado", None)
                st.session_state["pagina"] = "evaluacion_docente"
                st.rerun()


# ===================== FORMULARIO DE EVALUACIÓN DOCENTE =====================

def _cabecera(f, derecha=""):
    st.markdown(
        f'<div class="ev-cab"><b>Estudiante:</b> {ui.e(f["nombre"])} ({ui.e(f["matricula"])}) · '
        f'<b>Caso:</b> {ui.e(f["clave_caso"])} – {ui.e(f.get("nombre_caso", ""))} · '
        f'<b>Circuito:</b> {ui.e(f["circuito"])} · <b>Área:</b> {f["num_area"]} {ui.e(f["area"])} · '
        f'<b>Fecha:</b> {ui.e(f.get("fecha_examen", ""))} &nbsp; {ui.badge_modalidad(f["modalidad"])}'
        f'<span style="float:right">{derecha}</span></div>', unsafe_allow_html=True)


def _sidebar():
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**Médico:** {st.session_state.get('nombre', 'Médico')}")
        st.markdown(f"**ID:** {st.session_state.get('identificador', '')}")
        st.markdown("---")


def _volver(destino="panel_medico"):
    st.markdown("<style>[data-testid='stSidebar']{background-color:#70257E !important}"
                "[data-testid='stSidebar'] *{color:#FFFFFF !important}</style>", unsafe_allow_html=True)
    _sidebar()
    if st.button("← Regresar", key="ev_volver"):
        st.session_state["pagina"] = destino
        st.session_state["medico_tab"] = "evaluar"
        st.rerun()


def mostrar_formulario():
    ui.css()
    f = st.session_state.get("ev_fila")
    if not f:
        st.session_state["pagina"] = "panel_medico"
        st.rerun()
    identificador = st.session_state.get("identificador", "")
    _volver()
    st.markdown('<div class="ev-titulo">Evaluación Docente</div>', unsafe_allow_html=True)
    _cabecera(f, '<span style="color:#626779;font-size:12px">Formulario generado a partir de las '
                 'competencias definidas en el caso</span>')

    caso = ed.obtener_caso(f["clave_caso"])
    criterios = ed.competencias_de_caso(caso or {})
    if not criterios:
        st.warning("Este caso no tiene competencias seleccionadas. El médico creador debe elegirlas en el Paso 2.")
        return

    previa = ed.obtener_eval_docente(f["matricula"], f["clave_caso"], identificador) or {}
    previos = {c.get("clave"): c for c in ed._a_json(previa.get("criterios"), [])}
    pref = f"evd_{f['matricula']}_{f['clave_caso']}"

    estandarizado = f["modalidad"] == "Estandarizado"
    if estandarizado:
        col_form = st.container()
        st.caption("Caso estandarizado: evalúa en vivo con la rúbrica. Se guarda el caso y tu evaluación (100 % médico).")
    else:
        col_ev, col_form = st.columns([1, 1.25])
        with col_ev:
            st.markdown('<div class="ev-seccion">Evidencia del estudiante</div>', unsafe_allow_html=True)
            ev = ed.obtener_evidencia(f["matricula"], f["clave_caso"])
            t1, t2, t3 = st.tabs(["Transcripción del chat", "Estudios solicitados", "Diagnóstico y plan"])
            with t1:
                st.markdown(ui.transcripcion_html(ev["transcripcion"]), unsafe_allow_html=True)
            with t2:
                if ev["estudios"]:
                    for est in ev["estudios"]:
                        st.markdown(f"• {est}")
                else:
                    st.info("No hay estudios solicitados registrados.")
            with t3:
                texto = ed.texto_respuestas(ev["respuestas"])
                if texto:
                    st.markdown(f'<div class="ev-tarjeta ev-txt" style="white-space:pre-wrap">{ui.e(texto)}</div>',
                                unsafe_allow_html=True)
                else:
                    st.info("El estudiante no registró respuestas escritas.")

    with col_form:
        st.markdown(f'<div class="ev-seccion">Rúbrica del caso ({len(criterios)} dominios)</div>', unsafe_allow_html=True)
        resultado = []
        for idx, c in enumerate(criterios):
            prev = previos.get(c["clave"], {})
            with st.container(border=True):
                st.markdown(f'<span class="ev-dom">{ui.e(c["categoria"].title())} · {ui.e(c["dominio"])}</span>'
                            f'<span class="ev-crit">{ui.e(c["texto"])}</span>', unsafe_allow_html=True)
                clave_p = f"{pref}_p{idx}"
                puntaje_actual = st.session_state.get(clave_p, prev.get("puntaje"))
                st.markdown(ui.niveles_html(c["niveles"], puntaje_actual), unsafe_allow_html=True)
                opciones = list(range(1, 11))
                puntaje = st.radio("Puntaje", opciones, horizontal=True, key=clave_p,
                                   index=opciones.index(prev["puntaje"]) if prev.get("puntaje") in opciones else None)
                comentario = st.text_input("Comentario sobre este criterio (opcional)", key=f"{pref}_c{idx}",
                                           value=prev.get("comentario", ""), placeholder="💬 Comentario del médico sobre este criterio")
                resultado.append({"clave": c["clave"], "categoria": c["categoria"], "dominio": c["dominio"],
                                  "texto": c["texto"], "puntaje": puntaje,
                                  "nivel": ed.nivel_de_puntaje(puntaje) if puntaje else None,
                                  "comentario": comentario})

        generales = st.text_area("Comentarios generales", value=previa.get("comentarios_generales", "") or "",
                                 key=f"{pref}_gen", placeholder="Retroalimentación general para el estudiante")
        nota = ed.promedio([r["puntaje"] for r in resultado if r["puntaje"]])
        a, b, c3 = st.columns([1.6, 1, 1.2])
        a.markdown(f'Calificación docente: <span style="font-size:26px;color:{ui.MORADO};font-weight:700">'
                   f'{ui.fmt(nota)}</span><br><span style="font-size:11px;color:#8A8FA0">🔒 La calificación del '
                   f'chatbot se muestra solo después de enviar (evaluación ciega).</span>', unsafe_allow_html=True)
        if b.button("Guardar borrador", use_container_width=True, key=f"{pref}_bor"):
            ok, msg = ed.guardar_eval_docente(f, resultado, generales, identificador, enviar=False)
            (st.success if ok else st.error)(msg)
        if c3.button("Enviar evaluación", type="primary", use_container_width=True, key=f"{pref}_env"):
            faltan = [r["texto"][:40] for r in resultado if not r["puntaje"]]
            if faltan:
                st.error("Asigna puntaje a todos los criterios antes de enviar.")
            else:
                ok, msg = ed.guardar_eval_docente(f, resultado, generales, identificador, enviar=True)
                if ok:
                    st.success(msg)
                    st.session_state["pagina"] = "panel_medico"
                    st.session_state["medico_tab"] = "evaluar"
                    st.rerun()
                else:
                    st.error(msg)


# ===================== EVALUACIÓN DEL CHATBOT (vista del médico) =====================

def mostrar_eval_chatbot():
    ui.css()
    f = st.session_state.get("ev_fila")
    identificador = st.session_state.get("identificador", "")
    if not f:
        st.session_state["pagina"] = "panel_medico"
        st.rerun()
    _volver()
    mi = ed.obtener_eval_docente(f["matricula"], f["clave_caso"], identificador)
    if not mi or mi.get("estatus") != "enviada":
        st.warning("Primero envía tu evaluación: la del chatbot se muestra solo después (evaluación ciega).")
        return
    bot = f.get("eval_chatbot")
    if not bot:
        st.info("El chatbot aún no ha evaluado este caso.")
        return

    st.markdown('<div class="ev-titulo">Evaluación del chatbot</div>', unsafe_allow_html=True)
    comps = ed._a_json(bot.get("competencias"), [])
    mis = {c.get("clave"): c for c in ed._a_json(mi.get("criterios"), [])}
    _cabecera(f, f'Prompt <b>{ui.e(bot.get("prompt_version"))}</b> · {ui.e(str(bot.get("fecha_evaluacion", ""))[:10])} · '
                 f'Chatbot: <b style="color:{ui.MORADO}">{ui.fmt(bot.get("calificacion"))}</b> · '
                 f'Tú: <b style="color:{ui.MORADO}">{ui.fmt(mi.get("calificacion"))}</b>')

    col_a, col_b = st.columns([1.5, 1])
    with col_a:
        for c in comps:
            st.markdown(ui.tarjeta_chatbot(c, (mis.get(c.get("clave")) or {}).get("puntaje")), unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="ev-seccion">Transcripción con evidencias marcadas</div>', unsafe_allow_html=True)
        st.markdown(ui.transcripcion_html(ed._a_json(bot.get("transcripcion"), []), ui.marcados_de(comps)),
                    unsafe_allow_html=True)
        with st.popover("Reportar desacuerdo con el chatbot", use_container_width=True):
            comp = st.selectbox("Competencia", [c.get("texto") for c in comps], key="rep_comp_med")
            txt = st.text_area("¿En qué no estás de acuerdo?", key="rep_txt_med")
            if st.button("Enviar reporte", key="rep_env_med"):
                ok = ed.reportar_chatbot(f["matricula"], f["clave_caso"], comp, txt, "desacuerdo",
                                         identificador, "medico", bot.get("prompt_version"))
                (st.success if ok else st.error)("Reporte enviado" if ok else "No se pudo enviar")
