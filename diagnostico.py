# diagnostico.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

PROMPT = """
ERES UN PACIENTE REAL EN UN EXAMEN MÉDICO. NO ERES UN ROBOT. NO ERES UNA IA.
TU ÚNICA MISIÓN ES RESPONDER PREGUNTAS MÉDICAS CON LA VERDAD DE TU CASO.

IDENTIDAD DEL PACIENTE:
- Nombre: José Aguilar
- Edad: 18
- Sexo: Masculino
- Motivo: Dolor e inflamación en tobillo derecho tras caída
- Síntomas: Dolor en tobillo derecho, inflamación
- Antecedentes: Ninguno
- Medicamentos: Ninguno
- Hábitos: Ninguno
- Alergias: Ninguno

REGLAS OBLIGATORIAS:
1. Si el médico te dice "Hola", responde: "Buenos días, doctor. Vine porque tengo dolor en el tobillo derecho."
2. Si te preguntan algo médico, responde con la información de tu caso.
3. Si te preguntan algo no médico, responde: "Disculpe, doctor, no entendí bien la pregunta."
4. No uses términos médicos.
5. Respuesta máximo 2 oraciones.
"""

print("=" * 60)
print("PRUEBA 1: Enviar 'Hola' SIN historial (generate_content)")
print("=" * 60)

try:
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=PROMPT)
    response = model.generate_content(f"{PROMPT}\n\nDoctor: Hola\nPaciente:")
    print(f"✅ RESPUESTA: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {str(e)[:300]}")

print("\n" + "=" * 60)
print("PRUEBA 2: Enviar 'Hola' CON historial formateado correctamente")
print("=" * 60)

try:
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=PROMPT)
    
    # AHORA SÍ CON EL FORMATO CORRECTO
    historial = [
        {"role": "user", "parts": [{"text": "Hola"}]}
    ]
    
    chat = model.start_chat(history=historial)
    response = chat.send_message("Hola")
    
    print(f"✅ RESPUESTA: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {str(e)[:300]}")

print("\n" + "=" * 60)
print("PRUEBA 3: Enviar '¿Cuáles son tus síntomas?' CON historial formateado")
print("=" * 60)

try:
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=PROMPT)
    
    historial = [
        {"role": "user", "parts": [{"text": "Hola"}]},
        {"role": "model", "parts": [{"text": "Buenos días, doctor. Vine porque tengo dolor en el tobillo derecho."}]},
        {"role": "user", "parts": [{"text": "¿Cuáles son tus síntomas?"}]}
    ]
    
    chat = model.start_chat(history=historial)
    response = chat.send_message("¿Cuáles son tus síntomas?")
    
    print(f"✅ RESPUESTA: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {str(e)[:300]}")

print("\n" + "=" * 60)
print("PRUEBA 4: Enviar '¿Eres un robot?' CON historial formateado")
print("=" * 60)

try:
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=PROMPT)
    
    historial = [
        {"role": "user", "parts": [{"text": "Hola"}]},
        {"role": "model", "parts": [{"text": "Buenos días, doctor. Vine porque tengo dolor en el tobillo derecho."}]},
        {"role": "user", "parts": [{"text": "¿Eres un robot?"}]}
    ]
    
    chat = model.start_chat(history=historial)
    response = chat.send_message("¿Eres un robot?")
    
    print(f"✅ RESPUESTA: {response.text}")
except Exception as e:
    print(f"❌ ERROR: {str(e)[:300]}")