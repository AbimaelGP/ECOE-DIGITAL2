# test_supabase.py
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Probar consulta
response = supabase.table("usuarios").select("*").execute()
print(f"Total usuarios: {len(response.data)}")
for user in response.data:
    print(f" - {user['identificador']}: {user['nombre']} ({user['tipo_usuario']})")

# Verificar que la tabla actividad_estudiante existe
print("\n--- Verificando tabla actividad_estudiante ---")
try:
    response = supabase.table("actividad_estudiante").select("*").limit(1).execute()
    print("Tabla actividad_estudiante creada correctamente")
except Exception as e:
    print(f"Error: {e}")