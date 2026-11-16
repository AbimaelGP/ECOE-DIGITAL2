# escenas/escena_admin_resultados.py
import streamlit as st
from datetime import datetime
import pandas as pd
import io
from utils.supabase_client import supabase

# Diccionario para traducir el número del área al nombre real
NOMBRES_AREAS = {
    1: "Medicina Familiar",
    2: "Medicina Interna",
    3: "Pediatría",
    4: "Ginecología y Obstetricia",
    5: "Cirugía",
    6: "Urgencias"
}

# ==================== FUNCIONES DE RESULTADOS Y ESTADÍSTICAS ====================

def obtener_resultados_estudiantes_dinamico():
    if not supabase: return [], []
    try:
        response = supabase.table("usuarios").select("*").eq("tipo_usuario", "estudiante").execute()
        
        areas_activas = set()
        try:
            act_resp = supabase.table("actividad_estudiante").select("modulo_actual").execute()
            for act in act_resp.data:
                if act.get("modulo_actual"):
                    areas_activas.add(int(act["modulo_actual"]))
        except: pass
        
        if not areas_activas: areas_activas = {1, 2}
        areas_ordenadas = sorted(list(areas_activas))
        
        resultados = []
        for user in response.data:
            matricula = user["identificador"]
            fila = {"Matrícula": matricula, "Alumno": user["nombre"], "Estatus": "Aprobado"}
            
            tiempo_total_segundos = 0
            calificaciones_numericas = []
            
            for area_id in areas_ordenadas:
                dur_str = "00:00"
                calif_val = ""
                
                try:
                    r_mod = supabase.table("actividad_estudiante").select("*").eq("matricula", matricula).eq("modulo_actual", area_id).execute()
                    if r_mod.data:
                        regs = sorted(r_mod.data, key=lambda x: x.get("hora_inicio_sesion", ""))
                        if regs[0].get("hora_inicio_sesion") and regs[-1].get("hora_ultima_actividad"):
                            h_ini = datetime.fromisoformat(regs[0]["hora_inicio_sesion"].replace('Z', '+00:00'))
                            h_fin = datetime.fromisoformat(regs[-1]["hora_ultima_actividad"].replace('Z', '+00:00'))
                            dur = h_fin - h_ini
                            segs = int(dur.total_seconds())
                            tiempo_total_segundos += segs
                            dur_str = f"{segs // 60:02d}:{segs % 60:02d}"
                except: pass
                
                fila[f"Área {area_id} - Duración"] = dur_str
                calif_mostrar = calif_val if calif_val else "Pendiente"
                fila[f"Área {area_id} - Calificación"] = calif_mostrar
                
                if calif_mostrar != "Pendiente":
                    try: calificaciones_numericas.append(float(calif_mostrar))
                    except: pass
            
            if calificaciones_numericas:
                calif_final = sum(calificaciones_numericas) / len(calificaciones_numericas)
                fila["Calificación Final"] = f"{calif_final:.1f}"
            else:
                fila["Calificación Final"] = "Pendiente"
            
            fila["Tiempo Total"] = f"{tiempo_total_segundos // 60:02d}:{tiempo_total_segundos % 60:02d} min"
            fila["Tiempo Total Segundos"] = tiempo_total_segundos
            resultados.append(fila)
            
        return resultados, areas_ordenadas
    except Exception as e:
        print(f"Error: {e}")
        return [], []

def obtener_estadisticas_completas():
    resultados, areas_detectadas = obtener_resultados_estudiantes_dinamico()
    if not resultados: return None
    
    total = len(resultados)
    aprobados = len([r for r in resultados if r["Estatus"] == "Aprobado"])
    no_aprobados = total - aprobados
    
    tiempos_totales = [r["Tiempo Total Segundos"] for r in resultados if r["Tiempo Total Segundos"] > 0]
    t_prom_seg = sum(tiempos_totales) / len(tiempos_totales) if tiempos_totales else 0
    t_prom_format = f"{int(t_prom_seg // 60):02d}:{int(t_prom_seg % 60):02d}"
    
    califs = []
    for r in resultados:
        if r["Calificación Final"] != "Pendiente":
            try: califs.append(float(r["Calificación Final"]))
            except: pass
    prom_general = sum(califs) / len(califs) if califs else 0
    
    stats_areas = []
    for area_id in areas_detectadas:
        duraciones = []
        califs_area = []
        aprobados_area = 0
        
        for r in resultados:
            dur_str = r.get(f"Área {area_id} - Duración", "00:00")
            calif_str = r.get(f"Área {area_id} - Calificación", "Pendiente")
            
            try:
                m, s = map(int, dur_str.split(":"))
                if m + s > 0: 
                    duraciones.append((m * 60) + s)
                    aprobados_area += 1 
            except: pass
            
            if calif_str != "Pendiente":
                try: califs_area.append(float(calif_str))
                except: pass
        
        t_prom_area = sum(duraciones) / len(duraciones) if duraciones else 0
        prom_calif_area = sum(califs_area) / len(califs_area) if califs_area else 0
        reprobados_area = len(duraciones) - aprobados_area if len(duraciones) > 0 else 0
        
        # Calcular dificultad
        dificultad = "Sin datos"
        color_dif = "#626779"
        if prom_calif_area > 0:
            if prom_calif_area >= 8: dificultad = "Fácil"; color_dif = "#008A4B"
            elif prom_calif_area >= 6: dificultad = "Moderada"; color_dif = "#ffc107"
            else: dificultad = "Difícil"; color_dif = "#dc3545"

        stats_areas.append({
            "Area_ID": area_id,
            "Nombre": NOMBRES_AREAS.get(area_id, f"Área {area_id}"),
            "Tiempo_Minutos": round(t_prom_area / 60, 1),
            "Calificacion_Promedio": round(prom_calif_area, 2),
            "Porcentaje_Aprobados": 100 if len(duraciones) > 0 else 0,
            "Aprobados_Area": aprobados_area,
            "No_Aprobados_Area": reprobados_area,
            "Evaluados": len(duraciones),
            "Dificultad": dificultad,
            "Color": color_dif
        })

    return {
        "total_estudiantes": total,
        "aprobados": aprobados,
        "no_aprobados": no_aprobados,
        "porcentaje_aprobados": round((aprobados / total * 100) if total > 0 else 0, 1),
        "porcentaje_no_aprobados": round((no_aprobados / total * 100) if total > 0 else 0, 1),
        "tiempo_promedio": t_prom_format,
        "promedio_general": round(prom_general, 2),
        "stats_areas": stats_areas
    }

def generar_nombre_archivo_resultados():
    ahora = datetime.now()
    sufijo = "a" if 1 <= ahora.month <= 6 else "b"
    return f"resultados-ecoe-{ahora.year}-{sufijo}.xlsx"

def generar_nombre_archivo_estadisticas():
    ahora = datetime.now()
    sufijo = "a" if 1 <= ahora.month <= 6 else "b"
    return f"estadisticas-ecoe-{ahora.year}-{sufijo}.xlsx"

# ==================== RENDERIZADO ====================

def mostrar():
    st.markdown("""
    <style>
        .minimal-card { background-color: #FFFFFF; border-radius: 8px; padding: 12px 15px; border: 1px solid #E5E7EC; margin-top: 0.5rem; margin-bottom: 1rem; }
        .minimal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #E5E7EC; }
        .minimal-nombre { color: #252A38; font-size: 18px; font-weight: 600; margin: 0; }
        .minimal-matricula { color: #626779; font-size: 13px; margin-top: 2px; }
        .minimal-tiempo { color: #626779; font-size: 13px; text-align: right; }
        .minimal-tiempo strong { color: #252A38; font-size: 15px; }
        .area-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #E5E7EC; }
        .area-row:last-child { border-bottom: none; }
        .area-nombre { color: #303442; font-weight: 500; font-size: 13px; width: 30%; }
        .area-duracion { color: #626779; font-size: 13px; width: 35%; }
        .area-calificacion { color: #303442; font-size: 13px; text-align: right; width: 35%; }
        .area-calificacion span { color: #70257E; font-weight: 600; }
        .estatus-aprobado { color: #008A4B; font-weight: 600; font-size: 14px; }
        .estatus-reprobado { color: #dc3545; font-weight: 600; font-size: 14px; }
        .kpi-card { background-color: #FFFFFF; border-radius: 12px; padding: 1.2rem; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 5px solid #70257E; height: 100%; }
        .kpi-value { color: #252A38; font-size: 32px; font-weight: 700; margin: 0; }
        .kpi-label { color: #626779; font-size: 13px; text-transform: uppercase; font-weight: 600; letter-spacing: 1px; }
        .kpi-trend { font-size: 13px; margin-top: 5px; font-weight: 500; }
        .stButton button[key="btn_descargar_excel_resultados"], .stButton button[key="btn_confirmar_descarga_excel"], .stButton button[key="btn_descargar_excel_estadisticas"], .stButton button[key="btn_confirmar_descarga_estadisticas"] { background-color: #70257E !important; color: #FFFFFF !important; border-radius: 8px !important; padding: 0.4rem 1rem !important; font-size: 14px !important; }
    </style>
    """, unsafe_allow_html=True)
    
    sub_tab_res, sub_tab_est = st.tabs(["Resultados", "Estadísticas"])
    
    # ==================== PESTAÑA RESULTADOS ====================
    with sub_tab_res:
        st.markdown("### Resultados de Estudiantes")
        resultados, areas_detectadas = obtener_resultados_estudiantes_dinamico()
        
        if resultados:
            df = pd.DataFrame(resultados)
            columnas_tabla = ["Alumno", "Matrícula", "Calificación Final", "Tiempo Total", "Estatus"]
            st.dataframe(df[columnas_tabla], use_container_width=True, hide_index=True,
                column_config={
                    "Alumno": st.column_config.TextColumn("Alumno", width="large"),
                    "Matrícula": st.column_config.TextColumn("Matrícula", width="medium"),
                    "Calificación Final": st.column_config.TextColumn("Calificación Final", width="small"),
                    "Tiempo Total": st.column_config.TextColumn("Tiempo Total", width="small"),
                    "Estatus": st.column_config.TextColumn("Estatus", width="small"),
                }
            )
            
            st.markdown("---")
            st.markdown("**Resultados individuales**")
            opciones = [f"{row['Alumno']} ({row['Matrícula']})" for index, row in df.iterrows()]
            alumno_seleccionado = st.selectbox("Selecciona un alumno para ver el desglose", options=opciones, label_visibility="collapsed")
            
            if alumno_seleccionado:
                matricula_sel = alumno_seleccionado.split("(")[1].replace(")", "")
                datos = df[df["Matrícula"] == matricula_sel].iloc[0]
                color_estatus = "estatus-aprobado" if datos['Estatus'] == 'Aprobado' else "estatus-reprobado"
                
                filas_html = ""
                for area_id in areas_detectadas:
                    nombre_area = NOMBRES_AREAS.get(area_id, f"Área {area_id}")
                    dur = datos.get(f"Área {area_id} - Duración", "00:00")
                    calif = datos.get(f"Área {area_id} - Calificación", "Pendiente")
                    filas_html += f"""<div class="area-row"><div class="area-nombre">{nombre_area}</div><div class="area-duracion">Duración: {dur} min</div><div class="area-calificacion">Calificación: <span>{calif}</span></div></div>"""
                
                html_minimal = f"""<div class="minimal-card"><div class="minimal-header"><div><p class="minimal-nombre">{datos['Alumno']}</p><p class="minimal-matricula">Matrícula: {datos['Matrícula']}</p></div><div class="minimal-tiempo">Calificación Final: <strong>{datos['Calificación Final']}</strong><br>Tiempo Total: <strong>{datos['Tiempo Total']}</strong><br><span class="{color_estatus}">{datos['Estatus']}</span></div></div>{filas_html}</div>"""
                st.markdown(html_minimal, unsafe_allow_html=True)

            st.markdown("---")
            col_exportar, _ = st.columns([1, 4])
            with col_exportar:
                if st.button("Descargar Reporte Excel", key="btn_descargar_excel_resultados"):
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='openpyxl') as w: df.to_excel(w, index=False)
                    st.download_button("Confirmar descarga", buf.getvalue(), generar_nombre_archivo_resultados(), key="btn_confirmar_descarga_excel")
        else: 
            st.info("No hay resultados disponibles")

    # ==================== PESTAÑA ESTADÍSTICAS ====================
    with sub_tab_est:
        stats = obtener_estadisticas_completas()
        
        if stats:
            st.markdown("### Resumen General")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f'<div class="kpi-card" style="border-top-color: #008A4B;"><p class="kpi-value">{stats["aprobados"]}</p><p class="kpi-label">Aprobados</p><p class="kpi-trend" style="color: #008A4B;">{stats["porcentaje_aprobados"]}% del total</p></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="kpi-card" style="border-top-color: #dc3545;"><p class="kpi-value">{stats["no_aprobados"]}</p><p class="kpi-label">No Aprobados</p><p class="kpi-trend" style="color: #dc3545;">{stats["porcentaje_no_aprobados"]}% del total</p></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="kpi-card" style="border-top-color: #70257E;"><p class="kpi-value">{stats["tiempo_promedio"]}</p><p class="kpi-label">Tiempo Promedio</p><p class="kpi-trend" style="color: #626779;">Duración total</p></div>', unsafe_allow_html=True)
            with c4:
                color_prom = "#008A4B" if stats["promedio_general"] >= 6 else "#dc3545"
                st.markdown(f'<div class="kpi-card" style="border-top-color: {color_prom};"><p class="kpi-value">{stats["promedio_general"]}</p><p class="kpi-label">Promedio General</p><p class="kpi-trend" style="color: {color_prom};">Calificación Global</p></div>', unsafe_allow_html=True)

            st.markdown("---")

            try:
                import plotly.graph_objects as go
                col_pie, col_bar_aprob = st.columns(2)
                
                with col_pie:
                    st.markdown("#### Distribución de Resultados Generales")
                    fig_pie = go.Figure(data=[go.Pie(labels=['Aprobados', 'No Aprobados'], values=[stats['aprobados'], stats['no_aprobados']], hole=0.5, marker_colors=['#008A4B', '#626779'])])
                    fig_pie.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Poppins", size=13, color="#303442"))
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col_bar_aprob:
                    st.markdown("#### Estatus por Área")
                    nombres_areas = [a['Nombre'] for a in stats['stats_areas']]
                    aprobados_area = [a['Aprobados_Area'] for a in stats['stats_areas']]
                    reprobados_area = [a['No_Aprobados_Area'] for a in stats['stats_areas']]

                    fig_bar_aprob = go.Figure(data=[
                        go.Bar(name='Aprobados', x=nombres_areas, y=aprobados_area, marker_color='#008A4B'),
                        go.Bar(name='No Aprobados', x=nombres_areas, y=reprobados_area, marker_color='#626779')
                    ])
                    fig_bar_aprob.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Poppins", size=12, color="#303442"), barmode='group')
                    st.plotly_chart(fig_bar_aprob, use_container_width=True)

                st.markdown("---")
                
                col_tiempo, col_calif = st.columns(2)
                
                with col_tiempo:
                    st.markdown("#### Tiempo Promedio por Área (min)")
                    fig_tiempo = go.Figure(data=[go.Bar(x=nombres_areas, y=[a['Tiempo_Minutos'] for a in stats['stats_areas']], marker_color='#70257E', text=[f"{a['Tiempo_Minutos']:.1f}" for a in stats['stats_areas']], textposition='auto')])
                    fig_tiempo.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Poppins", size=12, color="#303442"))
                    st.plotly_chart(fig_tiempo, use_container_width=True)
                
                with col_calif:
                    st.markdown("#### Calificación Promedio por Área")
                    fig_calif = go.Figure(data=[go.Bar(x=nombres_areas, y=[a['Calificacion_Promedio'] for a in stats['stats_areas']], marker_color='#70257E', text=[a['Calificacion_Promedio'] for a in stats['stats_areas']], textposition='auto')])
                    fig_calif.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Poppins", size=12, color="#303442"), yaxis=dict(range=[0, 10]))
                    st.plotly_chart(fig_calif, use_container_width=True)

            except ImportError:
                st.warning("Instala 'plotly' para ver las gráficas (pip install plotly)")

            st.markdown("---")

            # 4. TABLA DETALLADA MEJORADA (formato st.dataframe como en Resultados)
            st.markdown("### Resumen por Área")
            df_areas = pd.DataFrame(stats['stats_areas'])
            
            # Preparar dataframe para mostrar con emojis de dificultad
            df_areas_mostrar = df_areas[[
                "Nombre", "Evaluados", "Tiempo_Minutos", 
                "Calificacion_Promedio", "Dificultad"
            ]].copy()
            df_areas_mostrar.columns = [
                "Área", "Casos Evaluados", "Tiempo Promedio (min)", 
                "Calificación Promedio", "Nivel de Dificultad"
            ]
            
            # Agregar emojis según dificultad para mantener el indicador visual
            emoji_map = {
                "Fácil": "🟢 Fácil",
                "Moderada": "🟡 Moderada",
                "Difícil": "🔴 Difícil",
                "Sin datos": "⚪ Sin datos"
            }
            df_areas_mostrar["Nivel de Dificultad"] = df_areas_mostrar["Nivel de Dificultad"].map(emoji_map).fillna(df_areas_mostrar["Nivel de Dificultad"])
            
            # Mostrar con st.dataframe y column_config (mismo estilo que Resultados)
            st.dataframe(
                df_areas_mostrar,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Área": st.column_config.TextColumn("Área", width="large"),
                    "Casos Evaluados": st.column_config.NumberColumn("Casos Evaluados", width="small"),
                    "Tiempo Promedio (min)": st.column_config.NumberColumn(
                        "Tiempo Promedio (min)", width="small", format="%.1f"
                    ),
                    "Calificación Promedio": st.column_config.NumberColumn(
                        "Calificación Promedio", width="small", format="%.2f"
                    ),
                    "Nivel de Dificultad": st.column_config.TextColumn(
                        "Nivel de Dificultad", width="small"
                    ),
                }
            )

            # 5. EXPORTAR ESTADÍSTICAS
            st.markdown("---")
            col_exp_est, _ = st.columns([1, 4])
            with col_exp_est:
                if st.button("Descargar Estadísticas Excel", key="btn_descargar_excel_estadisticas"):
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='openpyxl') as w:
                        df_resumen = pd.DataFrame({
                            'Métrica': ['Total Estudiantes', 'Aprobados', 'No Aprobados', '% Aprobados', '% No Aprobados', 'Tiempo Promedio', 'Promedio General'],
                            'Valor': [stats['total_estudiantes'], stats['aprobados'], stats['no_aprobados'], f"{stats['porcentaje_aprobados']}%", f"{stats['porcentaje_no_aprobados']}%", stats['tiempo_promedio'], stats['promedio_general']]
                        })
                        df_resumen.to_excel(w, index=False, sheet_name='Resumen General')
                        
                        # Exportar sin columnas HTML/emoji
                        df_export = df_areas.drop(columns=['Color', 'Dificultad'])
                        df_export.to_excel(w, index=False, sheet_name='Estadisticas por Area')
                        
                    st.download_button("Confirmar descarga", buf.getvalue(), generar_nombre_archivo_estadisticas(), key="btn_confirmar_descarga_estadisticas")
        else:
            st.info("No hay datos suficientes para generar estadísticas.")