# -*- coding: utf-8 -*-
# evaluador_api.py - API para generar solo la carátula PDF sin interfaz gráfica
import os
import re
import traceback
import logging
from datetime import datetime

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import simpleSplit
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False
    print("⚠️ reportlab no instalado. Ejecuta: pip install reportlab")

from . import config
from .evaluador_ecoe import EvaluadorECOE 
#le movi a estas rutas

logger = logging.getLogger("ECOE.API")
logging.basicConfig(level=logging.WARNING) # 👈 Ocultará los INFO, solo mostrará WARNING y ERROR

_STOPWORDS = {"y", "de", "del", "la", "el", "los", "las", "en", "con",
              "a", "para", "por", "o", "u", "al", "un", "una"}

class GeneradorCaratula:
    """Genera el PDF de la carátula a partir de los datos de evaluación."""

    @staticmethod
    def _codigo_area(nombre):
        palabras = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", nombre or "")
        sig = [p for p in palabras if p.lower() not in _STOPWORDS]
        codigo = "".join(p[0].upper() for p in sig)
        return codigo[:5] if codigo else "AREA"

    @staticmethod
    def _promedio_10(items):
        if not items:
            return 0.0
        valores = []
        for i in items:
            max_v = i["maxima"] if i["maxima"] > 0 else 1
            valores.append(i["puntuacion"] / max_v * 10)
        return sum(valores) / len(valores)

    @classmethod
    def _promedio_global_categorias(cls, cat_blocks):
        if not cat_blocks:
            return 0.0
        promedios = [cls._promedio_10(items) for _, items in cat_blocks]
        return sum(promedios) / len(promedios)

    @staticmethod
    def _nivel_desde_10(valor_10):
        pct = valor_10 * 10
        if pct >= 90:
            return "ESTRATÉGICO"
        if pct >= 60:
            return "AUTÓNOMO"
        if pct >= 40:
            return "RESOLUTIVO"
        if pct >= 20:
            return "RECEPTIVO"
        return "PREFORMAL"

    @staticmethod
    def _descripcion_nivel(nivel_des):
        return {
            "PREFORMAL": (
                "No se posee la competencia. No tiene nociones de la información."
            ),
            "RECEPTIVO": (
                "Se tiene recepción de la información, el desempeño es muy operativo. "
                "Requiere de la asesoría y supervisión continua."
            ),
            "RESOLUTIVO": (
                "Se resuelven problemas sencillos, hay labores de asistencia a otras "
                "personas, se tienen elementos técnicos de los procesos implicados en la "
                "competencia. Se poseen conceptos básicos. Requiere asesoría en situaciones "
                "específicas y/o complejas."
            ),
            "AUTÓNOMO": (
                "Hay autonomía en la actuación (no se requiere asesoría continua de otras "
                "personas), hay argumentación científica sólida. Se resuelven problemas de "
                "diversa índole con los elementos necesarios."
            ),
            "ESTRATÉGICO": (
                "Se plantean estrategias de cambio en la realidad. Hay creatividad e "
                "innovación. Hay altos niveles de impacto en la realidad. Se hacen análisis "
                "evolutivos y prospectivos para abordar mejor los problemas. Se consideran "
                "consecuencias de las diferentes opciones de resolución de los problemas "
                "del contexto."
            ),
        }.get(nivel_des, "")

    @staticmethod
    def _anonimizar_texto(texto):
        if not texto:
            return texto
        texto = re.sub(
            r'\b(El|La)\s+(Dr|Dra|Doctor|Doctora|Médico|Médica|Lic|Licenciado|Licenciada)\.?\s+'
            r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*',
            'El alumno', texto
        )
        texto = re.sub(
            r'\b(el|la)\s+(estudiante|alumno|alumna|sustentante)\s+'
            r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*',
            r'\1 alumno', texto
        )
        texto = re.sub(
            r'\b(Dr|Dra|Doctor|Doctora|Médico|Médica|Lic|Licenciado|Licenciada)\.?\s+'
            r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*',
            'el alumno', texto
        )
        texto = re.sub(
            r'\b(el|la)\s+(paciente|señor|señora|sr|sra|joven|niño|niña)\s+'
            r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*',
            r'\1 \2', texto
        )
        return texto

    @staticmethod
    def _observaciones_categoria(items):
        """Devuelve la primera oración de la primera debilidad no vacía, sin truncar."""
        for it in items:
            d = (it.get("debilidades") or "").strip()
            if not d:
                continue
            if d.lower() in ("—", "n/a", "-", "ninguna", "no aplica",
                             "no evaluado (modo respaldo)"):
                continue
            primera = re.split(r'[.!?]', d)[0].strip()
            if not primera:
                continue
            return primera
        return ""

    @classmethod
    def generar_pdf(cls, evaluacion, rubrica, ruta_pdf, matricula="", nombre=""):
        """
        Genera el PDF de la carátula.
        
        Args:
            evaluacion (dict): Resultado de la evaluación (JSON).
            rubrica (dict): Rúbrica procesada (JSON).
            ruta_pdf (str): Ruta donde guardar el PDF.
            matricula (str): Matrícula del estudiante.
            nombre (str): Nombre del estudiante.
        
        Returns:
            tuple: (bool, str) indicando éxito y mensaje.
        """
        if not REPORTLAB_DISPONIBLE:
            return False, "reportlab no instalado. Ejecuta: pip install reportlab"

        try:
            page_w, page_h = A4
            margin = 25

            c = rl_canvas.Canvas(ruta_pdf, pagesize=(page_w, page_h))

            col_categoria = HexColor("#7E5DC2")
            col_panel     = HexColor("#7030A0")
            col_codigo    = HexColor("#FFFFFF")
            col_desc      = HexColor("#F2F2F2")
            col_punt      = HexColor("#D9D9D9")
            col_blanco    = HexColor("#FFFFFF")
            col_borde     = HexColor("#B0B0B0")
            col_negro     = HexColor("#000000")

            # ---- Logos ----
            assets_dir = "assets"
            imagenes_logo = []
            if os.path.isdir(assets_dir):
                todas = [f for f in os.listdir(assets_dir)
                         if f.lower().endswith((".png", ".jpg", ".jpeg"))]
                img_izq = next((f for f in todas if "izq" in f.lower()), None)
                img_der = next((f for f in todas if "der" in f.lower()), None)
                if img_izq:
                    imagenes_logo.append(os.path.join(assets_dir, img_izq))
                if img_der:
                    imagenes_logo.append(os.path.join(assets_dir, img_der))
                for f in todas:
                    p = os.path.join(assets_dir, f)
                    if p not in imagenes_logo:
                        imagenes_logo.append(p)

            def draw_header():
                logo_size = 45
                logo_y = page_h - margin - logo_size

                if len(imagenes_logo) >= 1:
                    try:
                        c.drawImage(imagenes_logo[0], margin, logo_y,
                                    width=logo_size, height=logo_size,
                                    preserveAspectRatio=True, mask='auto')
                    except Exception as e:
                        logger.warning("Logo 1: %s", e)
                if len(imagenes_logo) >= 2:
                    try:
                        c.drawImage(imagenes_logo[1], page_w - margin - logo_size, logo_y,
                                    width=logo_size, height=logo_size,
                                    preserveAspectRatio=True, mask='auto')
                    except Exception as e:
                        logger.warning("Logo 2: %s", e)

                yy = page_h - margin - 4
                c.setFillColor(col_negro)
                for texto, size, gap in [
                    ("UNIVERSIDAD AUTÓNOMA DE CHIHUAHUA", 11, 13),
                    ("FACULTAD DE MEDICINA Y CIENCIAS BIOMÉDICAS", 10, 12),
                    ("RESULTADOS DE EXAMEN PROFESIONAL", 9, 11),
                    ("EXAMEN CLÍNICO OBJETIVO ESTRUCTURADO - MIXTO", 9, 16),
                ]:
                    c.setFont("Helvetica-Bold", size)
                    c.drawCentredString(page_w / 2, yy, texto)
                    yy -= gap

                c.setFont("Helvetica-Bold", 8)
                c.drawString(margin + 4, yy, "MATRÍCULA:")
                c.setFont("Helvetica", 8)
                c.drawString(margin + 70, yy, matricula or "____________________")
                yy -= 11
                c.setFont("Helvetica-Bold", 8)
                c.drawString(margin + 4, yy, "NOMBRE:")
                c.setFont("Helvetica", 8)
                c.drawString(margin + 70, yy, nombre or "______________________________________________")

                yy -= 14
                return yy

            categorias = rubrica.get("categorias", [])
            items_eval = evaluacion.get("evaluacion", [])
            cat_blocks = []
            for cat in categorias:
                nombre_cat = cat.get("nombre", "")
                items_cat = [i for i in items_eval if i.get("categoria") == nombre_cat]
                if items_cat:
                    cat_blocks.append((nombre_cat, items_cat))

            final10 = cls._promedio_global_categorias(cat_blocks)
            nivel_des = cls._nivel_desde_10(final10)
            descripcion_nivel = cls._descripcion_nivel(nivel_des)

            feedback_text = (evaluacion.get("observaciones") or "").strip()
            if not feedback_text:
                fortalezas = (evaluacion.get("fortalezas_globales") or "").strip()
                mejoras = (evaluacion.get("areas_mejora") or "").strip()
                partes = []
                if fortalezas and fortalezas not in ("—", "-"):
                    partes.append("Fortalezas: " + fortalezas)
                if mejoras and mejoras not in ("—", "-"):
                    partes.append("Áreas de mejora: " + mejoras)
                feedback_text = " ".join(partes)
            if not feedback_text:
                feedback_text = "Sin retroalimentación adicional."

            feedback_text = cls._anonimizar_texto(feedback_text)

            gap_col = 10
            total_w = page_w - 2 * margin
            left_w  = (total_w - gap_col) * 2 / 3
            right_w = (total_w - gap_col) / 3
            left_x  = margin
            right_x = margin + left_w + gap_col

            cat_h  = 15
            crit_h = 14
            col_w_code  = 36
            col_w_score = 36
            col_w_desc  = left_w - col_w_code - col_w_score

            min_bottom = margin + 10

            content_top = draw_header()

            # ================== COLUMNA DERECHA ==================
            y_right = content_top
            h_header = 14

            y_right -= h_header
            c.setFillColor(col_panel)
            c.rect(right_x, y_right, right_w, h_header, stroke=0, fill=1)
            c.setFillColor(col_blanco)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(right_x + right_w / 2,
                                y_right + (h_header / 2) - 3,
                                "PROMEDIO POR ÁREA")

            row_prom = 13
            for nombre_cat, items_cat in cat_blocks:
                y_right -= row_prom
                c.setFillColor(col_negro)
                c.setFont("Helvetica", 7)
                nombre_corto = nombre_cat if len(nombre_cat) <= 22 else nombre_cat[:21] + "…"
                c.drawString(right_x + 3, y_right + 3.5, nombre_corto)

                score_w = 28
                c.setFillColor(col_punt)
                c.rect(right_x + right_w - score_w, y_right,
                       score_w, row_prom, stroke=0, fill=1)
                c.setFillColor(col_negro)
                c.setFont("Helvetica-Bold", 7.5)
                c.drawCentredString(right_x + right_w - score_w / 2,
                                    y_right + 3.5,
                                    "{:.2f}".format(cls._promedio_10(items_cat)))

            y_right -= 8

            y_right -= h_header
            c.setFillColor(col_panel)
            c.rect(right_x, y_right, right_w, h_header, stroke=0, fill=1)
            c.setFillColor(col_blanco)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(right_x + right_w / 2,
                                y_right + (h_header / 2) - 3,
                                "CALIFICACIÓN FINAL")

            y_right -= 32
            c.setFillColor(col_negro)
            c.setFont("Helvetica-Bold", 22)
            c.drawCentredString(right_x + right_w / 2, y_right + 10,
                                "{:.2f}".format(final10))

            y_right -= 12

            y_right -= h_header
            c.setFillColor(col_panel)
            c.rect(right_x, y_right, right_w, h_header, stroke=0, fill=1)
            c.setFillColor(col_blanco)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(right_x + right_w / 2,
                                y_right + (h_header / 2) - 3,
                                "RESULTADOS POR COMPETENCIAS")

            chart_top = y_right - 10
            chart_h = 130
            label_w = 38
            bar_area_w = right_w - label_w - 15
            chart_x = right_x + 3

            n_bars = len(cat_blocks)
            if n_bars > 0:
                bar_h = min(10, (chart_h / n_bars) * 0.65)
                gap_bar = max(3, (chart_h - n_bars * bar_h) / max(n_bars - 1, 1))

                c.setStrokeColor(HexColor("#D3D3D3"))
                c.setLineWidth(0.5)
                for tick in range(0, 11, 2):
                    x_line = chart_x + label_w + (tick / 10.0) * bar_area_w
                    c.line(x_line, chart_top - 5, x_line, chart_top - chart_h - 5)
                    c.setFillColor(col_negro)
                    c.setFont("Helvetica", 6)
                    c.drawCentredString(x_line, chart_top - chart_h - 15, str(tick))

                y_bar = chart_top - 5
                for nombre_cat, items_cat in cat_blocks:
                    codigo = cls._codigo_area(nombre_cat)
                    prom = cls._promedio_10(items_cat)

                    c.setFillColor(col_negro)
                    c.setFont("Helvetica-Bold", 6.5)
                    c.drawRightString(chart_x + label_w - 4, y_bar - bar_h + 3, codigo)

                    bar_w = max(1, (prom / 10.0) * bar_area_w)
                    c.setFillColor(col_panel)
                    c.rect(chart_x + label_w, y_bar - bar_h, bar_w, bar_h, stroke=0, fill=1)

                    y_bar -= (bar_h + gap_bar)

            y_right -= (chart_h + 20)

            y_right -= h_header
            c.setFillColor(col_panel)
            c.rect(right_x, y_right, right_w, h_header, stroke=0, fill=1)
            c.setFillColor(col_blanco)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(right_x + right_w / 2,
                                y_right + (h_header / 2) - 3,
                                "NIVEL DE DESARROLLO OBTENIDO")

            y_right -= 22
            c.setFillColor(col_negro)
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(right_x + right_w / 2, y_right + 8, nivel_des)

            if descripcion_nivel:
                y_right -= 6
                c.setFillColor(col_negro)
                c.setFont("Helvetica", 6)
                desc_lines = simpleSplit(descripcion_nivel, "Helvetica", 6, right_w - 6)
                for line in desc_lines:
                    y_right -= 7.5
                    c.drawString(right_x + 3, y_right, line)

            # ================== COLUMNA IZQUIERDA ==================
            y_left = content_top

            for nombre_cat, items_cat in cat_blocks:
                codigo_area = cls._codigo_area(nombre_cat)

                if y_left - cat_h < min_bottom:
                    c.showPage()
                    y_left = draw_header()

                y_left -= cat_h
                c.setFillColor(col_categoria)
                c.rect(left_x, y_left, left_w, cat_h, stroke=0, fill=1)
                c.setFillColor(col_blanco)
                c.setFont("Helvetica-Bold", 8)
                c.drawString(left_x + 5, y_left + (cat_h / 2) - 3, nombre_cat.upper())
                prom_cat = cls._promedio_10(items_cat)
                c.drawRightString(left_x + left_w - 5, y_left + (cat_h / 2) - 3,
                                  "{:.2f}".format(prom_cat))

                for idx, item in enumerate(items_cat, 1):
                    if y_left - crit_h < min_bottom:
                        c.showPage()
                        y_left = draw_header()

                    y_left -= crit_h
                    max_v = item["maxima"] if item["maxima"] > 0 else 1
                    punt10 = item["puntuacion"] / max_v * 10

                    c.setFillColor(col_codigo)
                    c.setStrokeColor(col_borde)
                    c.setLineWidth(0.3)
                    c.rect(left_x, y_left, col_w_code, crit_h, stroke=1, fill=1)
                    c.setFillColor(col_negro)
                    c.setFont("Helvetica-Bold", 6.5)
                    c.drawCentredString(left_x + col_w_code / 2,
                                        y_left + (crit_h / 2) - 2.5,
                                        "{}{}".format(codigo_area, idx))

                    c.setFillColor(col_desc)
                    c.rect(left_x + col_w_code, y_left, col_w_desc, crit_h, stroke=0, fill=1)
                    c.setFillColor(col_negro)
                    c.setFont("Helvetica", 6.5)
                    desc = item["criterio"]
                    if item.get("descripcion"):
                        desc += " — " + item["descripcion"]
                    max_chars = int(col_w_desc / 3.1)
                    if len(desc) > max_chars:
                        desc = desc[:max_chars - 3] + "..."
                    c.drawString(left_x + col_w_code + 4,
                                 y_left + (crit_h / 2) - 2.5, desc)

                    c.setFillColor(col_punt)
                    c.rect(left_x + col_w_code + col_w_desc, y_left,
                           col_w_score, crit_h, stroke=0, fill=1)
                    c.setFillColor(col_negro)
                    c.setFont("Helvetica-Bold", 7)
                    c.drawCentredString(left_x + col_w_code + col_w_desc + col_w_score / 2,
                                        y_left + (crit_h / 2) - 2.5,
                                        "{:.2f}".format(punt10))

                c.setStrokeColor(col_borde)
                c.setLineWidth(0.3)
                c.line(left_x, y_left, left_x + left_w, y_left)

            # ================== SECCIÓN RETROALIMENTACIÓN ==================
            c.setFont("Helvetica-Bold", 8)
            heading_lines = simpleSplit(
                "RETROALIMENTACIÓN DETALLADA SOBRE SU DESEMPEÑO EN EL RECIENTE EXÁMEN PRÁCTICO.",
                "Helvetica-Bold", 8, total_w - 8
            )
            heading_h = len(heading_lines) * 11

            c.setFont("Helvetica", 7.5)
            fb_lines = simpleSplit(feedback_text, "Helvetica", 7.5, total_w - 8)
            fb_h = len(fb_lines) * 9.5

            min_requerido = heading_h + fb_h + 6 + 14 + 20

            lowest_y = min(y_left, y_right)

            if lowest_y - 20 < min_bottom + min_requerido:
                c.showPage()
                retro_y = draw_header() - 6
            else:
                retro_y = lowest_y - 20

            c.setFillColor(col_negro)
            c.setFont("Helvetica-Bold", 8)
            for line in heading_lines:
                c.drawString(margin + 4, retro_y, line)
                retro_y -= 11

            retro_y -= 2

            c.setFillColor(col_negro)
            c.setFont("Helvetica", 7.5)
            for line in fb_lines:
                if retro_y < min_bottom + 20:
                    c.showPage()
                    retro_y = draw_header() - 6
                c.drawString(margin + 4, retro_y, line)
                retro_y -= 9.5

            retro_y -= 8

            # ================== TABLA DE ÁREAS ==================
            areas_col1_w = 140
            areas_col2_w = total_w - areas_col1_w

            areas_rows = []
            for nombre_cat, items_cat in cat_blocks:
                obs = cls._observaciones_categoria(items_cat)
                if not obs:
                    obs = "0"
                areas_rows.append((nombre_cat, obs))

            areas_header_h = 14
            areas_row_min_h = 12
            areas_row_heights = []
            for _, obs in areas_rows:
                lines = simpleSplit(obs, "Helvetica", 6, areas_col2_w - 8)
                h = max(areas_row_min_h, len(lines) * 8 + 5)
                areas_row_heights.append(h)

            def draw_areas_header(y_top):
                y_h = y_top - areas_header_h
                c.setStrokeColor(col_borde)
                c.setLineWidth(0.3)
                c.setFillColor(col_blanco)
                c.rect(margin, y_h, areas_col1_w, areas_header_h, stroke=1, fill=1)
                c.rect(margin + areas_col1_w, y_h, areas_col2_w, areas_header_h, stroke=1, fill=1)
                c.setFillColor(col_negro)
                c.setFont("Helvetica-Bold", 7)
                c.drawCentredString(margin + areas_col1_w / 2,
                                    y_h + 4, "ÁREA TRONCAL")
                c.drawCentredString(margin + areas_col1_w + areas_col2_w / 2,
                                    y_h + 4, "OBSERVACIONES Y SUGERENCIAS")
                return y_h

            current_y = retro_y
            current_y = draw_areas_header(current_y)

            for i, (nombre_cat, obs) in enumerate(areas_rows):
                row_h = areas_row_heights[i]

                if current_y - row_h < min_bottom:
                    c.showPage()
                    new_top = draw_header()
                    current_y = new_top - 6
                    current_y = draw_areas_header(current_y)

                current_y -= row_h

                c.setStrokeColor(col_borde)
                c.setLineWidth(0.3)
                c.setFillColor(col_blanco)
                c.rect(margin, current_y, areas_col1_w, row_h, stroke=1, fill=1)
                c.rect(margin + areas_col1_w, current_y, areas_col2_w, row_h, stroke=1, fill=1)

                c.setFillColor(col_negro)
                c.setFont("Helvetica-Bold", 6.5)
                c.drawString(margin + 4, current_y + row_h - 8, nombre_cat)

                c.setFont("Helvetica", 6)
                lines = simpleSplit(obs, "Helvetica", 6, areas_col2_w - 8)
                line_y = current_y + row_h - 8
                for line in lines:
                    c.drawString(margin + areas_col1_w + 4, line_y, line)
                    line_y -= 8

            c.save()
            logger.info("PDF carátula guardado: %s", ruta_pdf)
            return True, "PDF generado correctamente"

        except Exception as e:
            logger.error("Error generando PDF: %s", traceback.format_exc())
            return False, "Error: {}".format(e)


def evaluar_y_generar_pdf(ruta_rubrica, ruta_conversacion, ruta_pdf_salida,
                          matricula="", nombre=""):
    """
    Función principal de la API.
    
    Lee la rúbrica y la conversación, ejecuta la evaluación con Gemini
    y genera únicamente el PDF de la carátula.
    
    Args:
        ruta_rubrica (str): Ruta al archivo de la rúbrica (.txt, .pdf, .docx).
        ruta_conversacion (str): Ruta al archivo de la conversación (.txt, .pdf, .docx).
        ruta_pdf_salida (str): Ruta donde se guardará el PDF generado.
        matricula (str): Matrícula del estudiante (opcional).
        nombre (str): Nombre del estudiante (opcional).
    
    Returns:
        tuple: (bool, str) indicando éxito y mensaje.
    """
    try:
        evaluador = EvaluadorECOE()
    except Exception as e:
        return False, "Error al conectar con Gemini: {}".format(e)

    try:
        contenido_rub = evaluador.leer_archivo(ruta_rubrica)
        if not contenido_rub:
            return False, "No se pudo leer la rúbrica: {}".format(ruta_rubrica)

        contenido_conv = evaluador.leer_archivo(ruta_conversacion)
        if not contenido_conv:
            return False, "No se pudo leer la conversación: {}".format(ruta_conversacion)

        rubrica = evaluador.procesar_rubrica(contenido_rub)
        evaluacion = evaluador.evaluar_conversacion(contenido_conv, rubrica)

        ok, msg = GeneradorCaratula.generar_pdf(
            evaluacion, rubrica, ruta_pdf_salida,
            matricula=matricula, nombre=nombre
        )
        if not ok:
            return False, msg

        return True, ruta_pdf_salida

    except Exception as e:
        logger.error("Error en evaluar_y_generar_pdf: %s", traceback.format_exc())
        return False, "Error inesperado: {}".format(e)