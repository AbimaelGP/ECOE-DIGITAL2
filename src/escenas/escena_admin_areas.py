# escenas/escena_admin_areas.py
import streamlit as st
from datetime import datetime, time
from utils.horario import ahora as ahora_local, leer_fecha, leer_hora
import pandas as pd
import random
import hashlib
import io
from utils.supabase_client import supabase
from components.modal_historial import ver_caso_modal

# ==================== FUNCIONES DE CIRCUITOS ====================

def obtener_circuitos_supabase():
    if not supabase: return []
    try:
        response = supabase.table("circuitos").select("*").order("nombre").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error al obtener circuitos: {e}")
        return []

def crear_circuito_supabase(datos):
    if not supabase: return False, "Supabase no conectado"
    try:
        datos_completos = {
            "nombre": datos.get("nombre", ""),
            "creado_por": datos.get("creado_por", ""),
            "activo": True
        }
        for i in range(1, 7):
            datos_completos[f"modulo_{i}"] = datos.get(f"modulo_{i}", "")
            datos_completos[f"caso_{i}"] = datos.get(f"caso_{i}", "")
        
        supabase.table("circuitos").insert(datos_completos).execute()
        return True, "Circuito creado exitosamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def actualizar_circuito_supabase(circuito_id, datos):
    if not supabase: return False, "Supabase no conectado"
    try:
        datos_actualizados = {"nombre": datos.get("nombre", ""), "creado_por": datos.get("creado_por", "")}
        for i in range(1, 7):
            datos_actualizados[f"modulo_{i}"] = datos.get(f"modulo_{i}", "")
            datos_actualizados[f"caso_{i}"] = datos.get(f"caso_{i}", "")
        
        supabase.table("circuitos").update(datos_actualizados).eq("id", circuito_id).execute()
        return True, "Circuito actualizado exitosamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def eliminar_circuito_supabase(circuito_id):
    if not supabase: return False, "Supabase no conectado"
    try:
        supabase.table("circuitos").delete().eq("id", circuito_id).execute()
        return True, "Circuito eliminado"
    except Exception as e:
        return False, f"Error: {str(e)}"

def obtener_casos_disponibles():
    if not supabase: return []
    try:
        response = supabase.table("casos_clinicos").select("clave_caso, especialidad, data").execute()
        casos = []
        for caso in response.data:
            data = caso.get('data', {})
            casos.append({
                "clave_caso": caso.get('clave_caso', ''),
                "especialidad": caso.get('especialidad', ''),
                "titulo": data.get('nombre', caso.get('clave_caso', ''))
            })
        return casos
    except Exception as e:
        print(f"Error al obtener casos: {e}")
        return []

def obtener_lista_modulos():
    return ["Medicina Familiar", "Medicina Interna", "Pediatría", "Ginecología y Obstetricia", "Cirugía", "Urgencias"]

def mostrar_previsualizacion_caso(clave_caso):
    if not supabase or not clave_caso: return
    try:
        response = supabase.table("casos_clinicos").select("*").eq("clave_caso", clave_caso).execute()
        if response.data and len(response.data) > 0:
            caso = response.data[0]
            data_paciente = caso.get('data', {})
            
            st.markdown("""
            <div style="background-color: #FFFFFF; border-radius: 8px; padding: 1rem; margin-top: 0.5rem; border-left: 4px solid #70257E; color: #303442;">
                <p style="margin: 0; font-weight: 600; color: #252A38;">Previsualizacion del caso</p>
                <p style="margin: 0.25rem 0; font-size: 14px;"><strong>Clave:</strong> {clave}</p>
                <p style="margin: 0.25rem 0; font-size: 14px;"><strong>Paciente:</strong> {nombre}</p>
                <p style="margin: 0.25rem 0; font-size: 14px;"><strong>Edad:</strong> {edad} años</p>
                <p style="margin: 0.25rem 0; font-size: 14px;"><strong>Sexo:</strong> {sexo}</p>
                <p style="margin: 0.25rem 0; font-size: 14px;"><strong>Motivo:</strong> {motivo}</p>
            </div>
            """.format(
                clave=caso.get('clave_caso', 'N/A'),
                nombre=data_paciente.get('nombre', 'No disponible'),
                edad=data_paciente.get('edad', 'N/A'),
                sexo=data_paciente.get('sexo', 'N/A'),
                motivo=data_paciente.get('motivo_consulta', 'No disponible')
            ), unsafe_allow_html=True)
    except Exception as e:
        st.warning("No se pudo cargar la previsualizacion del caso")

def mostrar_formulario_circuito(circuito=None, modo="crear"):
    especialidades_disponibles = ["No asignar", "Medicina Familiar", "Medicina Interna", "Pediatría", "Ginecología y Obstetricia", "Cirugía", "Urgencias"]
    todos_los_casos = obtener_casos_disponibles()
    casos_por_especialidad = {}
    
    for caso in todos_los_casos:
        especialidad = caso.get('especialidad', '')
        if especialidad:
            if especialidad not in casos_por_especialidad:
                casos_por_especialidad[especialidad] = []
            casos_por_especialidad[especialidad].append(caso)
    
    st.markdown("""
    <style>
        .stExpander { background-color: #FFFFFF !important; border-radius: 8px !important; border: 1px solid #E5E7EC !important; margin-bottom: 0.5rem !important; }
        .stExpander > div { background-color: #FFFFFF !important; }
        .stSelectbox > div > div { background-color: #FFFFFF !important; }
        .stSelectbox select { background-color: #FFFFFF !important; }
        .stFormSubmitButton button { background-color: #70257E !important; color: #FFFFFF !important; border-radius: 8px !important; padding: 0.25rem 1rem !important; font-size: 14px !important; border: none !important; }
        .stFormSubmitButton button:hover { background-color: #70257E !important; }
    </style>
    """, unsafe_allow_html=True)
    
    if modo == "crear":
        st.markdown('<p class="card-title">Crear Nuevo Circuito</p>', unsafe_allow_html=True)
    else:
        st.markdown(f'<p class="card-title">Editar Circuito: {circuito.get("nombre", "")}</p>', unsafe_allow_html=True)
    
    for i in range(1, 7):
        key = f'mostrar_casos_mod_{i}'
        if key not in st.session_state:
            if modo == "editar" and circuito:
                especialidad_actual = circuito.get(f"modulo_{i}", "")
                if especialidad_actual and especialidad_actual != "No asignar":
                    st.session_state[key] = especialidad_actual
                else: st.session_state[key] = ""
            else: st.session_state[key] = ""
    
    with st.form(key=f"form_circuito_{modo}"):
        nombre = st.text_input("Nombre del Circuito *", value=circuito.get("nombre", "") if circuito else "")
        st.markdown("---")
        st.markdown("### Configuración de Áreas")
        st.caption("Selecciona la especialidad y el caso para cada área del circuito")
        
        col1, col2 = st.columns(2)
        
        def renderizar_modulo(i, columna):
            with columna:
                with st.expander(f"Área {i}", expanded=False):
                    especialidad_actual = circuito.get(f"modulo_{i}", "") if circuito else ""
                    caso_actual = circuito.get(f"caso_{i}", "") if circuito else ""
                    try:
                        index_actual = especialidades_disponibles.index(especialidad_actual) if especialidad_actual in especialidades_disponibles else 0
                    except ValueError: index_actual = 0
                    
                    especialidad_seleccionada = st.selectbox("Especialidad", options=especialidades_disponibles, index=index_actual, key=f"esp_mod_{i}")
                    
                    if especialidad_seleccionada != st.session_state.get(f'ultima_especialidad_{i}', ''):
                        st.session_state[f'mostrar_casos_mod_{i}'] = ""
                        st.session_state[f'ultima_especialidad_{i}'] = especialidad_seleccionada
                    
                    col_btn_ver, col_espacio = st.columns([1, 3])
                    with col_btn_ver:
                        ver_casos = st.form_submit_button("Ver casos", key=f"ver_casos_submit_{i}")
                        if ver_casos:
                            st.session_state[f'mostrar_casos_mod_{i}'] = especialidad_seleccionada
                            st.rerun()
                    
                    if modo == "editar" and circuito:
                        especialidad_guardada = circuito.get(f"modulo_{i}", "")
                        if especialidad_guardada and especialidad_guardada != "No asignar":
                            if st.session_state.get(f'mostrar_casos_mod_{i}', '') == "":
                                st.session_state[f'mostrar_casos_mod_{i}'] = especialidad_guardada
                    
                    if especialidad_seleccionada == "No asignar":
                        st.caption("Este área no será utilizada en el circuito")
                        st.session_state[f'caso_mod_{i}'] = ""
                    else:
                        casos_filtrados = casos_por_especialidad.get(especialidad_seleccionada, [])
                        if casos_filtrados and st.session_state.get(f'mostrar_casos_mod_{i}', '') == especialidad_seleccionada:
                            opciones_casos = [{"clave": "", "label": "Seleccionar caso"}]
                            for caso in casos_filtrados:
                                opciones_casos.append({"clave": caso['clave_caso'], "label": f"{caso['clave_caso']} - {caso.get('titulo', caso['clave_caso'])}"})
                            
                            caso_index = 0
                            for idx, opt in enumerate(opciones_casos):
                                if opt["clave"] == caso_actual: caso_index = idx; break
                            
                            caso_seleccionado = st.selectbox("Caso", options=opciones_casos, index=caso_index, format_func=lambda x: x["label"], key=f"caso_mod_{i}")
                            
                            if caso_seleccionado and caso_seleccionado["clave"]:
                                st.session_state[f'caso_seleccionado_clave_{i}'] = caso_seleccionado["clave"]
                            else: st.session_state[f'caso_seleccionado_clave_{i}'] = ""
                            
                            if caso_seleccionado and caso_seleccionado["clave"]:
                                ver_caso_modal(caso_seleccionado["clave"], f"mod_{i}", dentro_formulario=True)
                                if st.session_state.get(f'preview_caso_{i}', '') == caso_seleccionado["clave"]:
                                    st.markdown("---")
                                    mostrar_previsualizacion_caso(caso_seleccionado["clave"])
                                    cerrar_preview = st.form_submit_button("Cerrar", key=f"cerrar_preview_submit_{i}")
                                    if cerrar_preview:
                                        st.session_state[f'preview_caso_{i}'] = ''
                                        st.rerun()
                        elif casos_filtrados:
                            st.caption(f"Presiona 'Ver casos' para mostrar los casos de {especialidad_seleccionada}")
                            st.session_state[f'caso_seleccionado_clave_{i}'] = ""
                        else:
                            st.caption("No hay casos disponibles para esta especialidad")
                            st.session_state[f'caso_seleccionado_clave_{i}'] = ""
        
        for i in range(1, 4): renderizar_modulo(i, col1)
        for i in range(4, 7): renderizar_modulo(i, col2)
        
        st.markdown("---")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("Cancelar", use_container_width=True):
                st.session_state['mostrar_formulario_circuito'] = False
                st.session_state['editando_circuito'] = None
                for i in range(1, 7):
                    for k in [f'preview_caso_{i}', f'caso_seleccionado_clave_{i}', f'mostrar_casos_mod_{i}', f'ultima_especialidad_{i}']:
                        if k in st.session_state: del st.session_state[k]
                st.rerun()
        with col_btn2:
            if st.form_submit_button("Guardar Circuito", use_container_width=True, type="primary"):
                if not nombre: st.error("El nombre del circuito es obligatorio")
                else:
                    creado_por = st.session_state.get('identificador', 'admin')
                    datos = {"nombre": nombre, "creado_por": creado_por}
                    for i in range(1, 7):
                        especialidad_key = f"esp_mod_{i}"
                        if especialidad_key in st.session_state:
                            especialidad = st.session_state[especialidad_key]
                            datos[f"modulo_{i}"] = especialidad
                            if especialidad == "No asignar": datos[f"caso_{i}"] = ""
                            else: datos[f"caso_{i}"] = st.session_state.get(f'caso_seleccionado_clave_{i}', '')
                        else:
                            datos[f"modulo_{i}"] = ""
                            datos[f"caso_{i}"] = ""
                    
                    exito, mensaje = crear_circuito_supabase(datos) if modo == "crear" else actualizar_circuito_supabase(circuito['id'], datos)
                    
                    if exito:
                        st.success(mensaje)
                        st.session_state['mostrar_formulario_circuito'] = False
                        st.session_state['editando_circuito'] = None
                        for i in range(1, 7):
                            for k in [f'preview_caso_{i}', f'caso_seleccionado_clave_{i}', f'mostrar_casos_mod_{i}', f'ultima_especialidad_{i}']:
                                if k in st.session_state: del st.session_state[k]
                        st.rerun()
                    else: st.error(mensaje)


# ==================== FUNCIONES DE ESTUDIANTES ====================

def generar_clave_acceso(): return ''.join(str(random.randint(0, 9)) for _ in range(6))

def _celda(valor):
    """Texto limpio de una celda de Excel (vacías → '', 380264.0 → '380264')."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()

def crear_estudiante_supabase(matricula, nombre_completo, contraseña, creado_por):
    if not supabase: return False, "Supabase no conectado", None
    clave_acceso = generar_clave_acceso()
    # El estudiante entra con su clave de acceso; si no se da contraseña, se usa la misma clave
    password_hash = hashlib.sha256((contraseña or clave_acceso).encode()).hexdigest()
    try:
        supabase.table("usuarios").insert({"identificador": matricula, "nombre": nombre_completo, "tipo_usuario": "estudiante", "password_hash": password_hash}).execute()
        supabase.table("perfiles_estudiantes").insert({"matricula": matricula, "nombre_completo": nombre_completo, "clave_acceso": clave_acceso, "creado_por": creado_por}).execute()
        return True, "Estudiante creado exitosamente", clave_acceso
    except Exception as e:
        return False, f"Error: {str(e)}", None

def obtener_estudiantes_supabase():
    if not supabase: return []
    try:
        response = supabase.table("usuarios").select("*").eq("tipo_usuario", "estudiante").execute()
        estudiantes = []
        for user in response.data:
            perfil_response = supabase.table("perfiles_estudiantes").select("*").eq("matricula", user["identificador"]).execute()
            perfil = perfil_response.data[0] if perfil_response.data else {}
            estudiantes.append({
                "matricula": user["identificador"], "nombre": user["nombre"], "clave_acceso": perfil.get("clave_acceso", ""),
                "numero_estudiante": perfil.get("numero_estudiante", ""), "circuito_asignado": perfil.get("circuito_asignado", ""),
                "fecha_examen": perfil.get("fecha_examen", ""), "hora_inicio": perfil.get("hora_inicio", ""),
                "hora_fin": perfil.get("hora_fin", ""), "creado_por": perfil.get("creado_por", ""), "fecha_creacion": perfil.get("fecha_creacion", "")
            })
        return estudiantes
    except Exception as e:
        print(f"Error al obtener estudiantes: {e}")
        return []

def _a_fecha(v):
    """Texto de la base → date (acepta 2026-11-20, 20/11/2026, 20-11-2026)."""
    return leer_fecha(_celda(v) if not hasattr(v, "year") else v)

def _a_hora(v):
    """Texto de la base → time (acepta 08:00, 8:00, 7, 7am…)."""
    return leer_hora(_celda(v) if not hasattr(v, "hour") else v)

def _valor_guardable(campo, v):
    """Lo que se guarda en la base: fecha YYYY-MM-DD, hora HH:MM, vacío = None (nunca NaN)."""
    if campo == "fecha_examen":
        d = _a_fecha(v); return d.strftime("%Y-%m-%d") if d else None
    if campo in ("hora_inicio", "hora_fin"):
        h = _a_hora(v); return h.strftime("%H:%M") if h else None
    t = _celda(v)
    return t or None

def actualizar_campo_estudiante_supabase(matricula, campo, valor):
    if not supabase: return False, "Supabase no conectado"
    if campo not in ['numero_estudiante', 'circuito_asignado', 'fecha_examen', 'hora_inicio', 'hora_fin']: return False, f"Campo {campo} no valido"
    try:
        supabase.table("perfiles_estudiantes").update({campo: valor}).eq("matricula", matricula).execute()
        return True, "Actualizado correctamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

# Orden de borrado (de "hijas" a "padre") porque NO hay ON DELETE CASCADE en Supabase.
# (tabla, columna con la matrícula, obligatoria)
#   obligatoria=True  → si falla, se detiene el borrado para no dejar datos a medias.
#   obligatoria=False → tablas de migraciones opcionales; si no existen se omiten.
TABLAS_ESTUDIANTE = [
    ("historial_chat_estudiante",      "matricula",     True),
    ("historial_preguntas_estudiante", "matricula",     True),
    ("evaluaciones_pdf",               "matricula",     True),
    ("actividad_estudiante",           "matricula",     False),
    ("progreso_examen",                "matricula",     False),
    ("evaluacion_estudiantes",         "matricula",     False),
    ("evaluacion_docente",             "matricula",     False),
    ("evaluacion_chatbot",             "matricula",     False),
    ("calificacion_final",             "matricula",     False),
    ("reportes_chatbot",               "matricula",     False),
    ("perfiles_estudiantes",           "matricula",     True),
    ("usuarios",                       "identificador", True),
]


def obtener_datos_respaldo_estudiante(matricula):
    """Lee todos los registros del estudiante en cada tabla (para el respaldo)."""
    datos = {}
    for tabla, columna, _ in TABLAS_ESTUDIANTE:
        try:
            filas = supabase.table(tabla).select("*").eq(columna, matricula).execute().data or []
        except Exception as e:
            print(f"⚠️ Respaldo: no se pudo leer {tabla}: {e}")
            filas = []
        if tabla == "usuarios":
            # Nunca exportar el hash de la contraseña
            filas = [{k: v for k, v in f.items() if k != "password_hash"} for f in filas]
        datos[tabla] = filas
    return datos


def generar_respaldo_estudiante_zip(matricula):
    """ZIP con respaldo.json (todas las tablas) + los PDF de evaluación si se pueden descargar."""
    import json, zipfile, requests
    datos = obtener_datos_respaldo_estudiante(matricula)
    respaldo = {
        "matricula": matricula,
        "generado": ahora_local().isoformat(),
        "tablas": datos,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("respaldo.json", json.dumps(respaldo, ensure_ascii=False, indent=2, default=str))
        for i, ev in enumerate(datos.get("evaluaciones_pdf", []), 1):
            url = ev.get("url_pdf")
            if not url:
                continue
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                z.writestr(f"evaluaciones/evaluacion_{i}.pdf", r.content)
            except Exception as e:
                print(f"⚠️ Respaldo: no se pudo descargar {url}: {e}")
    return buffer.getvalue()


def eliminar_estudiante_supabase(matricula):
    """
    Deep delete manual (sin ON DELETE CASCADE): borra al estudiante de cada tabla
    en el orden de TABLAS_ESTUDIANTE. Si falla una tabla obligatoria se detiene
    ANTES de llegar a perfiles_estudiantes/usuarios.
    """
    if not supabase: return False, "Supabase no conectado"
    if not matricula: return False, "Matrícula vacía"
    resumen = []
    for tabla, columna, obligatoria in TABLAS_ESTUDIANTE:
        try:
            r = supabase.table(tabla).delete().eq(columna, matricula).execute()
            resumen.append(f"{tabla}: {len(r.data or [])}")
        except Exception as e:
            if obligatoria:
                hecho = ", ".join(resumen) or "nada"
                return False, (f"Error al borrar de {tabla}: {e}. Se detuvo el borrado "
                               f"(ya eliminado → {hecho}). El usuario NO se borró.")
            print(f"⚠️ Se omitió {tabla} al borrar {matricula}: {e}")
            resumen.append(f"{tabla}: omitida")
    # Verificación final: que el usuario ya no exista (RLS puede impedir el delete sin error)
    try:
        sigue = supabase.table("usuarios").select("identificador").eq("identificador", matricula).execute().data
        if sigue:
            return False, "Supabase no permitió borrar el usuario (revisa las políticas RLS de la tabla usuarios)."
    except Exception:
        pass
    return True, f"Estudiante {matricula} eliminado por completo (registros borrados → {', '.join(resumen)})"

def generar_nombre_archivo_estudiantes():
    ahora = ahora_local()
    sufijo = "a" if 1 <= ahora.month <= 6 else "b"
    return f"estudiantes-ecoe-{ahora.year}-{sufijo}.xlsx"


# ==================== RENDERIZADO DE LA PESTAÑA ====================

def mostrar():
    st.markdown("""
    <style>
        .section-title { color: #252A38; font-family: 'Poppins'; font-size: 24px; font-weight: 600; margin-top: 1.5rem; margin-bottom: 1rem; border-left: 4px solid #70257E; padding-left: 1rem; }
        .card-title { color: #252A38; font-family: 'Poppins'; font-size: 18px; font-weight: 600; margin-bottom: 1rem; }
        label { color: #303442 !important; font-weight: 500 !important; }
        .stButton button { border-radius: 8px !important; font-weight: 500 !important; }
        
        /* Estilos de los botones */
        .stButton button[key="btn_anadir_circuito_admin"] { background-color: #70257E !important; color: #FFFFFF !important; }
        .stButton button[key^="ver_circuito_"], .stButton button[key^="editar_circuito_"] { background-color: #E5E7EC !important; color: #303442 !important; border: 1px solid #E5E7EC !important; }
        .stButton button[key^="ver_circuito_"]:hover, .stButton button[key^="editar_circuito_"]:hover { background-color: #E5E7EC !important; }
        
        /* Estilos de inputs */
        .stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input, .stSelectbox select { border: 2px solid #70257E !important; border-radius: 8px !important; background-color: #FFFFFF !important; color: #303442 !important; }
        .stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus, .stTimeInput input:focus, .stSelectbox select:focus { border-color: #70257E !important; box-shadow: 0 0 0 2px rgba(112, 37, 126, 0.3) !important; outline: none !important; }
        
        /* Colores de botones funcionales */
        .stButton button[key="btn_descargar_excel"], .stButton button[key="btn_activar"], .stButton button[key="btn_monitoreo"], .stButton button[key="btn_guardar_cambios"], .stButton button[key="btn_descargar_excel_estudiantes"], .stButton button[key="btn_confirmar_descarga_estudiantes"] { background-color: #70257E !important; color: #FFFFFF !important; }
        .stButton button[key="btn_desactivar"] { background-color: #dc3545 !important; color: white !important; }
        
        /* Barra azul del circuito */
        .circuito-nombre { background-color: #70257E; color: #FFFFFF; padding: 10px 16px; border-radius: 8px 0 0 8px; text-align: left; font-size: 16px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Gestión de Estudiantes</div>', unsafe_allow_html=True)
    tab_lista, tab_crear, tab_importar = st.tabs(["Lista de Estudiantes", "Crear Estudiante", "Importar y Exportar"])
    
    # --- PESTAÑA LISTA ---
    with tab_lista:
        estudiantes = obtener_estudiantes_supabase()
        if estudiantes:
            df_estudiantes = pd.DataFrame(estudiantes)
            columnas_orden = ["matricula", "nombre", "clave_acceso", "numero_estudiante", "circuito_asignado", "fecha_examen", "hora_inicio", "hora_fin"]
            df_estudiantes = df_estudiantes[[col for col in columnas_orden if col in df_estudiantes.columns]]
            # Fechas y horas como selectores (evita textos que el examen no puede interpretar)
            if "fecha_examen" in df_estudiantes: df_estudiantes["fecha_examen"] = df_estudiantes["fecha_examen"].map(_a_fecha)
            for c in ("hora_inicio", "hora_fin"):
                if c in df_estudiantes: df_estudiantes[c] = df_estudiantes[c].map(_a_hora)
            try:
                from escenas.escena_admin_creadores import obtener_lista_circuitos
                opciones_circuito = [c for c in obtener_lista_circuitos() if c != "Todos"]
            except Exception:
                opciones_circuito = None
            
            df_editado = st.data_editor(
                df_estudiantes, use_container_width=True, hide_index=True,
                column_config={
                    "matricula": "Matrícula", "nombre": "Nombre Completo", "clave_acceso": "Clave Acceso",
                    "numero_estudiante": st.column_config.NumberColumn("Número Estudiante"), "circuito_asignado": (st.column_config.SelectboxColumn("Circuito", options=opciones_circuito)
                                          if opciones_circuito else "Circuito"),
                    "fecha_examen": st.column_config.DateColumn("Fecha Examen", format="DD/MM/YYYY"),
                    "hora_inicio": st.column_config.TimeColumn("Hora Inicio", format="HH:mm", step=300),
                    "hora_fin": st.column_config.TimeColumn("Hora Fin", format="HH:mm", step=300)
                }
            )
            
            col_guardar1, col_guardar2 = st.columns([1, 3])
            if st.session_state.get("msg_tabla_estudiantes"):
                col_guardar2.success(st.session_state.pop("msg_tabla_estudiantes"))
            with col_guardar1:
                if st.button("Guardar cambios", use_container_width=True, key="btn_guardar_cambios"):
                    cambios_realizados = False
                    errores = []
                    for idx, row in df_editado.iterrows():
                        matricula = row['matricula']
                        original = df_estudiantes[df_estudiantes['matricula'] == matricula]
                        if not original.empty:
                            for campo in ['hora_inicio', 'hora_fin', 'circuito_asignado', 'fecha_examen']:
                                nuevo = _valor_guardable(campo, row[campo])
                                if nuevo != _valor_guardable(campo, original.iloc[0][campo]):
                                    exito, mensaje = actualizar_campo_estudiante_supabase(matricula, campo, nuevo)
                                    if exito: cambios_realizados = True
                                    else: errores.append(f"{matricula} - {campo}: {mensaje}")
                    
                    if errores:
                        for error in errores: st.error(f"{error}")
                    if cambios_realizados and not errores:
                        st.session_state["msg_tabla_estudiantes"] = "Cambios guardados correctamente"; st.rerun()
                    elif not cambios_realizados: st.info("No se detectaron cambios")
            
            st.markdown("---")
            col_eliminar1, col_eliminar2 = st.columns([1, 2])
            if st.session_state.get("msg_eliminar_estudiante"):
                st.success(st.session_state.pop("msg_eliminar_estudiante"))
            with col_eliminar1:
                matricula_eliminar = st.selectbox("Seleccionar matrícula para eliminar", options=[e["matricula"] for e in estudiantes], key="eliminar_matricula")
                
                # 1) Respaldo opcional antes de borrar
                clave_resp = f"respaldo_zip_{matricula_eliminar}"
                if st.button("Generar respaldo de sus datos", use_container_width=True, key="btn_generar_respaldo_est"):
                    with st.spinner("Generando respaldo..."):
                        st.session_state[clave_resp] = generar_respaldo_estudiante_zip(matricula_eliminar)
                if st.session_state.get(clave_resp):
                    st.download_button(
                        "Descargar respaldo (.zip)",
                        data=st.session_state[clave_resp],
                        file_name=f"respaldo_{matricula_eliminar}_{ahora_local().strftime('%Y%m%d_%H%M')}.zip",
                        mime="application/zip",
                        use_container_width=True,
                        key="btn_descargar_respaldo_est",
                    )
            with col_eliminar2:
                st.caption("Se borrará TODO lo del estudiante: historial de chat, respuestas, "
                           "evaluaciones, calificaciones, progreso, perfil y usuario. No se puede deshacer.")
                # 2) Doble confirmación: checkbox + escribir la matrícula
                seguro = st.checkbox(f"Estoy seguro de eliminar a {matricula_eliminar} y todos sus datos",
                                     key=f"chk_seguro_eliminar_{matricula_eliminar}")
                confirmacion = st.text_input("Escribe la matrícula para confirmar",
                                             key=f"txt_confirmar_eliminar_{matricula_eliminar}")
                listo = seguro and confirmacion.strip() == str(matricula_eliminar)
                if st.button("Eliminar Estudiante", use_container_width=True, disabled=not listo,
                             key="btn_eliminar_estudiante"):
                    with st.spinner("Eliminando registros..."):
                        exito, mensaje = eliminar_estudiante_supabase(matricula_eliminar)
                    if exito:
                        st.session_state.pop(clave_resp, None)
                        st.session_state["msg_eliminar_estudiante"] = mensaje
                        st.rerun()
                    else: st.error(mensaje)
        else:
            st.info("No hay estudiantes registrados")
    
    # --- PESTAÑA CREAR (Con diseño mejorado) ---
    with tab_crear:
        st.markdown("**Crear Estudiante Individual**")
        with st.form("form_crear_estudiante"):
            col1, col2 = st.columns(2)
            with col1:
                matricula_nueva = st.text_input("Matrícula *", placeholder="Ej: 20250001")
                nombre_nuevo = st.text_input("Nombre completo *", placeholder="Ej: Juan Pérez Gómez")
            with col2:
                st.caption("La app genera una **clave de acceso** de 6 dígitos: es con la que el estudiante "
                           "entra a la app. La verás en la tabla, columna \"Clave Acceso\".")
            
            creado_por = st.session_state.get('identificador', 'admin')
            submitted = st.form_submit_button("Crear Estudiante", use_container_width=True)
            
            if submitted:
                if not matricula_nueva or not nombre_nuevo:
                    st.error("Por favor completa todos los campos obligatorios")
                else:
                    exito, mensaje, clave = crear_estudiante_supabase(matricula_nueva.strip(), nombre_nuevo.strip(), "", creado_por)
                    if exito:
                        st.success(f"{mensaje}. Clave de acceso para entrar: **{clave}**")
                    else: st.error(mensaje)
    
    # --- PESTAÑA IMPORTAR/EXPORTAR ---
    with tab_importar:
        st.markdown("### Importar Estudiantes desde Excel")
        st.caption("Formato requerido: columnas 'matricula' y 'nombre'. La columna 'contraseña' es opcional: "
                   "cada estudiante entra con la clave de acceso que genera la app.")
        archivo_excel = st.file_uploader("Subir archivo Excel", type=['xlsx', 'xls'], key="upload_estudiantes_masivo")
        
        if archivo_excel:
            try:
                df_import = pd.read_excel(archivo_excel, dtype=str)
                st.write("Vista previa de los datos a importar:")
                st.dataframe(df_import.head(), use_container_width=True)
                if st.button("Confirmar Importación", key="btn_confirmar_importacion"):
                    creado_por = st.session_state.get('identificador', 'admin')
                    exitos, errores = 0, 0
                    for _, row in df_import.iterrows():
                        matricula = _celda(row.get('matricula', row.get('matrícula')))
                        nombre = _celda(row.get('nombre'))
                        contraseña = _celda(row.get('contraseña'))
                        if not (matricula or nombre or contraseña):
                            continue  # fila vacía
                        if matricula and nombre:
                            exito, _, _ = crear_estudiante_supabase(matricula, nombre, contraseña, creado_por)
                            if exito: exitos += 1
                            else: errores += 1
                        else: errores += 1
                    st.success(f"Importación completada: {exitos} exitosos, {errores} errores"); st.rerun()
            except Exception as e: st.error(f"Error al leer el archivo: {e}")
        
        st.markdown("---")
        st.markdown("### Exportar Lista de Estudiantes")
        st.caption("Descarga la lista completa de estudiantes registrados en formato Excel")
        
        estudiantes_exportar = obtener_estudiantes_supabase()
        if estudiantes_exportar:
            df_exportar = pd.DataFrame(estudiantes_exportar)
            columnas_exportar = ["matricula", "nombre", "clave_acceso", "numero_estudiante", "circuito_asignado", "fecha_examen", "hora_inicio", "hora_fin"]
            df_exportar = df_exportar[[col for col in columnas_exportar if col in df_exportar.columns]]
            df_exportar.columns = ["Matrícula", "Nombre Completo", "Clave de Acceso", "Número Estudiante", "Circuito", "Fecha Examen", "Hora Inicio", "Hora Fin"][:len(df_exportar.columns)]
            
            st.caption(f"Total de estudiantes a exportar: {len(df_exportar)}")
            col_exportar, _ = st.columns([1, 4])
            with col_exportar:
                if st.button("Descargar Excel", use_container_width=True, key="btn_descargar_excel_estudiantes"):
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer: df_exportar.to_excel(writer, index=False, sheet_name='Estudiantes')
                    st.download_button("Confirmar descarga", buffer.getvalue(), generar_nombre_archivo_estudiantes(), key="btn_confirmar_descarga_estudiantes")
        else: st.info("No hay estudiantes registrados para exportar")
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # ==================== GESTIÓN DE EXAMEN ====================
    st.markdown('<div class="section-title">Gestión de Examen</div>', unsafe_allow_html=True)
    
    if 'examen_activo' not in st.session_state:
        try: st.session_state['examen_activo'] = supabase.table("configuracion_examen").select("*").eq("id", 1).execute().data[0].get('examen_activo', False)
        except: st.session_state['examen_activo'] = False
    
    horas_opciones = [time(h, m) for h in range(5, 19) for m in [0, 15, 30, 45]]
    
    col_pass, col_min = st.columns(2)
    with col_pass:
        from utils.acceso_examen import obtener_contrasena_dia, guardar_contrasena_dia, listar_contrasenas
        st.markdown("**Contraseña del examen (por día)**")
        st.caption("La misma para todos los estudiantes con examen ese día. Se pide al dar \"Iniciar examen\"; "
                   "para entrar a la app cada estudiante usa su clave de acceso.")
        dia_pass = st.date_input("Día del examen", value=ahora_local().date(), key="dia_pass_examen", format="DD/MM/YYYY")
        actual = obtener_contrasena_dia(dia_pass)
        nueva_pass = st.text_input("Contraseña de examen", value=actual or "", placeholder="Ej. ECOE-1711",
                                   key=f"pass_examen_{dia_pass}")
        if st.button("Guardar contraseña del día", key="btn_guardar_pass_dia", use_container_width=True):
            ok, msg = guardar_contrasena_dia(dia_pass, nueva_pass, st.session_state.get("identificador", "admin"))
            (st.success if ok else st.error)(msg)
        registradas = listar_contrasenas(5)
        if registradas:
            st.caption("Configuradas: " + " · ".join(
                f"{leer_fecha(r['fecha']).strftime('%d/%m/%Y')}: {r['contrasena']}" for r in registradas))
    with col_min:
        from utils.evaluacion_dual import obtener_calificacion_minima, guardar_calificacion_minima
        if "calif_minima" not in st.session_state:
            guardada = obtener_calificacion_minima()
            st.session_state["calif_minima"] = "" if guardada is None else f"{guardada:g}"

        def _guardar_minima():
            texto = str(st.session_state.get("calif_minima", "")).strip().replace(",", ".")
            if not texto:
                return
            try:
                valor = float(texto)
            except ValueError:
                st.session_state["msg_calif_minima"] = ("error", "Ingresa un número válido")
                return
            if not 1 <= valor <= 10:
                st.session_state["msg_calif_minima"] = ("error", "La calificación debe estar entre 1 y 10")
                return
            ok, msg = guardar_calificacion_minima(valor, st.session_state.get("identificador", "admin"))
            st.session_state["msg_calif_minima"] = ("success" if ok else "error", msg)

        st.text_input("Calificación mínima aprobatoria", placeholder="1-10", key="calif_minima",
                      on_change=_guardar_minima, help="Se guarda al presionar Enter. Se usa para Aprobado / No aprobado en Resultados.")
        if st.session_state.get("msg_calif_minima"):
            tipo, msg = st.session_state.pop("msg_calif_minima")
            (st.success if tipo == "success" else st.error)(msg)
    
    # (Se quitaron "Fecha/Hora de inicio y término": no se guardaban ni controlaban nada.
    #  El horario que cuenta es el de cada estudiante en la tabla de estudiantes.)
    st.caption("El horario de cada estudiante se define en la tabla **Lista de Estudiantes** (Fecha Examen, Hora Inicio, Hora Fin).")
    
    col_activar, col_monitoreo = st.columns(2)
    with col_activar:
        st.markdown("**Activar Examen**")
        if st.session_state.get('examen_activo', False):
            st.markdown('<div style="background-color: #FFFFFF; border: 2px solid #008A4B; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 10px;"><span style="color: #008A4B; font-weight: bold;">ACTIVADO</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background-color: #f8d7da; border: 2px solid #dc3545; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 10px;"><span style="color: #721c24; font-weight: bold;">DESACTIVADO</span></div>', unsafe_allow_html=True)
        
        if st.button("Activar", use_container_width=True, key="btn_activar"):
            try:
                supabase.table("configuracion_examen").update({"examen_activo": True, "actualizado_por": st.session_state.get('identificador', 'admin'), "ultima_actualizacion": ahora_local().isoformat()}).eq("id", 1).execute()
                st.session_state['examen_activo'] = True; st.success("Examen activado"); st.rerun()
            except Exception as e: st.error(f"Error: {e}")
        
        if st.button("Desactivar", use_container_width=True, key="btn_desactivar"):
            try:
                supabase.table("configuracion_examen").update({"examen_activo": False, "actualizado_por": st.session_state.get('identificador', 'admin'), "ultima_actualizacion": ahora_local().isoformat()}).eq("id", 1).execute()
                st.session_state['examen_activo'] = False; st.warning("Examen desactivado"); st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    
    with col_monitoreo:
        st.markdown("**Monitoreo**")
        if st.button("Monitoreo en vivo", use_container_width=True, key="btn_monitoreo"):
            st.session_state['pagina'] = 'monitoreo'; st.rerun()
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
        # ==================== CIRCUITOS ====================
    st.markdown('<div class="section-title">Circuitos</div>', unsafe_allow_html=True)
    
    # El formulario ya no se dibuja aquí, ahora es otra escena
    circuitos = obtener_circuitos_supabase()
    if circuitos:
        for circuito in circuitos:
            col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
            with col1: 
                st.markdown(f'<div class="circuito-nombre">{circuito["nombre"]}</div>', unsafe_allow_html=True)
            with col2:
                if st.button("Ver", key=f"ver_circuito_{circuito['id']}", use_container_width=True): 
                    st.session_state['circuito_a_ver'] = circuito
                    st.session_state['mostrar_ver_circuito'] = True
                    st.rerun()
            with col3:
                # REDIRECCIÓN A LA NUEVA ESCENA
                if st.button("Editar", key=f"editar_circuito_{circuito['id']}", use_container_width=True):
                    st.session_state['editando_circuito'] = circuito
                    st.session_state['pagina'] = 'editar_circuito' # <-- Nueva ruta
                    st.rerun()
            with col4:
                if st.button("Eliminar", key=f"eliminar_circuito_{circuito['id']}", use_container_width=True):
                    exito, mensaje = eliminar_circuito_supabase(circuito['id'])
                    if exito: st.success(mensaje); st.rerun()
                    else: st.error(mensaje)
    else: 
        st.info("No hay circuitos creados")
    
    # ===== MOSTRAR MODAL DE VER CIRCUITO =====
    if st.session_state.get('mostrar_ver_circuito', False):
        from components.modal_ver_circuito import mostrar_modal_ver_circuito
        circuito_a_ver = st.session_state.get('circuito_a_ver')
        if circuito_a_ver:
            mostrar_modal_ver_circuito(circuito_a_ver)

    col_add_circuito, _ = st.columns([1, 4])
    with col_add_circuito:
        # REDIRECCIÓN A LA NUEVA ESCENA
        if st.button("+ Añadir nuevo circuito", use_container_width=True, key="btn_anadir_circuito_admin"):
            st.session_state['editando_circuito'] = None
            st.session_state['pagina'] = 'editar_circuito' # <-- Nueva ruta
            st.rerun()