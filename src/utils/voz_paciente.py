# utils/voz_paciente.py
import pyttsx3
import os
import tempfile

def _obtener_voz(engine, sexo):
    """Selecciona la mejor voz disponible (Sabina en español)."""
    voices = engine.getProperty('voices')
    
    # Buscar voces en español
    for voice in voices:
        lang = str(voice.languages).lower()
        name = voice.name.lower()
        
        if 'es-mx' in lang or 'es-es' in lang or 'spanish' in lang:
            # Si es femenino, usar Sabina
            if sexo.lower() == 'femenino':
                if any(x in name for x in ['sabina', 'dalia', 'elvira', 'female', 'mujer']):
                    return voice.id
            else:
                # Si es masculino, buscar Raul o alguna masculina en español
                if any(x in name for x in ['raul', 'jorge', 'alvaro', 'male', 'hombre']):
                    return voice.id
    
    # Si no encontró ninguna del sexo específico, usar la primera en español
    for voice in voices:
        lang = str(voice.languages).lower()
        if 'es-mx' in lang or 'es-es' in lang or 'spanish' in lang:
            return voice.id
    
    # Si no hay en español, usar la primera disponible
    if voices:
        return voices[0].id
    return None

def generar_audio_paciente(texto, info_caso):
    """Genera audio WAV temporal con pyttsx3 (Sabina en español)."""
    try:
        engine = pyttsx3.init()
        
        edad = info_caso.get('edad', 30) if info_caso else 30
        sexo = info_caso.get('sexo', 'Masculino') if info_caso else 'Masculino'
        
        if isinstance(edad, str):
            try:
                edad = int(edad)
            except:
                edad = 30
        
        # Seleccionar voz (Sabina)
        voice_id = _obtener_voz(engine, sexo)
        if voice_id:
            engine.setProperty('voice', voice_id)
        
        # Ajustar velocidad según edad
        if edad >= 60:
            engine.setProperty('rate', 120)  # Más lento (anciano)
        elif edad < 18:
            engine.setProperty('rate', 180)  # Más rápido (niño)
        else:
            engine.setProperty('rate', 150)  # Normal (adulto)
        
        # Guardar en archivo temporal WAV
        temp_file = os.path.join(tempfile.gettempdir(), f"paciente_{os.getpid()}_{id(texto)}.wav")
        
        engine.save_to_file(texto, temp_file)
        engine.runAndWait()
        
        # Leer el archivo generado
        with open(temp_file, 'rb') as f:
            audio_bytes = f.read()
        
        # Limpiar el archivo temporal
        try:
            os.remove(temp_file)
        except:
            pass
        
        return audio_bytes
        
    except Exception as e:
        print(f"❌ Error con pyttsx3: {e}")
        return None