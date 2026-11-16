import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Credenciales no encontradas")
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Conexión a Supabase establecida")
    
    # Intentar insertar un registro manual
    try:
        data = {
            "matricula": "380264",
            "pantalla_actual": "inicio",
            "estatus": "activo",
            "hora_inicio_sesion": datetime.now().isoformat(),
            "hora_ultima_actividad": datetime.now().isoformat()
        }
        
        response = supabase.table("actividad_estudiante").insert(data).execute()
        print("✅ Registro insertado correctamente")
        print(f"📊 Datos: {response.data}")
        
    except Exception as e:
        print(f"❌ Error al insertar: {e}")