# chatbot/adaptador_bot.py
import itertools
import time
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Claves de Gemini desde la variable de entorno GEMINI_API_KEY (puede ser una lista separada por comas)
API_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEY", "").split(",") if k.strip()] or [""]

key_cycler = itertools.cycle(API_KEYS)

def get_next_key():
    return next(key_cycler)

def responder_como_paciente(pregunta, prompt_base, historial=None):
    """Responde usando Gemini 2.5 Flash con system_instruction."""
    
    for intento in range(5):
        try:
            genai.configure(api_key=get_next_key())
            
            model = genai.GenerativeModel(
                'gemini-2.5-flash',
                system_instruction=prompt_base
            )
            
            if historial and len(historial) > 1:
                # ===== CONVERTIR HISTORIAL AL FORMATO CORRECTO =====
                historial_formateado = []
                for msg in historial:
                    if msg["role"] == "user":
                        historial_formateado.append({
                            "role": "user",
                            "parts": [{"text": msg["content"]}]
                        })
                    else:
                        historial_formateado.append({
                            "role": "model",
                            "parts": [{"text": msg["content"]}]
                        })
                # ==============================================
                
                chat = model.start_chat(history=historial_formateado)
                response = chat.send_message(pregunta)
            else:
                # Si solo hay 1 mensaje o no hay historial, usar generate_content
                response = model.generate_content(
                    f"{prompt_base}\n\nDoctor: {pregunta}\nPaciente:"
                )
            
            texto = response.text.strip()
            
            for prefix in ["Paciente:", "paciente:", "PACIENTE:", "Modelo:", "modelo:", "Respuesta:", "respuesta:"]:
                if texto.startswith(prefix):
                    texto = texto.replace(prefix, "", 1).strip()
            
            if texto:
                return texto
            return "Disculpe, doctor, no entendí bien la pregunta."
            
        except Exception as e:
            error_msg = str(e)
            print(f"Intento {intento+1} falló: {error_msg[:100]}")
            
            if "429" in error_msg or "503" in error_msg:
                time.sleep(5)
                continue
            
            if intento == 3:
                try:
                    genai.configure(api_key=get_next_key())
                    model = genai.GenerativeModel(
                        'gemini-2.5-flash',
                        system_instruction=prompt_base
                    )
                    if historial and len(historial) > 1:
                        historial_formateado = []
                        for msg in historial:
                            if msg["role"] == "user":
                                historial_formateado.append({
                                    "role": "user",
                                    "parts": [{"text": msg["content"]}]
                                })
                            else:
                                historial_formateado.append({
                                    "role": "model",
                                    "parts": [{"text": msg["content"]}]
                                })
                        chat = model.start_chat(history=historial_formateado)
                        response = chat.send_message(pregunta)
                    else:
                        response = model.generate_content(
                            f"{prompt_base}\n\nDoctor: {pregunta}\nPaciente:"
                        )
                    texto = response.text.strip()
                    if texto:
                        return texto
                except:
                    pass
            
            return "Disculpe, doctor, no entendí bien la pregunta."
    
    return "El servicio está saturado. Por favor, intenta más tarde."