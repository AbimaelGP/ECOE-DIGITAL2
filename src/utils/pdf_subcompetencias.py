# utils/pdf_subcompetencias.py
"""Página extra del PDF: gráfica del nivel obtenido en cada subcompetencia
(escala 1–10 con las 5 bandas de la Rúbrica General)."""
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from utils.evaluacion_dual import NIVELES, nivel_de_puntaje

MORADO = colors.HexColor("#70257E")
GRIS = colors.HexColor("#626779")
# Bandas de nivel de claro a oscuro (mismo morado institucional)
BANDAS = [colors.HexColor(c) for c in ("#F3E8FF", "#E4CCF5", "#CFA6E8", "#B27BD4", "#8F4FB5")]
ORDEN_AREAS = ["BÁSICAS", "ESPECÍFICAS", "PROFESIONALES"]


def _partir(texto, max_chars):
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        if len(actual) + len(p) + 1 > max_chars:
            lineas.append(actual)
            actual = p
        else:
            actual = f"{actual} {p}".strip()
    if actual:
        lineas.append(actual)
    return lineas


def generar_pagina_subcompetencias(items, ruta_pdf, matricula="", nombre=""):
    """items: competencias evaluadas [{categoria, dominio, texto, puntaje, nivel}]"""
    c = canvas.Canvas(ruta_pdf, pagesize=letter)
    ancho, alto = letter
    margen = 40
    y = alto - 50

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawCentredString(ancho / 2, y, "NIVEL OBTENIDO POR SUBCOMPETENCIA")
    y -= 16
    c.setFont("Helvetica", 8)
    c.drawString(margen, y, f"MATRÍCULA: {matricula}")
    y -= 11
    c.drawString(margen, y, f"NOMBRE: {nombre}")
    y -= 22

    # Escala y leyenda
    x0, x1 = margen + 205, ancho - margen - 40          # zona de la barra
    escala = (x1 - x0) / 10.0
    for (nombre_nivel, lo, hi), color in zip(NIVELES, BANDAS):
        xa, xb = x0 + (lo - 1) * escala, x0 + hi * escala
        c.setFillColor(color)
        c.rect(xa, y - 6, xb - xa, 18, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 6)
        c.drawCentredString((xa + xb) / 2, y + 4, nombre_nivel.upper())
        c.setFont("Helvetica", 6)
        c.drawCentredString((xa + xb) / 2, y - 3, f"{lo}–{hi}")
    y -= 22

    def clave_area(it):
        cat = (it.get("categoria") or "").upper()
        return ORDEN_AREAS.index(cat) if cat in ORDEN_AREAS else 99

    area_actual, contador = None, 0
    for it in sorted(items, key=clave_area):
        cat = (it.get("categoria") or "General").upper()
        if cat != area_actual:
            area_actual, contador = cat, 0
            y -= 6
            c.setFillColor(MORADO)
            c.rect(margen, y - 3, ancho - 2 * margen, 14, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(margen + 6, y + 1, cat)
            y -= 18
        contador += 1

        texto = re.sub(r"^\s*\d+\.\s*", "", it.get("texto", ""))
        lineas = _partir(f"{cat[:1]}{contador}  {it.get('dominio', '')}: {texto}", 52)[:3]
        alto_fila = max(24, 10 * len(lineas) + 6)

        if y - alto_fila < 60:                      # salto de página
            c.showPage()
            y = alto - 60

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 7)
        for i, linea in enumerate(lineas):
            c.drawString(margen, y - i * 9, linea)

        # Fondo con las 5 bandas y barra del puntaje
        yb = y - 8
        for (_, lo, hi), color in zip(NIVELES, BANDAS):
            c.setFillColor(color)
            c.rect(x0 + (lo - 1) * escala, yb, (hi - lo + 1) * escala, 12, stroke=0, fill=1)
        puntaje = float(it.get("puntaje") or 0)
        c.setFillColor(colors.HexColor("#3B0A45"))
        c.rect(x0, yb + 4, max(0, puntaje) * escala, 4, stroke=0, fill=1)
        # marcador en el puntaje obtenido
        xm = x0 + max(0, puntaje) * escala
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#3B0A45"))
        c.setLineWidth(1.2)
        c.circle(xm, yb + 6, 4, stroke=1, fill=1)
        c.setStrokeColor(GRIS)
        c.setLineWidth(0.3)
        for k in range(11):
            c.line(x0 + k * escala, yb - 2, x0 + k * escala, yb)
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(colors.black)
        c.drawString(x1 + 6, yb + 3, f"{puntaje:.0f}")
        c.setFont("Helvetica", 6.5)
        c.setFillColor(GRIS)
        c.drawString(x1 + 18, yb + 3, (it.get("nivel") or nivel_de_puntaje(puntaje) or "")[:12])
        y -= alto_fila + 6

    # Escala numérica al pie
    c.setFont("Helvetica", 6.5)
    c.setFillColor(GRIS)
    for k in range(0, 11):
        c.drawCentredString(x0 + k * escala, y + 2, str(k))
    c.drawString(margen, 40, "Escala 1–10 de la Rúbrica General. La barra muestra el puntaje obtenido en cada subcompetencia.")
    c.save()
    return ruta_pdf


def generar_resumen_circuito(estaciones, ruta_pdf, matricula="", nombre="", circuito=""):
    """Primera página del PDF cuando el circuito tiene varias estaciones.
    estaciones: [{area, clave_caso, modalidad, evaluador, calificacion (o None), estado}]"""
    from utils.evaluacion_dual import promedio
    c = canvas.Canvas(ruta_pdf, pagesize=letter)
    ancho, alto = letter
    margen = 40
    y = alto - 50
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawCentredString(ancho / 2, y, "UNIVERSIDAD AUTÓNOMA DE CHIHUAHUA")
    y -= 14
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(ancho / 2, y, "FACULTAD DE MEDICINA Y CIENCIAS BIOMÉDICAS")
    y -= 14
    c.drawCentredString(ancho / 2, y, "RESUMEN DEL CIRCUITO ECOE")
    y -= 26
    c.setFont("Helvetica", 8.5)
    c.drawString(margen, y, f"MATRÍCULA: {matricula}")
    c.drawString(margen + 250, y, f"CIRCUITO: {circuito}")
    y -= 12
    c.drawString(margen, y, f"NOMBRE: {nombre}")
    y -= 26

    # Tabla de estaciones
    cols = [("ESTACIÓN", margen), ("ÁREA", margen + 52), ("CASO", margen + 205), ("MODALIDAD", margen + 260),
            ("EVALUÓ", margen + 345), ("CALIF.", margen + 410), ("NIVEL", margen + 455)]
    c.setFillColor(MORADO)
    c.rect(margen, y - 4, ancho - 2 * margen, 16, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7.5)
    for t, x in cols:
        c.drawString(x + 4, y + 1, t)
    y -= 18
    califs = []
    for i, e in enumerate(estaciones, 1):
        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#F6F0FA"))
            c.rect(margen, y - 5, ancho - 2 * margen, 16, stroke=0, fill=1)
        cal = e.get("calificacion")
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 7.5)
        valores = [str(i), str(e.get("area") or "")[:30], e.get("clave_caso") or "", e.get("modalidad") or "",
                   e.get("evaluador") or "—", f"{cal:.2f}" if cal is not None else "—",
                   (nivel_de_puntaje(cal) or "") if cal is not None else (e.get("estado") or "Sin evaluación")]
        for (t, x), v in zip(cols, valores):
            c.drawString(x + 4, y, v)
        if cal is not None:
            califs.append(cal)
        y -= 16

    # Calificación del circuito
    final = promedio(califs)
    y -= 14
    c.setFillColor(MORADO)
    c.rect(ancho - margen - 180, y - 34, 180, 46, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(ancho - margen - 90, y + 2, "CALIFICACIÓN DEL CIRCUITO")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(ancho - margen - 90, y - 18, f"{final:.2f}" if final is not None else "—")
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(ancho - margen - 90, y - 29, (nivel_de_puntaje(final) or "").upper() if final is not None else "")
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 7)
    texto = ("Promedio de las estaciones evaluadas. El chatbot evalúa las estaciones virtuales y estáticas; "
             "las estandarizadas las evalúa el médico. La calificación final oficial combina esta evaluación "
             "con la del médico según la ponderación vigente y se consulta en el sistema.")
    for k, linea in enumerate(_partir(texto, 75)):
        c.drawString(margen, y - k * 10, linea)
    y -= 62

    # Gráfica: calificación por estación sobre las 5 bandas de nivel
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margen, y, "NIVEL OBTENIDO POR ESTACIÓN")
    y -= 18
    x0, x1 = margen + 150, ancho - margen - 60
    escala = (x1 - x0) / 10.0
    for (nombre_nivel, lo, hi), color in zip(NIVELES, BANDAS):
        xa, xb = x0 + (lo - 1) * escala, x0 + hi * escala
        c.setFillColor(color)
        c.rect(xa, y - 6, xb - xa, 18, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 6)
        c.drawCentredString((xa + xb) / 2, y + 4, nombre_nivel.upper())
        c.setFont("Helvetica", 6)
        c.drawCentredString((xa + xb) / 2, y - 3, f"{lo}–{hi}")
    y -= 26
    for i, e in enumerate(estaciones, 1):
        cal = e.get("calificacion")
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 7.5)
        c.drawString(margen, y + 2, f"{i}. {str(e.get('area') or '')[:22]} ({e.get('clave_caso')})")
        for (_, lo, hi), color in zip(NIVELES, BANDAS):
            c.setFillColor(color)
            c.rect(x0 + (lo - 1) * escala, y - 2, (hi - lo + 1) * escala, 14, stroke=0, fill=1)
        if cal is not None:
            c.setFillColor(colors.HexColor("#3B0A45"))
            c.rect(x0, y + 3, cal * escala, 4, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.HexColor("#3B0A45"))
            c.setLineWidth(1.2)
            c.circle(x0 + cal * escala, y + 5, 4, stroke=1, fill=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(x1 + 6, y + 2, f"{cal:.2f}")
        else:
            c.setFillColor(GRIS)
            c.setFont("Helvetica", 7)
            c.drawString(x1 + 6, y + 2, "—")
        y -= 22
    c.setFont("Helvetica", 6.5)
    c.setFillColor(GRIS)
    for k in range(0, 11):
        c.drawCentredString(x0 + k * escala, y + 8, str(k))
    c.drawString(margen, 40, "En las páginas siguientes: carátula y nivel por subcompetencia de cada estación.")
    c.save()
    return ruta_pdf
