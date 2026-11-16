# components/ui_evaluacion.py
"""Estilos y piezas visuales compartidas por las pantallas de evaluación dual."""
import html

import streamlit as st

from utils.evaluacion_dual import NIVELES, nivel_de_puntaje

MORADO = "#70257E"


def css():
    st.markdown(f"""
    <style>
      .ev-titulo {{ text-align:center; color:{MORADO}; font-family:'Poppins',sans-serif; font-size:34px;
                   font-weight:700; margin:0.2rem 0 1rem; }}
      .ev-seccion {{ color:#252A38; font-size:21px; font-weight:600; border-left:4px solid {MORADO};
                    padding-left:0.8rem; margin:1rem 0 0.8rem; }}
      .ev-tarjeta {{ background:#FFFFFF; border:1px solid #E5E7EC; border-radius:12px; padding:14px 16px;
                    margin-bottom:12px; }}
      .ev-cab {{ background:#FFFFFF; border:1px solid #E5E7EC; border-radius:12px; padding:12px 16px;
                margin-bottom:14px; font-size:14px; color:#303442; }}
      .ev-badge {{ display:inline-block; white-space:nowrap; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }}
      .ev-virtual {{ background:#F3E8FF; color:{MORADO}; }}
      .ev-estatico {{ background:#E0E7FF; color:#3730A3; }}
      .ev-estandarizado {{ background:#FEF3C7; color:#92400E; }}
      .ev-pend {{ background:#FDECEC; color:#C0392B; }}
      .ev-ok {{ background:#E8F7EE; color:#1E7B45; }}
      .ev-gris {{ background:#EEF0F4; color:#626779; }}
      .ev-dom {{ display:inline-block; background:#F3E8FF; color:{MORADO}; font-size:11px; font-weight:600;
                padding:2px 8px; border-radius:6px; margin-right:6px; }}
      .ev-crit {{ font-weight:600; color:#252A38; font-size:15px; }}
      .ev-nota {{ float:right; color:{MORADO}; font-weight:700; font-size:16px; }}
      .ev-niveles {{ display:flex; gap:6px; margin:8px 0; }}
      .ev-nivel {{ flex:1; border:1px solid #E5E7EC; border-radius:8px; padding:6px 7px; font-size:11px;
                  color:#626779; background:#FAFAFB; line-height:1.25; }}
      .ev-nivel b {{ color:#303442; font-size:12px; display:block; }}
      .ev-nivel.sel {{ border:2px solid {MORADO}; background:#F7EEF9; }}
      .ev-et {{ color:{MORADO}; font-weight:600; font-size:12px; margin-top:6px; }}
      .ev-txt {{ font-size:13px; color:#303442; }}
      .ev-evid {{ display:inline-block; background:{MORADO}; color:#fff; font-size:10px; font-weight:700;
                 border-radius:4px; padding:1px 5px; margin-right:4px; }}
      .ev-chat {{ background:#FFFFFF; border:1px solid #E5E7EC; border-radius:12px; padding:10px;
                 max-height:560px; overflow-y:auto; }}
      .ev-meta {{ font-size:11px; color:#8A8FA0; margin:6px 0 2px; }}
      .ev-msg-e {{ background:{MORADO}; color:#fff; border-radius:10px; padding:7px 10px; margin-left:18%;
                  font-size:13px; }}
      .ev-msg-p {{ background:#EEF0F4; color:#303442; border-radius:10px; padding:7px 10px; margin-right:18%;
                  font-size:13px; }}
      .ev-marcado {{ outline:3px solid #F5B700; }}
      .ev-kpi {{ background:#FFFFFF; border:1px solid #E5E7EC; border-radius:12px; padding:12px; text-align:center; }}
      .ev-kpi .v {{ font-size:28px; font-weight:700; color:{MORADO}; }}
      .ev-kpi .l {{ font-size:12px; color:#303442; }}
      .ev-kpi .s {{ font-size:11px; color:#1E7B45; }}
      .ev-alerta {{ background:#FDECEC; color:#7A1F1F; border-radius:8px; padding:8px 12px; font-size:13px; }}
    </style>
    """, unsafe_allow_html=True)


def e(texto):
    return html.escape(str(texto if texto is not None else ""))


def badge_modalidad(modalidad):
    clase = {"Virtual": "ev-virtual", "Estático": "ev-estatico", "Estandarizado": "ev-estandarizado"}.get(modalidad, "ev-gris")
    return f'<span class="ev-badge {clase}">{e(modalidad)}</span>'


def badge(texto, tipo="gris"):
    return f'<span class="ev-badge ev-{tipo}">{e(texto)}</span>'


def fmt(v, dec=1):
    return "—" if v is None else f"{float(v):.{dec}f}"


def niveles_html(descriptores, puntaje_sel=None, mostrar_desc=True):
    sel = nivel_de_puntaje(puntaje_sel) if puntaje_sel else None
    cajas = []
    for (nombre, lo, hi), desc in zip(NIVELES, descriptores or [""] * 5):
        clase = "ev-nivel sel" if nombre == sel else "ev-nivel"
        d = e(desc[:95] + ("…" if len(desc) > 95 else "")) if mostrar_desc else ""
        cajas.append(f'<div class="{clase}" title="{e(desc)}"><b>{nombre} {lo}–{hi}</b>{d}</div>')
    return f'<div class="ev-niveles">{"".join(cajas)}</div>'


def transcripcion_html(transcripcion, marcados=None):
    """marcados: dict {numero_mensaje: [ids de evidencia]}"""
    marcados = marcados or {}
    if not transcripcion:
        return '<div class="ev-chat"><i>Sin conversación registrada.</i></div>'
    partes = []
    for m in transcripcion:
        ids = marcados.get(m["n"], [])
        etiquetas = "".join(f'<span class="ev-evid">{i}</span>' for i in ids)
        hora = f" · {e(m['hora'][11:16])}" if m.get("hora") and len(m["hora"]) >= 16 else ""
        clase = "ev-msg-e" if m["rol"] == "Estudiante" else "ev-msg-p"
        extra = " ev-marcado" if ids else ""
        partes.append(f'<div class="ev-meta">{etiquetas}#{m["n"]} · {e(m["rol"])}{hora}</div>'
                      f'<div class="{clase}{extra}">{e(m["texto"])}</div>')
    return f'<div class="ev-chat">{"".join(partes)}</div>'


def tarjeta_chatbot(c, nota_medico=None):
    """Tarjeta de una competencia evaluada por el chatbot."""
    tu = f' <span style="color:#626779;font-weight:500;font-size:13px">· tú: {fmt(nota_medico, 0)}</span>' if nota_medico else ""
    evid = " · ".join(
        f'<span class="ev-evid">{e(x["id"])}</span>'
        + (f'#{x["mensaje"]} ' if x.get("mensaje") else "")
        + e(x.get("cita", "")) for x in c.get("evidencias", [])
    ) or "<i>Sin evidencias citadas</i>"
    subir = (f'<div class="ev-et">Para subir de nivel</div><div class="ev-txt">{e(c.get("para_subir"))}</div>'
             if c.get("para_subir") else "")
    from utils.evaluacion_dual import _descriptores_para
    return (f'<div class="ev-tarjeta"><span class="ev-dom">{e(c.get("dominio"))}</span>'
            f'<span class="ev-crit">{e(c.get("texto"))}</span>'
            f'<span class="ev-nota">{c.get("puntaje")} / 10{tu}</span>'
            f'{niveles_html(_descriptores_para(c.get("dominio"), c.get("texto")), c.get("puntaje"), mostrar_desc=False)}'
            f'<div class="ev-et">Criterio del chatbot</div><div class="ev-txt">{e(c.get("criterio"))}</div>'
            f'<div class="ev-et">Evidencias citadas</div><div class="ev-txt">{evid}</div>{subir}</div>')


def marcados_de(competencias):
    marcados = {}
    for c in competencias:
        for x in c.get("evidencias", []):
            if x.get("mensaje"):
                marcados.setdefault(int(x["mensaje"]), []).append(x["id"])
    return marcados
