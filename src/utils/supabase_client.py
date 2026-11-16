# utils/supabase_client.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Verificar que las credenciales existen
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Credenciales de Supabase no encontradas en .env")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Conexión a Supabase establecida")
    