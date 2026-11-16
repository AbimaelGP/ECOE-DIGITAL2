# escenas/escena_admin_confiabilidad.py
"""Pestaña 'Confiabilidad IA': concordancia chatbot evaluador vs médico evaluador."""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import ui_evaluacion as ui
from utils import evaluacion_dual as ed

UMBRAL_DOMINIO = 0.60


def _kpi(col, valor, etiqueta, sub=""):
    col.markdown(f'<div class="ev-kpi"><div class="v">{valor}</div><div class="l">{etiqueta}</div>'
                 f'<div class="s">{sub}</div></div>', unsafe_allow_html=True)


def mostrar():
    ui.css()
    if not ed.tablas_dual_disponibles():
        st.warning("Primero aplica la migración 002 (ver pestaña Evaluación).")
        return

    filas = ed.construir_filas()
    st.markdown('<div class="ev-seccion">Concordancia chatbot evaluador vs médico evaluador</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    examenes = sorted({str(f["fecha_examen"]) for f in filas if f["fecha_examen"]})
    areas = sorted({f["area"] for f in filas})
    exam = c1.selectbox("Examen", ["Todos"] + examenes, key="conf_exam")
    modas = c2.multiselect("Modalidad", ["Virtual", "Estático"], default=["Virtual", "Estático"], key="conf_moda")
    area = c3.selectbox("Área", ["Todas"] + areas, key="conf_area")

    sel = [f for f in filas
           if (exam == "Todos" or str(f["fecha_examen"]) == exam)
           and f["modalidad"] in modas and (area == "Todas" or f["area"] == area)]
    pares = ed.pares_criterio(sel)
    m = ed.metricas(pares)
    estaciones = sum(1 for f in sel if f["realizada"])
    pares_est = [(ed.nota_chatbot(f), ed.nota_medico(f), f) for f in sel]
    pares_est = [(b, md, f) for b, md, f in pares_est if b is not None and md is not None]

    if not m:
        st.info("Todavía no hay evaluaciones pareadas (chatbot + médico) con estos filtros. "
                "Las métricas aparecen en cuanto haya casos evaluados por ambos.")
        return

    k = st.columns(5)
    _kpi(k[0], len(pares_est), "Evaluaciones pareadas", f"de {estaciones} estaciones · {m['n']} criterios")
    _kpi(k[1], ui.fmt(m["icc"], 2), "ICC (2,1) · acuerdo absoluto", ed.interpretar_icc(m["icc"]))
    _kpi(k[2], ui.fmt(m["kappa"], 2), "Kappa ponderada · nivel", ed.interpretar_kappa(m["kappa"]))
    _kpi(k[3], f"{m['acuerdo_1']:.0f}%", "Acuerdo ±1 nivel", f"{m['acuerdo_exacto']:.0f}% acuerdo exacto")
    _kpi(k[4], ui.fmt(m["mae"]), "Error absoluto medio (pts)", f"Sesgo chatbot: {m['sesgo']:+.1f}")
    st.caption("ICC, kappa, acuerdo y error se calculan por criterio (cada competencia calificada por ambos). "
               "El sesgo positivo indica que el chatbot califica más alto que el médico.")

    g1, g2 = st.columns([1.1, 1])
    with g1:
        with st.container(border=True):
            ver_ba = st.toggle("Gráfico Bland-Altman", key="conf_ba")
            if pares_est:
                xs = [md for _, md, _ in pares_est]
                ys = [b for b, _, _ in pares_est]
                textos = [f"{f['matricula']} · {f['clave_caso']}" for _, _, f in pares_est]
                fig = go.Figure()
                if not ver_ba:
                    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", text=textos, name="Estudiante · caso",
                                             marker=dict(color="#9B59B6", size=9, opacity=0.75),
                                             hovertemplate="%{text}<br>Médico %{x:.1f} · Chatbot %{y:.1f}<extra></extra>"))
                    fig.add_trace(go.Scatter(x=[1, 10], y=[1, 10], mode="lines", name="acuerdo perfecto (y = x)",
                                             line=dict(color="#A93266", dash="dash")))
                    fig.update_layout(title="Calificación del chatbot vs médico (por estudiante y caso)",
                                      xaxis_title="Médico evaluador", yaxis_title="Chatbot evaluador",
                                      xaxis=dict(range=[0.5, 10.5]), yaxis=dict(range=[0.5, 10.5]))
                else:
                    medias = [(a + b) / 2 for a, b in zip(xs, ys)]
                    difs = [b - a for a, b in zip(xs, ys)]
                    md = sum(difs) / len(difs)
                    sd = (sum((d - md) ** 2 for d in difs) / max(1, len(difs) - 1)) ** 0.5
                    fig.add_trace(go.Scatter(x=medias, y=difs, mode="markers", text=textos, name="Estudiante · caso",
                                             marker=dict(color="#9B59B6", size=9, opacity=0.75)))
                    for y, nombre, estilo in [(md, f"Sesgo {md:+.2f}", "solid"), (md + 1.96 * sd, "+1.96 DE", "dash"),
                                              (md - 1.96 * sd, "−1.96 DE", "dash")]:
                        fig.add_hline(y=y, line_dash=estilo, line_color="#A93266", annotation_text=nombre)
                    fig.update_layout(title="Bland-Altman: diferencia (chatbot − médico) vs promedio",
                                      xaxis_title="Promedio de ambas calificaciones", yaxis_title="Chatbot − Médico")
                fig.update_layout(height=430, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                                  margin=dict(l=40, r=20, t=50, b=40), legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sin pares a nivel estudiante para graficar.")

    with g2:
        with st.container(border=True):
            st.markdown("**ICC por dominio evaluado**")
            por_dom = {}
            for p in pares:
                por_dom.setdefault(p["dominio"], []).append(p)
            bajos = []
            for dom, lista in sorted(por_dom.items(), key=lambda kv: -len(kv[1])):
                v = ed.icc_2_1([p["chatbot"] for p in lista], [p["medico"] for p in lista])
                ancho = max(0, min(1, v or 0)) * 100
                color = "#A93266" if v is not None and v < UMBRAL_DOMINIO else ui.MORADO
                if v is not None and v < UMBRAL_DOMINIO:
                    bajos.append(dom)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin:6px 0;font-size:13px">'
                    f'<div style="width:38%">{ui.e(dom)} <span style="color:#8A8FA0">(n={len(lista)})</span></div>'
                    f'<div style="flex:1;background:#EEF0F4;border-radius:6px;height:14px">'
                    f'<div style="width:{ancho:.0f}%;background:{color};height:14px;border-radius:6px"></div></div>'
                    f'<b style="width:42px;text-align:right">{ui.fmt(v, 2) if v is not None else "n<3"}</b></div>',
                    unsafe_allow_html=True)
            for dom in bajos:
                st.markdown(f'<div class="ev-alerta">⚠ <b>{ui.e(dom)}</b> por debajo de {UMBRAL_DOMINIO:.2f}: '
                            f'revisar el prompt del chatbot evaluador para este dominio.</div>', unsafe_allow_html=True)
            st.download_button("Exportar datos (CSV)", pd.DataFrame(pares).to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"confiabilidad_chatbot_{datetime.now():%Y%m%d}.csv", mime="text/csv",
                               key="conf_csv")

    try:
        from utils.supabase_client import supabase
        reps = supabase.table("reportes_chatbot").select("*").order("fecha", desc=True).limit(50).execute().data or []
    except Exception:
        reps = []
    if reps:
        with st.expander(f"Reportes sobre el chatbot ({len(reps)})"):
            st.dataframe(pd.DataFrame(reps)[["fecha", "tipo", "matricula", "clave_caso", "competencia", "comentario",
                                             "reportado_por", "prompt_version"]], use_container_width=True, hide_index=True)
