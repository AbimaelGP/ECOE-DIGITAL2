# escenas/escena_admin_dual.py
"""Administrador: ponderación de la calificación final, tabla comparativa
chatbot vs médico, comparativo por competencia y evaluación completa del chatbot."""
import io
import json
from datetime import datetime

import pandas as pd
import streamlit as st

from components import ui_evaluacion as ui
from utils import evaluacion_dual as ed


def _usuario():
    return st.session_state.get("identificador", "admin")


# ===================== PONDERACIÓN =====================

def _panel_ponderacion(filas, configs):
    c1, c2 = st.columns([1, 1.15])
    examenes = sorted({str(f["fecha_examen"]) for f in filas if f["fecha_examen"]})
    circuitos = sorted({f["circuito"] for f in filas})

    with c2:
        with st.container(border=True):
            st.markdown("**Alcance y reglas**")
            a1, a2, a3 = st.columns(3)
            exam = a1.selectbox("Aplicar a examen", ["Todos"] + examenes, key="pond_exam")
            circ = a2.selectbox("Circuito", ["Todos"] + circuitos, key="pond_circ")
            moda = a3.selectbox("Modalidad", ["Todas", "Virtual", "Estático", "Estandarizado"], key="pond_moda")
            if moda != "Todas":
                alcance, valor = "modalidad", moda
            elif circ != "Todos":
                alcance, valor = "circuito", circ
            else:
                alcance, valor = "examen", ("todos" if exam == "Todos" else exam)
            actual = next((c for c in configs if c.get("alcance") == alcance and str(c.get("valor")) == valor), None) \
                or ed.ponderacion_para({"fecha_examen": "todos"}, configs)
            usar = st.checkbox("Si falta una evaluación, usar 100 % la disponible",
                               value=bool(actual.get("usar_disponible", True)), key=f"pond_usar_{alcance}_{valor}")
            est = st.checkbox("Casos estandarizados: médico = 1.0 (sin evaluación del chatbot)",
                              value=bool(actual.get("estandarizado_solo_medico", True)), key=f"pond_est_{alcance}_{valor}")
            bloq = st.checkbox("Bloquear ponderación al publicar resultados",
                               value=bool(actual.get("bloqueada", False)), key=f"pond_bloq_{alcance}_{valor}")
            st.caption(f"Se guardará para: **{alcance} = {valor}**. Prioridad: modalidad › circuito › examen.")

    with c1:
        with st.container(border=True):
            st.markdown(f'<b style="color:{ui.MORADO};font-size:17px">Ponderación de la calificación final</b><br>'
                        '<span style="font-size:12px;color:#626779">Valores entre 0 y 1 · se normalizan para que sumen 1</span>',
                        unsafe_allow_html=True)
            wb = st.slider("🤖 Chatbot evaluador", 0.0, 1.0, float(actual.get("w_chatbot", 0.5)), 0.05,
                           key=f"pond_wb_{alcance}_{valor}", disabled=bool(actual.get("bloqueada")))
            wm = st.slider("🩺 Médico evaluador", 0.0, 1.0, float(actual.get("w_medico", 0.5)), 0.05,
                           key=f"pond_wm_{alcance}_{valor}", disabled=bool(actual.get("bloqueada")))
            tot = wb + wm
            nb, nm = (wb / tot, wm / tot) if tot else (0, 0)
            st.markdown(f'<div style="background:#F3E8FF;border-radius:8px;padding:8px;text-align:center">'
                        f'<b>Final</b> = {nb:.2f} × Chatbot + {nm:.2f} × Médico</div>', unsafe_allow_html=True)

    b1, b2, b3 = st.columns([3, 1, 1.4])
    if b2.button("Restablecer", use_container_width=True, key="pond_reset"):
        for k in list(st.session_state.keys()):
            if k.startswith("pond_w"):
                del st.session_state[k]
        st.rerun()
    if b3.button("Aplicar y recalcular", type="primary", use_container_width=True, key="pond_apply"):
        if actual.get("bloqueada") and bloq:
            st.error("Esta ponderación está bloqueada. Desmarca 'Bloquear' para modificarla.")
        else:
            ok, msg = ed.guardar_ponderacion(alcance, valor, wb, wm, usar, est, bloq, _usuario())
            if ok:
                configs = ed.obtener_ponderaciones()
                n = ed.publicar_calificaciones(filas, configs, _usuario())
                st.session_state["adm_dual_msg"] = f"{msg}. Calificaciones finales publicadas/actualizadas: {n}"
                st.rerun()
            else:
                st.error(msg)


# ===================== TABLA COMPARATIVA =====================

def _tabla_comparativa(filas, configs):
    st.markdown('<div class="ev-seccion">Evaluación de Exámenes · comparativo</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1.4, 1, 1])
    buscar = f1.text_input("Buscar", placeholder="🔍 Matrícula o nombre", key="cmp_buscar")
    examenes = sorted({str(f["fecha_examen"]) for f in filas if f["fecha_examen"]})
    exam = f2.selectbox("Examen", ["Todos"] + examenes, key="cmp_exam")
    moda = f3.selectbox("Modalidad", ["Todas", "Virtual", "Estático", "Estandarizado"], key="cmp_moda")

    vista = []
    for f in filas:
        if buscar and buscar.lower() not in f"{f['matricula']} {f['nombre']}".lower():
            continue
        if exam != "Todos" and str(f["fecha_examen"]) != exam:
            continue
        if moda != "Todas" and f["modalidad"] != moda:
            continue
        if not (f["realizada"] or f["eval_docentes"] or f["eval_chatbot"]):
            continue
        vista.append(f)

    if not vista:
        st.info("Aún no hay estaciones realizadas o evaluadas con estos filtros.")
        return

    filas_csv, registros = [], []
    for f in vista:
        r = ed.calcular_final(f, ed.ponderacion_para(f, configs))
        dif = (r["medico"] - r["chatbot"]) if (r["chatbot"] is not None and r["medico"] is not None) else None
        if r["final"] is None:
            final_txt = "—"
        elif r["parcial"]:
            final_txt = f"Parcial {r['final']:.2f}"
        else:
            final_txt = f"{r['final']:.2f}"
        registros.append({
            "Fecha examen": str(f["fecha_examen"]), "Matrícula": f["matricula"], "Nombre": f["nombre"],
            "Circuito": f["circuito"], "Área": f"{f['num_area']} · {f['area']}", "Caso": f["clave_caso"],
            "Modalidad": f["modalidad"],
            "Chatbot": "No aplica" if f["modalidad"] == "Estandarizado" else ui.fmt(r["chatbot"]),
            "Médico": "Pendiente" if r["medico"] is None else ui.fmt(r["medico"]),
            "Diferencia": "—" if dif is None else f"{dif:+.1f}",
            "Final ponderada": final_txt,
        })
        filas_csv.append({"fecha_examen": f["fecha_examen"], "matricula": f["matricula"], "nombre": f["nombre"],
                          "circuito": f["circuito"], "area": f["area"], "caso": f["clave_caso"],
                          "modalidad": f["modalidad"], "chatbot": r["chatbot"], "medico": r["medico"],
                          "w_chatbot": r["w_chatbot"], "w_medico": r["w_medico"], "final": r["final"],
                          "parcial": r["parcial"]})

    st.caption(f"{len(vista)} estaciones · selecciona una fila para ver el comparativo o evaluarla con el chatbot.")
    sel = st.dataframe(pd.DataFrame(registros), hide_index=True, use_container_width=True, height=420,
                       on_select="rerun", selection_mode="single-row", key="cmp_tabla")
    filas_sel = sel.selection.rows if sel and hasattr(sel, "selection") else []

    a1, a2, a3, a4 = st.columns([2.2, 1.2, 1.4, 1.2])
    if filas_sel:
        f = vista[filas_sel[0]]
        a1.markdown(f"**Seleccionado:** {f['nombre']} · {f['clave_caso']} {ui.badge_modalidad(f['modalidad'])}",
                    unsafe_allow_html=True)
        if a2.button("Ver comparativo", type="primary", use_container_width=True, key="cmp_ver"):
            st.session_state["adm_dual_fila"] = f
            st.session_state["adm_dual_vista"] = "comparativo"
            st.rerun()
        if f["modalidad"] != "Estandarizado" and f["realizada"]:
            etiqueta = "Re-evaluar con chatbot" if f["eval_chatbot"] else "Evaluar con chatbot"
            if a3.button(etiqueta, use_container_width=True, key="cmp_ev",
                         help="Ejecuta el chatbot evaluador (Gemini) para este estudiante y caso"):
                antes = ed.nota_chatbot(f)
                with st.spinner("El chatbot está evaluando…"):
                    try:
                        ok, msg = ed.evaluar_con_chatbot(f["matricula"], f["clave_caso"], f["num_area"])
                    except Exception as e:
                        ok, msg = False, str(e)
                if ok:
                    from utils.horario import ahora
                    nueva = ed.obtener_eval_chatbot_reciente(f["matricula"], f["clave_caso"])
                    st.session_state["adm_dual_msg"] = (
                        f"Re-evaluado a las {ahora():%H:%M}: {f['nombre']} · {f['clave_caso']} — "
                        f"chatbot {ui.fmt(antes)} → {ui.fmt((nueva or {}).get('calificacion'))}. "
                        "El PDF no cambia; para regenerarlo usa \"Re-evaluar\" en la tabla de PDF.")
                    st.rerun()
                else:
                    st.error(msg)
        try:
            from utils.supabase_client import supabase
            pdf = supabase.table("evaluaciones_pdf").select("url_pdf, fecha_creacion").eq("matricula", f["matricula"]) \
                .order("fecha_creacion").execute().data
            if pdf:
                a4.link_button("Ver resultados (PDF)", pdf[-1]["url_pdf"], use_container_width=True)
        except Exception:
            pass
    else:
        a1.caption("Ninguna fila seleccionada.")

    st.download_button("Exportar tabla (CSV)", pd.DataFrame(filas_csv).to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"comparativo_ecoe_{datetime.now():%Y%m%d}.csv", mime="text/csv", key="cmp_csv")


# ===================== COMPARATIVO POR COMPETENCIA =====================

def _pdf_comparativo(f, filas_comp, r):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
    est = getSampleStyleSheet()
    p = lambda t: Paragraph(str(t or "").replace("&", "&amp;").replace("<", "&lt;"), est["BodyText"])
    elems = [Paragraph("Comparativo Chatbot vs Médico", est["Title"]),
             p(f"{f['nombre']} ({f['matricula']}) · Caso {f['clave_caso']} · {f['modalidad']} · Circuito {f['circuito']} · Área {f['num_area']}"),
             p(f"Chatbot: {ui.fmt(r['chatbot'])} · Médico: {ui.fmt(r['medico'])} · Final ({r['w_chatbot']:.2f}/{r['w_medico']:.2f}): {ui.fmt(r['final'], 2)}"),
             Spacer(1, 10)]
    datos = [["Competencia", "Chatbot", "Criterio del chatbot", "Médico", "Observación del médico", "Dif."]]
    for x in filas_comp:
        datos.append([p(f"{x['dominio']} · {x['texto']}"), f"{x['bot_p'] or '—'} {x['bot_n'] or ''}", p(x["bot_crit"]),
                      f"{x['med_p'] or '—'} {x['med_n'] or ''}", p(x["med_com"]), x["dif"]])
    t = Table(datos, colWidths=[150, 70, 220, 70, 170, 50], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#70257E")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    elems.append(t)
    doc.build(elems)
    return buf.getvalue()


def _vista_comparativo(f, configs):
    if st.button("← Evaluación", key="cmp_back"):
        st.session_state.pop("adm_dual_vista", None)
        st.rerun()
    st.markdown('<div class="ev-titulo">Comparativo Chatbot vs Médico</div>', unsafe_allow_html=True)
    r = ed.calcular_final(f, ed.ponderacion_para(f, configs))
    bot = f.get("eval_chatbot") or {}
    medicos = [e for e in f.get("eval_docentes", []) if e.get("estatus") == "enviada"]
    nombres_med = ", ".join(sorted({e.get("evaluador", "") for e in medicos})) or "sin evaluación"

    h1, h2, h3, h4 = st.columns([4, 0.8, 0.8, 1.1])
    h1.markdown(f'<div class="ev-cab"><b>{ui.e(f["nombre"])}</b> ({ui.e(f["matricula"])}) · Caso {ui.e(f["clave_caso"])} '
                f'{ui.badge_modalidad(f["modalidad"])} · Circuito {ui.e(f["circuito"])} · Área {f["num_area"]}<br>'
                f'<span style="font-size:12px;color:#626779">Médico: {ui.e(nombres_med)} · Chatbot evaluador: prompt '
                f'{ui.e(bot.get("prompt_version", "—"))} · {ui.e(str(bot.get("fecha_evaluacion", ""))[:10])}</span></div>',
                unsafe_allow_html=True)
    h2.markdown(f'<div class="ev-kpi"><div class="l">Chatbot</div><div class="v">{ui.fmt(r["chatbot"])}</div></div>', unsafe_allow_html=True)
    h3.markdown(f'<div class="ev-kpi"><div class="l">Médico</div><div class="v">{ui.fmt(r["medico"])}</div></div>', unsafe_allow_html=True)
    etiqueta_final = "Parcial (una sola nota)" if r["parcial"] else f'Final ({r["w_chatbot"]:.2f} / {r["w_medico"]:.2f})'
    h4.markdown(f'<div class="ev-kpi" style="background:{ui.MORADO}"><div class="l" style="color:#fff">{etiqueta_final}'
                f'</div><div class="v" style="color:#fff">{ui.fmt(r["final"], 2)}</div></div>',
                unsafe_allow_html=True)

    st.markdown('<div class="ev-seccion">Calificación y criterio por competencia</div>', unsafe_allow_html=True)
    caso = ed.obtener_caso(f["clave_caso"]) or {}
    criterios = ed.competencias_de_caso(caso)
    bot_c = {c.get("clave"): c for c in ed._a_json(bot.get("competencias"), [])}
    med_c = {}
    for e in medicos:
        for c in ed._a_json(e.get("criterios"), []):
            med_c.setdefault(c.get("clave"), []).append(c)

    cab = st.columns([1.3, 2.2, 2.2, 0.8])
    for col, t in zip(cab, ["Competencia · dominio", "🤖 Chatbot evaluador: puntaje y criterio",
                            "🩺 Médico evaluador: puntaje y observación", "Diferencia"]):
        col.markdown(f"**{t}**")

    filas_comp = []
    for c in criterios:
        b = bot_c.get(c["clave"], {})
        ms = med_c.get(c["clave"], [])
        mp = ed.promedio([m.get("puntaje") for m in ms])
        com = " / ".join(m.get("comentario", "") for m in ms if m.get("comentario"))
        bp = b.get("puntaje")
        cols = st.columns([1.3, 2.2, 2.2, 0.8])
        cols[0].markdown(f'<b style="font-size:13px">{ui.e(c["categoria"].title())} · {ui.e(c["dominio"])}</b><br>'
                         f'<span style="font-size:12px">{ui.e(c["texto"])}</span>', unsafe_allow_html=True)
        if b:
            evid = "; ".join(f'{x["id"]}: "{x.get("cita", "")}"' + (f' (#{x["mensaje"]})' if x.get("mensaje") else "")
                             for x in b.get("evidencias", []))
            cols[1].markdown(f'<div class="ev-tarjeta"><b style="font-size:20px;color:{ui.MORADO}">{bp}</b> '
                             f'{ui.badge(b.get("nivel"), "virtual")}<div class="ev-txt">{ui.e(b.get("criterio"))}</div>'
                             f'<div style="background:#F6F7F9;border-radius:6px;padding:4px 8px;font-size:11px;margin-top:6px">'
                             f'Evidencia: {ui.e(evid) or "—"}</div></div>', unsafe_allow_html=True)
        else:
            cols[1].markdown('<div class="ev-tarjeta"><i>Sin evaluación del chatbot</i></div>', unsafe_allow_html=True)
        if ms:
            cols[2].markdown(f'<div class="ev-tarjeta"><b style="font-size:20px;color:{ui.MORADO}">{ui.fmt(mp, 0) if len(ms) == 1 else ui.fmt(mp)}</b> '
                             f'{ui.badge(ed.nivel_de_puntaje(mp), "virtual")}<div class="ev-txt">{ui.e(com) or "<i>Sin comentario</i>"}</div></div>',
                             unsafe_allow_html=True)
        else:
            cols[2].markdown('<div class="ev-tarjeta"><i>Sin evaluación del médico</i></div>', unsafe_allow_html=True)
        dif_txt = "—"
        if bp is not None and mp is not None:
            d = mp - bp
            dn = abs((ed.indice_nivel(mp) or 0) - (ed.indice_nivel(bp) or 0))
            if abs(d) < 0.5:
                dif_txt = "Δ 0 · acuerdo"
                cols[3].markdown('<div style="color:#1E7B45;font-weight:700;text-align:center">Δ 0<br>acuerdo</div>', unsafe_allow_html=True)
            else:
                dif_txt = f"Δ {abs(d):.0f} pts · {dn} nivel(es)"
                color = "#C0392B" if dn >= 1 else "#B7791F"
                cols[3].markdown(f'<div style="color:{color};font-weight:700;text-align:center">Δ {abs(d):.0f} pts<br>{dn} nivel(es)</div>',
                                 unsafe_allow_html=True)
        else:
            cols[3].write("—")
        filas_comp.append({"dominio": c["dominio"], "texto": c["texto"], "bot_p": bp, "bot_n": b.get("nivel"),
                           "bot_crit": b.get("criterio", ""), "med_p": ui.fmt(mp) if mp else None,
                           "med_n": ed.nivel_de_puntaje(mp) if mp else None, "med_com": com, "dif": dif_txt})

    if medicos and any(m.get("comentarios_generales") for m in medicos):
        st.markdown("**Comentarios generales del médico**")
        for m in medicos:
            if m.get("comentarios_generales"):
                st.markdown(f'<div class="ev-tarjeta ev-txt">{ui.e(m["comentarios_generales"])}</div>', unsafe_allow_html=True)

    a, b, c3, d = st.columns([2, 1.2, 1.6, 1.6])
    with b.popover("Marcar para revisión", use_container_width=True):
        txt = st.text_area("Motivo", key="cmp_rev_txt")
        if st.button("Guardar", key="cmp_rev_ok"):
            ok = ed.reportar_chatbot(f["matricula"], f["clave_caso"], "", txt, "revision", _usuario(), "admin",
                                     bot.get("prompt_version"))
            (st.success if ok else st.error)("Marcado para revisión" if ok else "No se pudo guardar")
    if bot and c3.button("Ver evaluación completa del chatbot", use_container_width=True, key="cmp_full"):
        st.session_state["adm_dual_vista"] = "completa"
        st.rerun()
    try:
        d.download_button("Descargar PDF comparativo", _pdf_comparativo(f, filas_comp, r),
                          file_name=f"comparativo_{f['matricula']}_{f['clave_caso']}.pdf", mime="application/pdf",
                          type="primary", use_container_width=True, key="cmp_pdf")
    except Exception as e:
        d.caption(f"PDF no disponible: {e}")


# ===================== EVALUACIÓN COMPLETA DEL CHATBOT =====================

def _vista_completa(f):
    if st.button("← Comparativo", key="full_back"):
        st.session_state["adm_dual_vista"] = "comparativo"
        st.rerun()
    bot = f.get("eval_chatbot")
    if not bot:
        st.info("No hay evaluación del chatbot para este caso.")
        return
    st.markdown('<div class="ev-titulo">Evaluación completa del chatbot</div>', unsafe_allow_html=True)
    comps = ed._a_json(bot.get("competencias"), [])
    st.markdown(f'<div class="ev-cab"><b>{ui.e(f["nombre"])}</b> ({ui.e(f["matricula"])}) · {ui.e(f["clave_caso"])} · '
                f'{ui.e(f["modalidad"])} &nbsp; Modelo evaluador: <b>{ui.e(bot.get("modelo"))}</b> · Prompt '
                f'<b>{ui.e(bot.get("prompt_version"))}</b> · Rúbrica General ({len(comps)} dominios) · '
                f'{ui.e(str(bot.get("fecha_evaluacion", ""))[:16].replace("T", " "))}'
                f'<span style="float:right">Promedio chatbot: <b style="color:{ui.MORADO}">{ui.fmt(bot.get("calificacion"))}</b> · '
                f'Nivel global: <b>{ui.e(bot.get("nivel_global"))}</b></span></div>', unsafe_allow_html=True)
    col_a, col_b = st.columns([1.5, 1])
    with col_a:
        for c in comps:
            st.markdown(ui.tarjeta_chatbot(c), unsafe_allow_html=True)
        if bot.get("resumen"):
            st.markdown(f'<div class="ev-tarjeta"><div class="ev-et">Resumen del chatbot</div>'
                        f'<div class="ev-txt">{ui.e(bot["resumen"])}</div></div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="ev-seccion">Transcripción con evidencias marcadas</div>', unsafe_allow_html=True)
        st.markdown(ui.transcripcion_html(ed._a_json(bot.get("transcripcion"), []), ui.marcados_de(comps)),
                    unsafe_allow_html=True)
        x1, x2 = st.columns(2)
        x1.download_button("Exportar JSON de la evaluación",
                           json.dumps(bot, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
                           file_name=f"eval_chatbot_{f['matricula']}_{f['clave_caso']}.json",
                           mime="application/json", use_container_width=True, key="full_json")
        with x2.popover("Reportar criterio incorrecto", use_container_width=True):
            comp = st.selectbox("Competencia", [c.get("texto") for c in comps], key="full_rep_comp")
            txt = st.text_area("¿Qué está mal en el criterio?", key="full_rep_txt")
            if st.button("Enviar reporte", key="full_rep_ok"):
                ok = ed.reportar_chatbot(f["matricula"], f["clave_caso"], comp, txt, "criterio_incorrecto",
                                         _usuario(), "admin", bot.get("prompt_version"))
                (st.success if ok else st.error)("Reporte guardado" if ok else "No se pudo guardar")


# ===================== ENTRADA =====================

def mostrar():
    """Se muestra al inicio de la pestaña 'Evaluación' del administrador."""
    ui.css()
    if not ed.tablas_dual_disponibles():
        st.warning("La evaluación dual necesita las tablas nuevas. Agrega el secreto **DATABASE_URL** para que la app "
                   "las cree sola, o ejecuta una vez `migraciones/002_evaluacion_dual.sql` en el SQL Editor de Supabase. "
                   "Solo agrega columnas y tablas; no borra nada.")
        return False

    vista = st.session_state.get("adm_dual_vista")
    fila = st.session_state.get("adm_dual_fila")
    configs = ed.obtener_ponderaciones()

    if vista in ("comparativo", "completa") and fila:
        # Recargar la fila con datos frescos
        frescas = [x for x in ed.construir_filas(circuito_filtro=[fila["circuito"]])
                   if x["matricula"] == fila["matricula"] and x["clave_caso"] == fila["clave_caso"]]
        fila = frescas[0] if frescas else fila
        if vista == "comparativo":
            _vista_comparativo(fila, configs)
        else:
            _vista_completa(fila)
        return True

    filas = ed.construir_filas()
    if st.session_state.get("adm_dual_msg"):
        st.success(st.session_state.pop("adm_dual_msg"))
    _panel_ponderacion(filas, configs)
    _tabla_comparativa(filas, configs)
    return False
