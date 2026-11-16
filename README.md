# ECOE Digital

Plataforma para el Examen Clínico Objetivo Estructurado (ECOE): circuitos de estaciones, paciente virtual con chatbot (Gemini) y evaluación automática. Hecha con Streamlit y Supabase.

## Ejecutar localmente

```bash
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1     Linux/Mac:  source .venv/bin/activate
pip install -r requirements.txt
```

Crea un archivo `.env` en la carpeta principal (no se sube a GitHub):

```
SUPABASE_URL=https://TU-PROYECTO.supabase.co
SUPABASE_KEY=tu-clave-secreta-de-supabase
GEMINI_API_KEY=tu-clave-de-gemini
```

Y ejecuta:

```bash
streamlit run src/app.py
```

## Publicar en internet (Streamlit Community Cloud, gratis)

1. Sube este repositorio a GitHub.
2. Entra a https://share.streamlit.io con tu cuenta de GitHub → **Create app**.
3. Elige el repositorio, rama `main` y archivo principal `src/app.py`.
4. En **Advanced settings → Secrets** pega el contenido de `.streamlit/secrets.toml.example` con tus claves reales.
5. **Deploy**. La app queda en una URL `https://<nombre>.streamlit.app`.

## Evaluación dual (chatbot + médico)

- **Médico:** pestaña *Evaluar Estudiantes* con los estudiantes de su circuito y área, formulario de evaluación
  docente (ciega) generado con las competencias del caso, y vista de la evaluación del chatbot después de enviar.
- **Administrador:** ponderación chatbot/médico (pestaña *Evaluación*), comparativo por competencia, evaluación
  completa del chatbot con evidencias y pestaña *Confiabilidad IA* (ICC, kappa ponderada, acuerdo ±1 nivel, error y sesgo).
- **Base de datos:** `migraciones/002_evaluacion_dual.sql` solo agrega columnas y tablas. Se aplica sola si existe el
  secreto `DATABASE_URL`; si no, ejecútala una vez en Supabase → SQL Editor. La app rechaza cualquier migración que
  contenga DROP, DELETE, TRUNCATE, RENAME o UPDATE.
- Los rangos de nivel (Preformal 1–2 … Estratégico 9–10) están en `src/utils/evaluacion_dual.py` (`NIVELES`).

## Créditos

Laboratorio LIIACOM — Facultad de Medicina y Ciencias Biomédicas, Universidad Autónoma de Chihuahua.
