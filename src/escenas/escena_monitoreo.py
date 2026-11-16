import streamlit as st
import pandas as pd
from utils.actividad_estudiante import obtener_actividad_estudiantes, limpiar_sesiones_inactivas
from datetime import datetime
import time

def mostrar():
    """Muestra el dashboard de monitoreo en vivo"""
    
    st.markdown("""
    <style>
        .stApp {
            background-color: #F1F2F5 !important;
        }
        .stApp > div:first-child {
            background-color: #F1F2F5 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #70257E !important;
        }
        [data-testid="stSidebar"] * {
            color: #FFFFFF !important;
        }
        .monitoreo-title {
            text-align: center;
            color: #252A38;
            font-family: 'Poppins', sans-serif;
            font-size: 42px;
            font-weight: 700;
            margin-top: 1rem;
            margin-bottom: 2rem;
        }
        .section-title {
            color: #252A38;
            font-family: 'Poppins', sans-serif;
            font-size: 24px;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            border-left: 4px solid #70257E;
            padding-left: 1rem;
        }
        .stButton button {
            border-radius: 8px !important;
            font-weight: 500 !important;
        }
        .stButton button[key="btn_regresar"] {
            background-color: #E5E7EC !important;
            color: #303442 !important;
        }
        .stButton button[key="btn_actualizar"] {
            background-color: #70257E !important;
            color: #FFFFFF !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="monitoreo-title">Monitoreo en Vivo</h1>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Estudiantes en examen</div>', unsafe_allow_html=True)
    
    # Inicializar el estado para la recarga automática
    if 'ultima_actualizacion' not in st.session_state:
        st.session_state.ultima_actualizacion = time.time()
    
    tiempo_actual = time.time()
    tiempo_transcurrido = tiempo_actual - st.session_state.ultima_actualizacion
    
    # Si pasaron 15 segundos, actualizamos el tiempo ANTES de dibujar la pantalla
    if tiempo_transcurrido >= 15:
        st.session_state.ultima_actualizacion = time.time()
    
    # Formatear la hora de la última actualización
    hora_ultima_act = datetime.fromtimestamp(st.session_state.ultima_actualizacion).strftime('%H:%M:%S')
    st.caption(f"**Fecha:** {datetime.now().strftime('%d/%m/%Y')} | **Última actualización:** {hora_ultima_act}")
    
    # Limpiamos sesiones inactivas (opcional, cierra sesiones fantasma después de 5 min)
    limpiar_sesiones_inactivas(5)
    
    # Obtener estudiantes
    estudiantes = obtener_actividad_estudiantes()
    
    if estudiantes:
        # Detectar estudiantes con más de una sesión
        estudiantes_dobles = list(set([e["Matricula"] for e in estudiantes if e.get("_es_doble", False)]))
        
        df_monitoreo = pd.DataFrame(estudiantes)
        
        # Quitamos la columna interna de detección
        df_mostrar = df_monitoreo.drop(columns=['_es_doble'], errors='ignore')
        
        columnas_mostrar = [
            "Matricula", 
            "Nombre", 
            "Pantalla", 
            "Area", 
            "Hora Inicio Sesion", 
            "Ultima Actividad",
            "Direccion IP",
            "Dispositivo",
            "Sesion ID"
        ]
        df_mostrar = df_mostrar[columnas_mostrar]
        
        # Función para pintar de rojo las filas duplicadas
        def resaltar_filas(row):
            matricula = row['Matricula']
            if matricula in estudiantes_dobles:
                return ['background-color: #f8d7da; color: #721c24; font-weight: bold;'] * len(row)
            return [''] * len(row)
        
        # Aplicar estilos
        df_estilizado = df_mostrar.style.apply(resaltar_filas, axis=1)
        
        st.dataframe(
            df_estilizado,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Matricula": st.column_config.TextColumn("Matricula", width="small"),
                "Nombre": st.column_config.TextColumn("Nombre", width="large"),
                "Pantalla": st.column_config.TextColumn("Pantalla", width="medium"),
                "Area": st.column_config.TextColumn("Área", width="medium"),
                "Hora Inicio Sesion": st.column_config.TextColumn("Hora Inicio Sesion", width="small"),
                "Ultima Actividad": st.column_config.TextColumn("Ultima Actividad", width="small"),
                "Direccion IP": st.column_config.TextColumn("Direccion IP", width="small"),
                "Dispositivo": st.column_config.TextColumn("Dispositivo", width="small"),
                "Sesion ID": st.column_config.TextColumn("Sesion ID", width="small")
            }
        )
        
        st.caption(f"Total de estudiantes activos hoy: {len(estudiantes)}")
        
    else:
        st.info("No hay estudiantes activos en este momento")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])
    
    with col_btn1:
        if st.button("Actualizar ahora", use_container_width=True, key="btn_actualizar"):
            st.session_state.ultima_actualizacion = time.time()
            st.rerun()
    
    with col_btn2:
        if st.button("Regresar", use_container_width=True, key="btn_regresar"):
            st.session_state['pagina'] = 'admin'
            st.rerun()
    
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**Administrador:** {st.session_state.get('nombre', 'Admin')}")
        st.markdown(f"**ID:** {st.session_state.get('identificador', '')}")
        st.markdown("---")
        st.markdown("**Actualización automática:** Cada 15 segundos")
        st.markdown(f"**Fecha:** {datetime.now().strftime('%d/%m/%Y')}")
        
        if st.button("Cerrar sesion", use_container_width=True):
            for key in ['autenticado', 'tipo_usuario', 'identificador', 'nombre', 'permisos', 'pagina', 'session_id']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # Lógica de recarga automática
    if tiempo_transcurrido >= 15:
        st.rerun()
    else:
        # Pausa de 1 segundo antes de volver a evaluar el tiempo
        time.sleep(1)
        st.rerun()