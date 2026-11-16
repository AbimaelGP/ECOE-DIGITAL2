# utils/chat_paciente.py
import streamlit as st
from chatbot.adaptador_bot import responder_como_paciente
from chatbot.prompt_constructor import crear_prompt_paciente

def mostrar_chatbot(caso_id):
    """
    Muestra el chat con el paciente virtual.
    
    Args:
        caso_id: Identificador del caso (ej: MF0001, MI0001)
    """
    
    # ===== INICIALIZAR PROMPT DEL PACIENTE =====
    prompt_key = f"prompt_{caso_id}"
    if prompt_key not in st.session_state:
        st.session_state[prompt_key] = crear_prompt_paciente(caso_id)
    
    # ===== INICIALIZAR HISTORIAL DEL CHAT =====
    chat_key = f"chat_{caso_id}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    
    # ===== CSS PARA EL CHAT =====
    st.markdown("""
    <style>
    .chat-container {
        height: 350px;
        overflow-y: auto;
        padding: 0.5rem;
        display: flex;
        flex-direction: column;
        margin-bottom: 0.5rem;
        border: 1px solid #E5E7EC;
        border-radius: 8px;
        background: #FFFFFF;
    }
    .chat-message {
        display: flex;
        margin: 0.5rem 0;
        align-items: flex-start;
    }
    .chat-message-user {
        justify-content: flex-end;
    }
    .chat-message-bot {
        justify-content: flex-start;
    }
    .bubble-user {
        background-color: #70257E;
        color: #FFFFFF;
        border-radius: 20px 4px 20px 20px;
        padding: 0.5rem 1rem;
        max-width: 70%;
        font-size: 14px;
        line-height: 1.4;
    }
    .bubble-bot {
        background-color: #E5E7EC;
        color: #303442;
        border-radius: 4px 20px 20px 20px;
        padding: 0.5rem 1rem;
        max-width: 70%;
        font-size: 14px;
        line-height: 1.4;
    }
    .avatar {
        width: 35px;
        height: 35px;
        border-radius: 50%;
        margin: 0 0.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ===== MOSTRAR MENSAJES DEL CHAT =====
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    if not st.session_state[chat_key]:
        st.markdown("""
        <div class="chat-message chat-message-bot">
            <div class="avatar">👤</div>
            <div class="bubble-bot">Hola Dr. gracias por atenderme. </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state[chat_key]:
            if msg["role"] == "assistant":
                st.markdown(f"""
                <div class="chat-message chat-message-bot">
                    <div class="avatar">👤</div>
                    <div class="bubble-bot">{msg["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message chat-message-user">
                    <div class="bubble-user">{msg["content"]}</div>
                    <div class="avatar">🧑‍⚕️</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ===== INPUT DEL CHAT CON FORMULARIO =====
    with st.form(key=f"chat_form_{caso_id}", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            pregunta = st.text_input(
                "Escribe tu mensaje...",
                key=f"chat_input_{caso_id}",
                placeholder="Escribe tu pregunta al paciente...",
                label_visibility="collapsed"
            )
        with col2:
            enviar = st.form_submit_button("Enviar", use_container_width=True)
        
        if enviar and pregunta:
            # Agregar mensaje del usuario
            st.session_state[chat_key].append({"role": "user", "content": pregunta})
            
            # Obtener respuesta del paciente
            prompt = st.session_state[prompt_key]
            respuesta = responder_como_paciente(pregunta, prompt)
            
            # Agregar respuesta del bot
            st.session_state[chat_key].append({"role": "assistant", "content": respuesta})
            
            # Recargar para mostrar los nuevos mensajes
            st.rerun()