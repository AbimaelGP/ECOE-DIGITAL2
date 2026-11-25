# escenas/escena_admin_creadores.py
import streamlit as st
from datetime import datetime
import pandas as pd
import hashlib
import io
from utils.supabase_client import supabase

# ==================== FUNCIONES DE CREADORES (MÉDICOS) ====================

def obtener_lista_modulos():
    return [
        "Medicina Familiar",
        "Medicina Interna",
        "Pediatría",
        "Ginecología y Obstetricia",
        "Cirugía",
        "Urgencias"
    ]

def _celda(valor):
    """Texto limpio de una celda de Excel (vacías → '', 380264.0 → '380264')."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()

def crear_medico_supabase(identificador, nombre_completo, modulo_asignado, contraseña, creado_por):
    if not supabase: return False, "Supabase no conectado"
    p_hash = hashlib.sha256(contraseña.encode()).hexdigest()
    try:
        supabase.table("usuarios").insert({
            "identificador": identificador, "nombre": nombre_completo, 
            "tipo_usuario": "medico", "password_hash": p_hash
        }).execute()
        supabase.table("perfiles_medicos").insert({
            "identificador": identificador, "nombre_completo": nombre_completo, "modulo_asignado": modulo_asignado
        }).execute()
        return True, "Creador de casos creado exitosamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def obtener_medicos_supabase():
    if not supabase: return []
    try:
        response = supabase.table("perfiles_medicos").select("*").order("nombre_completo").execute()
        return [{"identificador": p.get("identificador"), "nombre": p.get("nombre_completo"), "modulo_asignado": p.get("modulo_asignado"), "circuito_asignado": p.get("circuito_asignado") or "Todos"} for p in response.data]
    except Exception as e:
        print(f"Error al obtener creadores: {e}")
        return []

def obtener_lista_circuitos():
    """Circuitos existentes para ligar al médico evaluador ('Todos' = sin restricción)."""
    if not supabase: return ["Todos"]
    try:
        r = supabase.table("circuitos").select("nombre").order("nombre").execute()
        return ["Todos"] + [c["nombre"] for c in (r.data or []) if c.get("nombre")]
    except Exception:
        return ["Todos"]

def columna_circuito_disponible():
    """True si ya existe la columna circuito_asignado (migración 002)."""
    try:
        supabase.table("perfiles_medicos").select("circuito_asignado").limit(1).execute()
        return True
    except Exception:
        return False

def actualizar_campo_medico_supabase(identificador, campo, valor):
    if not supabase: return False, "Supabase no conectado"
    try:
        supabase.table("perfiles_medicos").update({campo: valor}).eq("identificador", identificador).execute()
        if campo == 'nombre_completo':
            supabase.table("usuarios").update({"nombre": valor}).eq("identificador", identificador).execute()
        return True, "Actualizado correctamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def eliminar_medico_supabase(identificador):
    if not supabase: return False, "Supabase no conectado"
    try:
        supabase.table("perfiles_medicos").delete().eq("identificador", identificador).execute()
        supabase.table("usuarios").delete().eq("identificador", identificador).execute()
        return True, "Creador de casos eliminado correctamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def generar_nombre_archivo_medicos():
    ahora = datetime.now()
    sufijo = "a" if 1 <= ahora.month <= 6 else "b"
    return f"creadores-ecoe-{ahora.year}-{sufijo}.xlsx"

# ==================== RENDERIZADO ====================

def mostrar():
    st.markdown("""
    <style>
        .section-title { color: #252A38; font-family: 'Poppins'; font-size: 24px; font-weight: 600; margin-top: 1.5rem; margin-bottom: 1rem; border-left: 4px solid #70257E; padding-left: 1rem; }
        
        /* Botones específicos de creadores */
        .stButton button[key="btn_guardar_cambios_medicos"], 
        .stButton button[key="btn_descargar_excel_medicos"], 
        .stButton button[key="btn_confirmar_descarga_medicos"] { 
            background-color: #70257E !important; 
            color: #FFFFFF !important; 
            border-radius: 8px !important;
            font-weight: 500 !important;
        }
        
        /* Inputs */
        .stTextInput input, .stSelectbox select { border: 2px solid #70257E !important; border-radius: 8px !important; background-color: #FFFFFF !important; color: #303442 !important; }
        .stTextInput input:focus, .stSelectbox select:focus { border-color: #70257E !important; box-shadow: 0 0 0 2px rgba(112, 37, 126, 0.3) !important; outline: none !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Gestión de Creadores de Casos</div>', unsafe_allow_html=True)
    tab_lista_med, tab_crear_med, tab_importar_med = st.tabs(["Lista de Creadores", "Crear Creador", "Importar y Exportar"])
    
    meds = obtener_medicos_supabase()
    
    # --- PESTAÑA LISTA ---
    with tab_lista_med:
        st.markdown("**Listado de Creadores Registrados:**")
        if meds:
            hay_circuito = columna_circuito_disponible()
            columnas_lista = ["identificador", "nombre", "modulo_asignado"] + (["circuito_asignado"] if hay_circuito else [])
            df_m = pd.DataFrame(meds)[columnas_lista]
            df_m_ed = st.data_editor(
                df_m, 
                use_container_width=True, 
                hide_index=True, 
                column_config={
                    "identificador": st.column_config.TextColumn("ID", width="small", disabled=True),
                    "nombre": st.column_config.TextColumn("Nombre", width="large"),
                    "modulo_asignado": st.column_config.SelectboxColumn("Área Asignada", width="medium", options=obtener_lista_modulos()),
                    "circuito_asignado": st.column_config.SelectboxColumn("Circuito (evaluador)", width="medium", options=obtener_lista_circuitos()),
                }
            )
            
            col_guardar, _ = st.columns([1, 3])
            with col_guardar:
                if st.button("Guardar cambios", use_container_width=True, key="btn_guardar_cambios_medicos"):
                    cambios = False
                    for idx, row in df_m_ed.iterrows():
                        original = df_m[df_m['identificador'] == row['identificador']]
                        if not original.empty:
                            if str(row['nombre']) != str(original.iloc[0]['nombre']): actualizar_campo_medico_supabase(row['identificador'], 'nombre_completo', row['nombre']); cambios = True
                            if str(row['modulo_asignado']) != str(original.iloc[0]['modulo_asignado']): actualizar_campo_medico_supabase(row['identificador'], 'modulo_asignado', row['modulo_asignado']); cambios = True
                            if hay_circuito and str(row['circuito_asignado']) != str(original.iloc[0]['circuito_asignado']):
                                valor_circ = None if row['circuito_asignado'] in (None, "", "Todos") else row['circuito_asignado']
                                actualizar_campo_medico_supabase(row['identificador'], 'circuito_asignado', valor_circ); cambios = True
                    if cambios: st.success("Guardado"); st.rerun()
                    else: st.info("No hay cambios")
            
            st.markdown("---")
            col_del_med, _ = st.columns([1, 2])
            with col_del_med:
                med_del = st.selectbox("Eliminar creador", [m["identificador"] for m in meds])
                if st.button("Eliminar Creador"): 
                    eliminar_medico_supabase(med_del)
                    st.rerun()
        else: 
            st.info("No hay creadores registrados")
    
    # --- PESTAÑA CREAR ---
    with tab_crear_med:
        st.markdown("**Crear Creador de Casos Individual**")
        
        # Mensaje de éxito del alta anterior (sobrevive al rerun)
        msg_ok = st.session_state.pop("medico_creado_msg", None)
        if msg_ok:
            st.success(msg_ok)
        
        # Cambiar este número genera widgets nuevos → todos los campos vuelven a quedar vacíos
        n_form = st.session_state.setdefault("form_crear_medico_n", 0)
        
        with st.form(f"form_crear_medico_{n_form}"):
            c1, c2 = st.columns(2)
            with c1: 
                id_n = st.text_input("ID (Identificador) *", placeholder="Ej: creador3", key=f"med_id_{n_form}")
                nom_n = st.text_input("Nombre completo *", placeholder="Ej: Dr. Juan Pérez", key=f"med_nom_{n_form}")
            with c2: 
                mod_n = st.selectbox("Área Asignada *", options=obtener_lista_modulos(), key=f"med_mod_{n_form}")
                p_n = st.text_input("Contraseña *", type="password", placeholder="Mínimo 6 caracteres", key=f"med_pass_{n_form}")
            
            if st.form_submit_button("Crear Creador", use_container_width=True):
                id_n, nom_n = (id_n or "").strip(), (nom_n or "").strip()
                if id_n and nom_n and p_n:
                    ex, msg = crear_medico_supabase(id_n, nom_n, mod_n, p_n, st.session_state.get('identificador', 'admin'))
                    if ex:
                        st.session_state["medico_creado_msg"] = f"Perfil de médico creado: {nom_n} ({id_n}) — Área: {mod_n}"
                        st.session_state["form_crear_medico_n"] = n_form + 1
                        st.rerun()
                    else: st.error(msg)
                else: 
                    st.error("Datos incompletos")
    
    # --- PESTAÑA IMPORTAR Y EXPORTAR ---
    with tab_importar_med:
        st.markdown("### Importar Creadores desde Excel")
        st.caption("Formato requerido: Columnas 'identificador', 'nombre_completo', 'modulo_asignado', 'contraseña'")
        
        archivo_excel_med = st.file_uploader("Subir archivo Excel", type=['xlsx', 'xls'], key="upload_medicos_masivo")
        
        if archivo_excel_med:
            try:
                df_import_med = pd.read_excel(archivo_excel_med, dtype=str)
                st.write("Vista previa de los datos a importar:")
                st.dataframe(df_import_med.head(), use_container_width=True)
                
                if st.button("Confirmar Importación", key="btn_confirmar_importacion_medicos"):
                    creado_por = st.session_state.get('identificador', 'admin')
                    exitos, errores = 0, 0
                    for _, row in df_import_med.iterrows():
                        identificador = _celda(row.get('identificador'))
                        nombre = _celda(row.get('nombre_completo'))
                        modulo = _celda(row.get('modulo_asignado'))
                        contraseña = _celda(row.get('contraseña'))
                        if not (identificador or nombre or modulo or contraseña):
                            continue  # fila vacía
                        
                        if identificador and nombre and modulo and contraseña:
                            exito, _ = crear_medico_supabase(identificador, nombre, modulo, contraseña, creado_por)
                            if exito: exitos += 1
                            else: errores += 1
                        else: errores += 1
                    st.success(f"Importación completada: {exitos} exitosos, {errores} errores")
                    st.rerun()
            except Exception as e: 
                st.error(f"Error al leer el archivo: {e}")
        
        st.markdown("---")
        
        # --- EXPORTAR (Diseño recuperado) ---
        st.markdown("### Exportar Lista de Creadores")
        st.caption("Descarga la lista completa de creadores registrados en formato Excel")
        
        if meds:
            df_exportar_med = pd.DataFrame(meds)
            
            # Renombrar columnas para el Excel
            columnas_exp = ["identificador", "nombre", "modulo_asignado"]
            df_exportar_med = df_exportar_med[[col for col in columnas_exp if col in df_exportar_med.columns]]
            df_exportar_med.columns = ["ID", "Nombre Completo", "Área Asignada"]
            
            st.caption(f"Total de creadores a exportar: {len(df_exportar_med)}")
            
            col_exportar_med, _ = st.columns([1, 4])
            with col_exportar_med:
                if st.button("Descargar Excel", use_container_width=True, key="btn_descargar_excel_medicos"):
                    nombre_archivo = generar_nombre_archivo_medicos()
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_exportar_med.to_excel(writer, index=False, sheet_name='Creadores')
                    
                    st.download_button(
                        label="Confirmar descarga",
                        data=buffer.getvalue(),
                        file_name=nombre_archivo,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="btn_confirmar_descarga_medicos"
                    )
        else:
            st.info("No hay creadores registrados para exportar")
