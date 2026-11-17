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
    
    st.markdown('<div class="section-title">Generar evaluación del chatbot (PDF por estudiante)</div>', unsafe_allow_html=True)
    
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
    cols_pesos = [1, 2.5, 1, 1.2, 1.8, 1.5, 1]
    
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

        # 4. Columna de Descarga / Carga
        url_pdf_existente = evaluaciones_dict.get(matricula)
        evaluando_ahora = st.session_state.get(f"evaluando_{matricula}", False)
        
        with cols[5]:
            if url_pdf_existente:
                st.link_button("Ver resultados", url_pdf_existente, use_container_width=True)
            elif evaluando_ahora:
                # 👈 AQUÍ SE MUESTRA EL TEXTO DE CARGA EN LA TABLA
                st.markdown('<div class="cargando-tabla">Procesando...</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="text-align:center; font-size:14px; color:#A0AABF;">-</div>', unsafe_allow_html=True)

        # 5. Columna de Acción (Botón Evaluar)
        with cols[6]:
            # Se puede evaluar cuando el estudiante ya pasó por TODAS sus estaciones
            # (aunque en alguna no haya guardado respuestas porque se le acabó el tiempo)
            disabled_eval = (
                (intentadas < total_casos) 
                or (total_casos == 0)
                or evaluando_ahora # 👈 Deshabilitar el botón mientras se procesa
            )
            if total_casos == 0:
                ayuda = "El estudiante no tiene circuito con estaciones"
            elif intentadas < total_casos:
                ayuda = f"Se habilita cuando el estudiante pase por todas sus estaciones ({intentadas}/{total_casos})"
            elif url_pdf_existente:
                ayuda = "Vuelve a evaluar con el chatbot y genera un PDF nuevo (el anterior se conserva en el almacenamiento)"
            else:
                ayuda = "Genera la evaluación del chatbot (PDF)"
            
            etiqueta_btn = "Re-evaluar" if url_pdf_existente else "Evaluar"
            if st.button(etiqueta_btn, key=f"eval_{matricula}", disabled=disabled_eval, use_container_width=True, help=ayuda):
                st.session_state[f"evaluando_{matricula}"] = True
                st.rerun()

        # 👈 LÓGICA DE EVALUACIÓN CON STATUS ESTILIZADO 👈
        if evaluando_ahora:
            # Usamos CSS para empujar el status a la derecha y que se vea alineado con la columna
            st.markdown('<div style="margin-left: 45%; margin-top: -15px; margin-bottom: 15px;">', unsafe_allow_html=True)
            
            with st.status(f"Evaluando a {nombre}...", expanded=True) as status:
                class StatusProgress:
                    def progress(self, val, text=""):
                        status.update(label=text)
                
                prog = StatusProgress()
                
                exito, resultado = evaluar_estudiante_completo(matricula, nombre, circuito_nombre, prog)
                
                if exito:
                    status.update(label="Subiendo PDF a la nube...", state="running")
                    url_pdf = subir_pdf_a_supabase(resultado, matricula, circuito_nombre)
                    
                    if url_pdf:
                        status.update(label="¡Evaluación completada con éxito!", state="complete")
                        st.session_state[f"evaluando_{matricula}"] = False
                        os.remove(resultado)
                        st.rerun() 
                    else:
                        status.update(label="Error al subir a Supabase", state="error")
                        st.session_state[f"evaluando_{matricula}"] = False
                else:
                    status.update(label=f"Error: {resultado}", state="error")
                    st.session_state[f"evaluando_{matricula}"] = False
            
            st.markdown('</div>', unsafe_allow_html=True)
                
        st.markdown("---")