# escenas/escena_admin_evaluacion.py
import streamlit as st
import os
import uuid
import requests
from datetime import datetime
from utils.supabase_client import supabase
from utils.evaluador_batch import evaluar_estudiante_completo
from utils.casos import formatear_fecha_inteligente
from utils.horario import leer_fecha

def subir_pdf_a_supabase(ruta_local, matricula, circuito_nombre):
    """Sube el PDF al Storage y guarda el registro en la base de datos."""
    try:
        nombre_archivo = f"{matricula}_{uuid.uuid4().hex[:6]}.pdf"
        ruta_storage = f"evaluaciones/{nombre_archivo}"
        
        with open(ruta_local, "rb") as f:
            supabase.storage.from_("casos_clinicos").upload(
                path=ruta_storage,
                file=f.read(),
                file_options={"content-type": "application/pdf"}
            )
            
        url = supabase.storage.from_("casos_clinicos").get_public_url(ruta_storage)
        
        # Registrar en la base de datos
        supabase.table("evaluaciones_pdf").insert({
            "matricula": matricula,
            "circuito": circuito_nombre,
            "url_pdf": url
        }).execute()
        
        return url
    except Exception as e:
        print(f"Error subiendo PDF: {e}")
        return None

def mostrar():
    st.markdown("""
    <style>
        .section-title { color: #252A38; font-family: 'Poppins'; font-size: 24px; font-weight: 600; margin-top: 1.5rem; margin-bottom: 1rem; border-left: 4px solid #70257E; padding-left: 1rem; }
        
        /* Badges más grandes y legibles */
        .badge-estatus { background-color: #E5E7EC; color: #626779; padding: 8px; border-radius: 6px; font-size: 14px; font-weight: 600; text-align: center; }
        .badge-estatus-listo { background-color: #6B21A8; color: #F3E8FF; padding: 8px; border-radius: 6px; font-size: 14px; font-weight: 600; text-align: center; }
        
        .texto-encabezado-tabla {
            font-size: 16px !important;
            color: #252A38;
            font-weight: bold;
        }

        .texto-tabla-normal {
            font-size: 14px !important; 
            color: #303442; 
            line-height: 1.4;
        }

        /* Botones más compactos */
        .stButton button { padding: 4px 8px !important; font-size: 14px !important; min-height: 35px !important; }
        
        /* Estilo para el mensaje de carga dentro de la tabla */
        .cargando-tabla {
            font-size: 12px;
            color: #6B21A8;
            font-weight: 600;
            text-align: center;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">Evaluación del chatbot (PDF por estudiante)</div>', unsafe_allow_html=True)
    st.caption("El chatbot evalúa automáticamente a cada estudiante al terminar su circuito. Aquí puedes ver y descargar su PDF.")
    
    # Obtener datos de estudiantes
    res_est = supabase.table("perfiles_estudiantes").select("matricula, nombre_completo, circuito_asignado, fecha_examen").execute()
    estudiantes = res_est.data if res_est.data else []

    if not estudiantes:
        st.info("No hay estudiantes registrados.")
        return

    # Obtener casos por circuito
    res_circ = supabase.table("circuitos").select("*").execute()
    circuitos_dict = {c["nombre"]: c for c in res_circ.data} if res_circ.data else {}

    # Obtener evaluaciones ya existentes para descargar de inmediato
    res_eval = supabase.table("evaluaciones_pdf").select("matricula, url_pdf, fecha_creacion").order("fecha_creacion").execute()
    # al recorrer en orden de fecha, se queda el PDF más reciente de cada estudiante
    evaluaciones_dict = {e["matricula"]: e["url_pdf"] for e in res_eval.data} if res_eval.data else {}

    # ===== CONSTRUIR LA TABLA =====
    headers = ["Matrícula", "Nombre", "Circuito", "Fecha Examen", "Estatus del Examen", "", ""]
    cols_pesos = [1.05, 2.1, 0.95, 1.1, 1.5, 1.3, 1.5]
    
    cols = st.columns(cols_pesos)
    
    # Pintar encabezados
    for i, (col, header) in enumerate(zip(cols, headers)):
        if header:
            col.markdown(f'<div class="texto-encabezado-tabla">{header}</div>', unsafe_allow_html=True)
        else:
            col.markdown("")
            
    st.markdown("---")

    # Renderizar filas
    for est in estudiantes:
        matricula = est["matricula"]
        nombre = est["nombre_completo"]
        circuito_nombre = est.get("circuito_asignado")
        
        cols = st.columns(cols_pesos)
        
        # 1. Datos básicos
        cols[0].markdown(f'<div class="texto-tabla-normal">{matricula}</div>', unsafe_allow_html=True)
        cols[1].markdown(f'<div class="texto-tabla-normal">{nombre}</div>', unsafe_allow_html=True)
        cols[2].markdown(f'<div class="texto-tabla-normal">{circuito_nombre or "—"}</div>', unsafe_allow_html=True)
        # fecha_examen es una fecha (sin hora): se muestra tal cual, sin convertir de zona horaria
        _dia = leer_fecha(est.get("fecha_examen"))
        cols[3].markdown(f'<div class="texto-tabla-normal">{_dia.strftime("%d/%m/%Y") if _dia else "—"}</div>', unsafe_allow_html=True)
        
        # 2. Calcular Estatus del Examen
        completadas = 0      # estaciones con respuestas guardadas ("Guardar y Terminar")
        intentadas = 0       # estaciones con chat o respuestas (p. ej. se le acabó el tiempo)
        total_casos = 0
        
        if circuito_nombre in circuitos_dict:
            circuito = circuitos_dict[circuito_nombre]
            for i in range(1, 7):
                caso = circuito.get(f"caso_{i}")
                area = circuito.get(f"modulo_{i}")
                
                if not caso or area == "No asignar":
                    continue
                
                total_casos += 1
                
                res_chat = supabase.table("historial_chat_estudiante").select("id").eq("matricula", matricula).eq("caso", caso).execute()
                res_preg = supabase.table("historial_preguntas_estudiante").select("id").eq("matricula", matricula).eq("caso", caso).execute()
                
                if res_preg.data:
                    completadas += 1
                if res_chat.data or res_preg.data:
                    intentadas += 1

        # 3. Columna de Estatus
        with cols[4]:
            if total_casos == 0:
                st.markdown('<div class="badge-estatus">Sin áreas asignadas</div>', unsafe_allow_html=True)
            elif completadas == total_casos:
                st.markdown('<div class="badge-estatus-listo">Completado 100%</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="badge-estatus">Completado {completadas}/{total_casos}</div>', unsafe_allow_html=True)
                if intentadas > completadas:
                    st.caption(f"{intentadas - completadas} estación(es) sin respuestas guardadas")

        # 4 y 5. Resultados: ver y descargar el PDF. Ya no se re-evalúa desde aquí:
        #        el chatbot evalúa automáticamente cuando el estudiante termina su circuito.
        url_pdf_existente = evaluaciones_dict.get(matricula)
        from utils.evaluacion_automatica import en_curso, lanzar_evaluacion, falta_medico, ultimo_resultado
        termino = total_casos > 0 and intentadas >= total_casos
        faltan_medico = falta_medico(matricula, circuito_nombre) if termino and not url_pdf_existente else []

        if url_pdf_existente:
            cols[5].link_button("Ver PDF", url_pdf_existente, use_container_width=True)
            url_descarga = url_pdf_existente + ("&" if "?" in url_pdf_existente else "?") + "download="
            cols[6].link_button("Descargar PDF", url_descarga, use_container_width=True)
        elif en_curso(matricula):
            cols[5].markdown('<div class="cargando-tabla">Evaluando…</div>', unsafe_allow_html=True)
            if cols[6].button("Actualizar", key=f"act_{matricula}", use_container_width=True):
                st.rerun()
        elif termino and faltan_medico:
            # Hay estación(es) estandarizadas sin evaluación del médico: el PDF se genera
            # solo en cuanto el médico la envía.
            cols[5].markdown('<div style="text-align:center; font-size:13px; color:#A0AABF;">Sin PDF aún</div>',
                             unsafe_allow_html=True)
            cols[6].button("Esperando médico", key=f"espm_{matricula}", disabled=True, use_container_width=True,
                           help="Falta la evaluación del médico en: " + ", ".join(faltan_medico)
                                + ". El PDF se genera automáticamente cuando la envíe.")
        elif termino:
            # Respaldo: terminó el circuito pero no tiene evaluación (p. ej. falló la automática
            # o terminó antes de esta versión). Solo aparece mientras NO exista PDF.
            cols[5].markdown('<div style="text-align:center; font-size:13px; color:#A0AABF;">Sin evaluación</div>',
                             unsafe_allow_html=True)
            if cols[6].button("Generar evaluación", key=f"gen_{matricula}", use_container_width=True,
                              help="Solo para estudiantes que terminaron y no tienen evaluación. No re-evalúa."):
                with st.spinner(f"Evaluando a {nombre}… (puede tardar 1–2 minutos)"):
                    lanzar_evaluacion(matricula, nombre, circuito_nombre, esperar=True)
                st.rerun()
            _motivo = ultimo_resultado(matricula)
            if _motivo:
                cols[5].caption(f"Último intento: {_motivo[:120]}")
        else:
            cols[5].markdown('<div style="text-align:center; font-size:14px; color:#A0AABF;">-</div>', unsafe_allow_html=True)
            cols[6].button("Pendiente", key=f"pend_{matricula}", disabled=True, use_container_width=True,
                           help=f"Se evalúa automáticamente al terminar su circuito ({intentadas}/{total_casos} estaciones)")

        st.markdown("---")