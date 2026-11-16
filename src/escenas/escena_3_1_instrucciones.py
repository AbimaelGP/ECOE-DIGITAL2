# escenas/escena_3_1_instrucciones.py
import streamlit as st
from datetime import datetime
import time
from utils.actividad_estudiante import actualizar_actividad_estudiante

def mostrar():
    """Muestra la pantalla de instrucciones con fondo blanco"""
    
    matricula = st.session_state['identificador']
    
    # Registrar actividad - estudiante en instrucciones
    actualizar_actividad_estudiante(matricula, "instrucciones")
    
    # Inicializar estado
    if 'tiempo_inicio_instrucciones' not in st.session_state:
        st.session_state['tiempo_inicio_instrucciones'] = datetime.now()
    if 'instrucciones_terminadas' not in st.session_state:
        st.session_state['instrucciones_terminadas'] = False
    if 'examen_iniciado' not in st.session_state:
        st.session_state['examen_iniciado'] = False
    
    # Calcular tiempo transcurrido
    tiempo_inicio = st.session_state['tiempo_inicio_instrucciones']
    tiempo_transcurrido = (datetime.now() - tiempo_inicio).total_seconds()
    tiempo_restante = max(0, 90 - int(tiempo_transcurrido))
    
    # CSS
    st.markdown("""
    <style>
        .stApp {
            background: #F1F2F5 !important;
        }
        .instrucciones-titulo {
            color: #252A38;
            font-size: 32px;
            font-weight: 700;
            text-align: center;
            margin-top: 3rem;
            margin-bottom: 2rem;
            font-family: 'Poppins', sans-serif;
        }
        .instrucciones-contenido {
            background-color: #FFFFFF;
            border-radius: 20px;
            padding: 2rem;
            max-width: 800px;
            margin: 0 auto;
            font-family: 'Poppins', sans-serif;
            color: #303442;
            line-height: 1.6;
        }
        .instrucciones-contenido p {
            font-size: 18px;
            margin-bottom: 1rem;
        }
        .instrucciones-contenido ul {
            margin-left: 2rem;
        }
        .instrucciones-contenido li {
            margin: 0.5rem 0;
            font-size: 16px;
        }
        .tiempo-restante {
            text-align: center;
            margin: 2rem auto;
            font-size: 24px;
            font-weight: 600;
            color: #70257E;
            font-family: monospace;
            background-color: #FFFFFF;
            display: inline-block;
            padding: 0.5rem 1.5rem;
            border-radius: 50px;
        }
        .tiempo-container {
            text-align: center;
        }
        .stButton {
            display: flex;
            justify-content: center;
            width: 100%;
        }
        .stButton > button {
            background-color: #70257E;
            color: #FFFFFF;
            font-family: 'Poppins', sans-serif;
            font-weight: 500;
            padding: 0.75rem 2rem;
            border-radius: 10px;
            border: none;
            width: 200px;
            margin: 0 auto;
            display: block;
        }
        .stButton > button:hover {
            background-color: #70257E;
        }
    </style>
    """, unsafe_allow_html=True)

    # Título
    st.markdown('<h1 class="instrucciones-titulo">Instrucciones</h1>', unsafe_allow_html=True)
    
    # Contenido de instrucciones
    st.markdown("""
    <div class="instrucciones-contenido">
        <p>Bienvenido a ECOE Digital.</p>
        <p>Por favor, sigue las siguientes indicaciones:</p>
        <ul>
            <li>Lee cuidadosamente cada instrucción.</li>
            <li>Recuerda que esto es una evaluación, contesta con profesionalismo.</li>
            <li>Una vez que avances, no podrás regresar.</li>
            <li>Todas tus acciones serán guardadas en un registro.</li>
            <li>El tiempo empieza a partir de que continues de esta página.</li>
        </ul>
        <p>Cuando estés listo, presiona "Continuar" para comenzar.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Contador de tiempo
    st.markdown(f"""
    <div class="tiempo-container">
        <div class="tiempo-restante">
            Tiempo restante: {tiempo_restante} segundos
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Botón Continuar
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Continuar", key="continuar_btn", use_container_width=True):
            if not st.session_state['examen_iniciado']:
                # Guardar tiempo de inicio del examen
                st.session_state['tiempo_inicio_examen'] = datetime.now()
                st.session_state['examen_iniciado'] = True
            
            st.session_state['instrucciones_terminadas'] = True
            st.session_state['pagina'] = 'seleccion_a'
            
            # Registrar actividad - estudiante va a selección de circuito
            actualizar_actividad_estudiante(matricula, "seleccion_a")
            st.rerun()
    
    # Verificar si pasaron 90 segundos (cierre automático)
    if tiempo_restante <= 0 and not st.session_state['instrucciones_terminadas']:
        if not st.session_state['examen_iniciado']:
            st.session_state['tiempo_inicio_examen'] = datetime.now()
            st.session_state['examen_iniciado'] = True
        
        st.session_state['instrucciones_terminadas'] = True
        st.session_state['pagina'] = 'seleccion_a'
        
        # Registrar actividad - estudiante va a selección de circuito (cierre automático)
        actualizar_actividad_estudiante(matricula, "seleccion_a")
        st.rerun()
    
    # Forzar actualización para que el contador se actualice visualmente
    if tiempo_restante > 0:
        time.sleep(1)
        st.rerun()