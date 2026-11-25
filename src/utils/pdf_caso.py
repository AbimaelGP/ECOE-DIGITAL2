# utils/pdf_caso.py
"""
Genera un PDF con la información completa de un caso clínico.

Estructura:
  PÁGINA 1  → Metadatos (tipo de caso, responsable, fecha) + Rúbrica de competencias
  PÁGINA 2  → Datos del paciente + Instrucciones al estudiante (hoja independiente)
  PÁGINA 3  → Guión del paciente (página independiente, fondo blanco, fluye entre páginas)
  SECCIÓN   → Rúbricas de evaluación (tabla completa de niveles + espacio para notas a mano)
  PÁGINA 4+ → Preguntas de evaluación (lista Pregunta / Respuesta esperada)
  PÁGINA 5+ → Anexo: imágenes de estudios (si existen)

Footer institucional en todas las páginas.
"""
import io
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    PageBreak, Image, Table, TableStyle, KeepTogether
)

MORADO = colors.HexColor("#70257E")
MORADO_OSCURO = colors.HexColor("#5B1E66")
GRIS_TEXTO = colors.HexColor("#303442")
GRIS_SUAVE = colors.HexColor("#626779")

FOOTER_TEXTO = (
    "©2026. Desarrollada por Natalia Acevedo, Maribel Aguilar, Carla Alvarado, "
    "Paulina González, Dr. Abimael Guzmán Pando & Dra. Haydeé Parra Acosta.<br/>"
    "Laboratorio de Investigación en Inteligencia Artificial y Computación Médica "
    "(LIIACOM), Facultad de Medicina y Ciencias Biomédicas, UACH."
)


# ==================== ESTILOS ====================

def _estilos():
    s = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=s["Title"], fontName="Helvetica-Bold",
            fontSize=20, textColor=MORADO, spaceAfter=6, alignment=0
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=s["Heading2"], fontName="Helvetica-Bold",
            fontSize=14, textColor=GRIS_TEXTO, spaceBefore=10, spaceAfter=6
        ),
        "seccion": ParagraphStyle(
            "seccion", parent=s["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, textColor=MORADO, spaceBefore=14, spaceAfter=8,
        ),
        "label": ParagraphStyle(
            "label", parent=s["BodyText"], fontName="Helvetica-Bold",
            fontSize=10, textColor=GRIS_TEXTO, spaceAfter=2
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo", parent=s["BodyText"], fontName="Helvetica",
            fontSize=10, textColor=GRIS_TEXTO, leading=14, spaceAfter=8
        ),
        "cuerpo_grande": ParagraphStyle(
            "cuerpo_grande", parent=s["BodyText"], fontName="Helvetica",
            fontSize=12, textColor=GRIS_TEXTO, leading=18, spaceAfter=8
        ),
        "caption": ParagraphStyle(
            "caption", parent=s["BodyText"], fontName="Helvetica-Oblique",
            fontSize=9, textColor=GRIS_SUAVE, spaceAfter=4
        ),
    }


# ==================== HELPERS ====================

def _formatear_fecha(fecha_raw):
    """Convierte la fecha de Supabase a formato legible en hora de México."""
    if not fecha_raw:
        return "—"
    try:
        from datetime import datetime as _dt
        fecha_str = str(fecha_raw)
        if not fecha_str.endswith("Z") and "+" not in fecha_str:
            if "T" in fecha_str:
                fecha_str = fecha_str.split(".")[0] + "+00:00"
            else:
                fecha_str = fecha_str.replace(" ", "T") + "+00:00"
        fecha_utc = _dt.fromisoformat(fecha_str)
        fecha_local = fecha_utc.astimezone(ZoneInfo("America/Mexico_City"))
        return fecha_local.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(fecha_raw)[:16]


def _descargar_imagen(url):
    """Descarga una imagen y retorna un BytesIO. None si falla."""
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return io.BytesIO(r.content)
    except Exception as e:
        print(f"⚠️ No se pudo descargar imagen {url}: {e}")
        return None


def _crear_imagen(url, max_width=4 * cm, max_height=5 * cm):
    """Crea un flowable Image escalado a partir de una URL."""
    buf = _descargar_imagen(url)
    if not buf:
        return None
    try:
        from PIL import Image as PILImage
        img = PILImage.open(buf)
        w, h = img.size
        buf.seek(0)
        ratio = min(max_width / w, max_height / h)
        return Image(buf, width=w * ratio, height=h * ratio)
    except Exception as e:
        print(f"⚠️ Error procesando imagen: {e}")
        return None


def _seccion(titulo, estilos):
    """Retorna un Paragraph de sección con línea morada."""
    return Paragraph(
        f'<font color="#70257E">▎</font> <b>{titulo}</b>',
        estilos["seccion"]
    )


def _campo(label, valor, estilos):
    """Retorna [label + valor] como Paragraphs separados."""
    valor = valor if valor not in (None, "", "None") else "—"
    return [
        Paragraph(label, estilos["label"]),
        Paragraph(str(valor).replace("\n", "<br/>"), estilos["cuerpo"]),
    ]


def _texto_pdf(texto):
    """Escapa &, <, > (rompen el parser de Paragraph) y convierte saltos de línea."""
    from xml.sax.saxutils import escape
    return escape(str(texto or "").strip()).replace("\n", "<br/>")


def _lineas_para_escribir(ancho, renglones=5, alto_renglon=0.8 * cm):
    """Espacio en blanco con renglones para que el docente escriba a mano."""
    t = Table([[""]] * renglones, colWidths=[ancho], rowHeights=[alto_renglon] * renglones)
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFC3CC")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D1D5DB")),
    ]))
    return t


def _seccion_rubricas(info_caso, estilos, ancho):
    """
    Sección independiente (inicia en página nueva) con la tabla completa de
    cada rúbrica: criterio + 5 niveles de desempeño con su descriptor, igual
    que el formulario del médico evaluador, y renglones para notas a mano.
    """
    rubrica = info_caso.get("rubrica_competencias", []) or []
    if not rubrica:
        return []

    # Import local: evaluacion_dual importa streamlit/supabase
    from utils.evaluacion_dual import competencias_de_caso, NIVELES
    criterios = competencias_de_caso(rubrica)
    if not criterios:
        return []

    th = ParagraphStyle("rub_th", fontName="Helvetica-Bold", fontSize=8,
                        textColor=colors.white, leading=10, alignment=1)
    th_rango = ParagraphStyle("rub_rango", fontName="Helvetica", fontSize=7,
                              textColor=colors.white, leading=9, alignment=1)
    td = ParagraphStyle("rub_td", fontName="Helvetica", fontSize=7.5,
                        textColor=GRIS_TEXTO, leading=9.5)
    estilo_dom = ParagraphStyle("rub_dom", fontName="Helvetica-Bold", fontSize=10.5,
                                textColor=MORADO, leading=13, spaceAfter=1)
    estilo_cat = ParagraphStyle("rub_cat", fontName="Helvetica", fontSize=8,
                                textColor=GRIS_SUAVE, leading=10, spaceAfter=2)
    estilo_crit = ParagraphStyle("rub_crit", fontName="Helvetica-Bold", fontSize=9.5,
                                 textColor=GRIS_TEXTO, leading=12, spaceAfter=5)
    estilo_obs = ParagraphStyle("rub_obs", fontName="Helvetica-Bold", fontSize=8.5,
                                textColor=GRIS_TEXTO, spaceBefore=5, spaceAfter=2)

    flows = [PageBreak(), _seccion("Rúbricas de evaluación", estilos), Paragraph(
        "Rúbrica General (5 niveles, escala 1–10) aplicada a cada competencia del caso. "
        "Debajo de cada rúbrica hay espacio para anotaciones del docente.",
        estilos["caption"]
    ), Spacer(1, 0.3 * cm)]

    ancho_col = ancho / len(NIVELES)
    for n, c in enumerate(criterios, 1):
        descriptores = list(c.get("niveles") or [])
        descriptores += [""] * (len(NIVELES) - len(descriptores))

        fila_titulos = [[Paragraph(nombre, th), Paragraph(f"{lo}–{hi}", th_rango)]
                        for nombre, lo, hi in NIVELES]
        fila_desc = [Paragraph(_texto_pdf(d), td) for d in descriptores[:len(NIVELES)]]

        tabla = Table([fila_titulos, fila_desc], colWidths=[ancho_col] * len(NIVELES))
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), MORADO),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("VALIGN", (0, 1), (-1, 1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        bloque = [
            Paragraph(f'{n}. {_texto_pdf(c.get("dominio"))}', estilo_dom),
            Paragraph(_texto_pdf(c.get("categoria")), estilo_cat),
            Paragraph(_texto_pdf(c.get("texto")), estilo_crit),
            tabla,
            Paragraph("Puntaje: ______ &nbsp;&nbsp;&nbsp; Observaciones del docente:", estilo_obs),
            _lineas_para_escribir(ancho, renglones=4),
            Spacer(1, 0.6 * cm),
        ]
        flows.append(KeepTogether(bloque))

    flows.append(KeepTogether([
        Paragraph("Comentarios generales / retroalimentación para el estudiante", estilo_obs),
        _lineas_para_escribir(ancho, renglones=6),
    ]))
    return flows


# ==================== FOOTER ====================

def _dibujar_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRIS_SUAVE)

    y = 1.2 * cm
    from reportlab.platypus import Paragraph as _P
    from reportlab.lib.styles import ParagraphStyle as _PS
    estilo_footer = _PS("footer", fontName="Helvetica", fontSize=7,
                        textColor=GRIS_SUAVE, alignment=1, leading=9)
    p = _P(FOOTER_TEXTO, estilo_footer)
    w, h = p.wrapOn(canvas, doc.pagesize[0] - 2 * cm, 3 * cm)
    p.drawOn(canvas, 1 * cm, y)

    # Línea superior del footer
    canvas.setStrokeColor(MORADO)
    canvas.setLineWidth(0.5)
    canvas.line(1 * cm, y + h + 0.3 * cm,
                doc.pagesize[0] - 1 * cm, y + h + 0.3 * cm)
    canvas.restoreState()


# ==================== CONSTRUCCIÓN DEL PDF ====================

def generar_pdf_caso(clave_caso, info_caso):
    """
    Genera el PDF del caso y retorna un BytesIO.
    `info_caso` es lo que devuelve `cargar_info_caso(clave_caso)`.
    """
    if not info_caso:
        raise ValueError("info_caso es requerido")

    estilos = _estilos()
    buffer = io.BytesIO()

    doc = BaseDocTemplate(
        buffer, pagesize=LETTER,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=3.5 * cm,
        title=f"Caso Clínico {clave_caso}",
        author="LIIACOM - UACH",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height, id="normal"
    )
    doc.addPageTemplates([
        PageTemplate(id="portada", frames=[frame], onPage=_dibujar_footer),
    ])

    story = []

    # ============================================================
    # PÁGINA 1: METADATOS + RÚBRICA
    # ============================================================
    nombre_caso = info_caso.get("nombre_caso") or "(Sin nombre de caso)"
    story.append(Paragraph("Caso Clínico", estilos["caption"]))
    story.append(Paragraph(nombre_caso, estilos["titulo"]))

    especialidad = info_caso.get("especialidad", "No especificada")
    story.append(Paragraph(
        f'<font color="#626779">Clave: <b>{clave_caso}</b> &nbsp;|&nbsp; '
        f'Especialidad: <b>{especialidad}</b></font>',
        estilos["cuerpo"]
    ))
    story.append(Spacer(1, 0.3 * cm))

    # ===== TABLA DE METADATOS =====
    tipo_caso = info_caso.get("tipo_caso", "—")
    responsable = info_caso.get("responsable", "—") or "—"
    fecha_formateada = _formatear_fecha(info_caso.get("fecha_actualizacion", ""))

    meta_label_style = ParagraphStyle(
        "meta_label", fontName="Helvetica-Bold", fontSize=8,
        textColor=colors.white, leading=11
    )
    meta_valor_style = ParagraphStyle(
        "meta_valor", fontName="Helvetica", fontSize=9,
        textColor=GRIS_TEXTO, leading=12
    )

    tabla_meta = Table(
        [
            [
                Paragraph("TIPO DE CASO", meta_label_style),
                Paragraph("RESPONSABLE", meta_label_style),
                Paragraph("ÚLTIMA ACTUALIZACIÓN", meta_label_style),
            ],
            [
                Paragraph(str(tipo_caso), meta_valor_style),
                Paragraph(str(responsable), meta_valor_style),
                Paragraph(fecha_formateada, meta_valor_style),
            ],
        ],
        colWidths=[doc.width / 3] * 3,
    )
    tabla_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MORADO),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8F4F9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
    ]))
    story.append(tabla_meta)
    story.append(Spacer(1, 0.6 * cm))

    # ===== RÚBRICA DE COMPETENCIAS (misma página) =====
    rubrica = info_caso.get("rubrica_competencias", []) or []
    if rubrica:
        story.append(_seccion("Rúbrica de competencias evaluadas", estilos))
        story.append(Paragraph(
            "Competencias del perfil de egreso que se evalúan con este caso clínico.",
            estilos["caption"]
        ))
        story.append(Spacer(1, 0.3 * cm))

        # Agrupar por categoría → subcategoría
        agrupadas = {}
        for comp in rubrica:
            cat = comp.get("categoria", "SIN CATEGORÍA")
            sub = comp.get("subcategoria", "General")
            agrupadas.setdefault(cat, {}).setdefault(sub, []).append(
                comp.get("texto", "")
            )

        for categoria, subcategorias in agrupadas.items():
            cat_parr = Paragraph(
                f'<b>{categoria}</b>',
                ParagraphStyle("cat", fontName="Helvetica-Bold", fontSize=12,
                               textColor=colors.white, leading=16)
            )
            tabla_cat = Table([[cat_parr]], colWidths=[doc.width])
            tabla_cat.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), MORADO),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(tabla_cat)
            story.append(Spacer(1, 0.15 * cm))

            for subcategoria, textos in subcategorias.items():
                story.append(Paragraph(
                    f'<font color="#70257E"><b>{subcategoria}</b></font>',
                    ParagraphStyle("sub", fontName="Helvetica-Bold", fontSize=10,
                                   textColor=MORADO, spaceBefore=4, spaceAfter=4)
                ))
                for texto in textos:
                    story.append(Paragraph(
                        f'• {texto}',
                        ParagraphStyle("item", fontName="Helvetica", fontSize=9,
                                       textColor=GRIS_TEXTO, leading=13,
                                       leftIndent=12, spaceAfter=2)
                    ))
                story.append(Spacer(1, 0.2 * cm))

    # ============================================================
    # PÁGINA 2: DATOS DEL PACIENTE + INSTRUCCIONES (hoja independiente)
    # ============================================================
    story.append(PageBreak())

    story.append(_seccion("Datos del paciente", estilos))

    sprite_flow = _crear_imagen(info_caso.get("sprite_url"), 4 * cm, 5 * cm)

    datos_izq = []
    for lbl, val in [
        ("Nombre", info_caso.get("nombre", "—")),
        ("Edad", f'{info_caso.get("edad", "—")} años'
         if str(info_caso.get("edad", "")).isdigit() else info_caso.get("edad", "—")),
        ("Sexo", info_caso.get("sexo", "—")),
        ("Motivo de consulta", info_caso.get("motivo_consulta", "—")),
    ]:
        datos_izq += _campo(lbl, val, estilos)

    if sprite_flow:
        tabla_paciente = Table(
            [[sprite_flow, datos_izq]],
            colWidths=[5 * cm, doc.width - 5 * cm]
        )
        tabla_paciente.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(tabla_paciente)
    else:
        story.extend(datos_izq)

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Descripción", estilos["label"]))
    story.append(Paragraph(
        info_caso.get("descripcion", "—").replace("\n", "<br/>"),
        estilos["cuerpo"]
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Antecedentes", estilos["label"]))
    story.append(Paragraph(
        info_caso.get("antecedentes", "—").replace("\n", "<br/>"),
        estilos["cuerpo"]
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Medicamentos actuales", estilos["label"]))
    story.append(Paragraph(
        info_caso.get("medicamentos_actuales", "—").replace("\n", "<br/>"),
        estilos["cuerpo"]
    ))

    # ===== INSTRUCCIONES AL ESTUDIANTE (misma hoja del paciente) =====
    instrucciones = info_caso.get("instrucciones", {}) or {}
    instrucciones_caso = instrucciones.get("instrucciones_caso", "").strip()
    if instrucciones_caso:
        story.append(Spacer(1, 0.6 * cm))
        story.append(_seccion("Indicaciones del caso", estilos))
        story.append(Paragraph(
            instrucciones_caso.replace("\n", "<br/>"),
            estilos["cuerpo_grande"]
        ))

    # ============================================================
    # PÁGINA 3: GUIÓN DEL PACIENTE (página independiente)
    # ============================================================
    guion_paciente = instrucciones.get("guion_paciente", "").strip()
    if guion_paciente:
        story.append(PageBreak())
        story.append(Paragraph("GUIÓN DEL PACIENTE", ParagraphStyle(
            "guion_titulo", fontName="Helvetica-Bold", fontSize=18,
            textColor=MORADO, alignment=1, spaceAfter=6
        )))
        story.append(Paragraph(
            "Documento independiente — para uso del actor / paciente estandarizado",
            ParagraphStyle("guion_sub", fontName="Helvetica-Oblique",
                           fontSize=9, textColor=GRIS_SUAVE,
                           alignment=1, spaceAfter=16)
        ))
        # Antes era un Paragraph dentro de una Table: si el guión no cabía en una
        # página, ReportLab lanzaba "tallest cell ... too large". Ahora es un
        # Paragraph con borde propio (fondo blanco) que se parte entre páginas.
        estilo_guion = ParagraphStyle(
            "guion_cuerpo", parent=estilos["cuerpo_grande"],
            backColor=colors.white,
            borderColor=MORADO, borderWidth=1.5, borderPadding=14,
            leftIndent=14, rightIndent=14,   # = borderPadding, para que el borde no salga del margen
            spaceBefore=14, spaceAfter=14,
        )
        story.append(Paragraph(_texto_pdf(guion_paciente), estilo_guion))

    # ============================================================
    # RÚBRICAS DE EVALUACIÓN (sección independiente)
    # ============================================================
    story.extend(_seccion_rubricas(info_caso, estilos, doc.width))

    # ============================================================
    # PÁGINA 4+: PREGUNTAS DE EVALUACIÓN
    # ============================================================
    solucion = info_caso.get("solucion", {}) or {}
    preguntas = solucion.get("preguntas", []) or []
    preguntas_validas = [
        p for p in preguntas
        if p.get("pregunta", "").strip()
    ]

    if preguntas_validas:
        story.append(PageBreak())
        story.append(_seccion("Preguntas de evaluación", estilos))
        story.append(Paragraph(
            "Las respuestas esperadas se muestran a continuación para uso del docente/evaluador.",
            estilos["caption"]
        ))
        story.append(Spacer(1, 0.2 * cm))

        # Lista simple (Pregunta / Respuesta esperada) en lugar de tabla
        estilo_pregunta = ParagraphStyle(
            "pregunta_item", fontName="Helvetica-Bold", fontSize=10,
            textColor=GRIS_TEXTO, leading=13, spaceBefore=6, spaceAfter=2,
            leftIndent=14, firstLineIndent=-14,
        )
        estilo_respuesta = ParagraphStyle(
            "respuesta_item", fontName="Helvetica", fontSize=9.5,
            textColor=GRIS_TEXTO, leading=13, spaceAfter=6, leftIndent=14,
        )
        for i, p in enumerate(preguntas_validas, 1):
            story.append(Paragraph(
                f'{i}. {_texto_pdf(p.get("pregunta", ""))}', estilo_pregunta
            ))
            story.append(Paragraph(
                f'<font color="#70257E"><b>Respuesta esperada:</b></font> '
                f'{_texto_pdf(p.get("respuesta_esperada", "")) or "—"}',
                estilo_respuesta
            ))

    # ============================================================
    # PÁGINA 5+: ANEXO: ESTUDIOS (valores + imágenes)
    # ============================================================
    valores_estudios = info_caso.get("valores_estudios", {}) or {}

    # Separar estudios por tipo
    estudios_valores = {
        nombre: datos for nombre, datos in valores_estudios.items()
        if isinstance(datos, dict) and datos.get("tipo") == "parametros"
    }
    estudios_imagen = {
        nombre: datos for nombre, datos in valores_estudios.items()
        if isinstance(datos, dict) and datos.get("imagen_url")
    }

    if estudios_valores or estudios_imagen:
        story.append(PageBreak())
        story.append(_seccion("Anexo: Estudios del caso", estilos))
        story.append(Paragraph(
            "Resultados de laboratorio e imágenes adjuntas al caso.",
            estilos["caption"]
        ))
        story.append(Spacer(1, 0.4 * cm))

        # ===== 1) ESTUDIOS DE VALORES =====
        if estudios_valores:
            story.append(Paragraph(
                "Estudios de laboratorio",
                ParagraphStyle("anexo_sub", fontName="Helvetica-Bold", fontSize=12,
                               textColor=MORADO, spaceBefore=6, spaceAfter=8)
            ))
            story.append(Spacer(1, 0.3 * cm))

            # Estilos para la tabla sobria (escala de grises)
            th_style = ParagraphStyle(
                "th_val_gris", fontName="Helvetica-Bold", fontSize=9,
                textColor=colors.white, leading=12
            )
            td_style = ParagraphStyle(
                "td_val_gris", fontName="Helvetica", fontSize=9,
                textColor=GRIS_TEXTO, leading=12
            )
            GRIS_ENCABEZADO = colors.HexColor("#4B5563")  # Gris pizarra oscuro
            GRIS_FILA = colors.HexColor("#F3F4F6")        # Gris muy claro
            GRIS_BORDE = colors.HexColor("#D1D5DB")       # Gris medio para bordes

            es_primer_estudio = True
            for nombre_estudio, datos in estudios_valores.items():
                parametros = datos.get("parametros", {}) or {}
                if not parametros:
                    continue

                # Si no es el primero, forzamos salto de página
                if not es_primer_estudio:
                    story.append(PageBreak())
                es_primer_estudio = False

                # Título del estudio
                story.append(Paragraph(f"<b>{nombre_estudio}</b>", estilos["subtitulo"]))
                story.append(Spacer(1, 0.2 * cm))

                # Tabla: Parámetro | Resultado | Unidad
                tabla_data = [[
                    Paragraph("Parámetro", th_style),
                    Paragraph("Resultado", th_style),
                    Paragraph("Unidad", th_style),
                ]]
                for param_nombre, param_data in parametros.items():
                    if isinstance(param_data, dict):
                        valor = param_data.get("valor", "—")
                        unidad = param_data.get("unidad", "") or "—"
                    else:
                        valor = param_data
                        unidad = "—"

                    tabla_data.append([
                        Paragraph(str(param_nombre), td_style),
                        Paragraph(str(valor), td_style),
                        Paragraph(str(unidad), td_style),
                    ])

                tabla_params = Table(
                    tabla_data,
                    colWidths=[doc.width * 0.50, doc.width * 0.25, doc.width * 0.25],
                    repeatRows=1,
                )
                tabla_params.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), GRIS_ENCABEZADO),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_FILA]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(tabla_params)

        # ===== 2) ESTUDIOS DE IMAGEN =====
        if estudios_imagen:
            # Si ya hubo estudios de valores, empezamos en página nueva
            if estudios_valores:
                story.append(PageBreak())

            story.append(Paragraph(
                "Estudios de imagen",
                ParagraphStyle("anexo_sub_img", fontName="Helvetica-Bold", fontSize=12,
                               textColor=MORADO, spaceBefore=6, spaceAfter=8)
            ))
            story.append(Spacer(1, 0.3 * cm))

            es_primer_imagen = True
            for nombre_estudio, datos in estudios_imagen.items():
                if not es_primer_imagen:
                    story.append(PageBreak())
                es_primer_imagen = False

                img_flow = _crear_imagen(datos.get("imagen_url"), 14 * cm, 16 * cm)
                story.append(Paragraph(f"<b>{nombre_estudio}</b>", estilos["subtitulo"]))
                story.append(Spacer(1, 0.3 * cm))
                
                if img_flow:
                    story.append(img_flow)
                else:
                    story.append(Paragraph("(No se pudo cargar la imagen)", estilos["caption"]))
                
                story.append(Spacer(1, 0.5 * cm))

    # ============ METADATA AL FINAL ============
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f'<font color="#626779" size="8">'
        f'Documento generado el '
        f'{datetime.now(ZoneInfo("America/Mexico_City")).strftime("%d/%m/%Y %H:%M")} '
        f'— Clave del caso: {clave_caso}</font>',
        estilos["caption"]
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer