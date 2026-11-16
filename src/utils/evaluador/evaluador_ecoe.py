# -*- coding: utf-8 -*-
# evaluador_ecoe.py - VERSIÓN UNIFICADA PARA CLAVE DE PAGO
# Modificado: una sola pasada, sin modo respaldo, errores notificados.

import json
import re
import os
import time
import logging
import requests

from . import config

logger = logging.getLogger("ECOE.Evaluador")

class EvaluadorECOE:

    def __init__(self):
        self.api_key = config.get_api_key()
        self.model_name = config.get_model()
        self._inicializar_cliente()

    def _inicializar_cliente(self):
        """Inicializa el cliente con la API key de pago"""
        print("🔌 Conectando con Gemini API (clave de pago)...")
        
        if not self.api_key or not self.api_key.startswith("AIzaSy"):
            raise RuntimeError(
                "❌ Clave de API inválida.\n"
                "La clave debe comenzar con 'AIzaSy'.\n"
                "Verifica tu clave en config.py"
            )

        for nombre_modelo in config.GEMINI_MODELS:
            try:
                print(f"   🔄 Probando modelo: {nombre_modelo}")
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{nombre_modelo}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                }
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": "Di 'OK'"}
                            ]
                        }
                    ]
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    self.model_name = nombre_modelo
                    logger.info("✅ Conectado con modelo '%s'", nombre_modelo)
                    print(f"✅ ¡CONECTADO! Modelo: {nombre_modelo}")
                    return
                elif response.status_code == 401:
                    print(f"   ❌ Autenticación fallida para {nombre_modelo} (401)")
                    print("   Verifica que la API key sea válida y tenga permisos")
                    raise RuntimeError("❌ Error de autenticación. Verifica tu API key.")
                elif response.status_code == 404:
                    print(f"   ❌ Modelo {nombre_modelo} no disponible (404)")
                else:
                    print(f"   ❌ Error {response.status_code}: {response.text[:60]}")
                    
            except requests.exceptions.Timeout:
                print(f"   ❌ Timeout con {nombre_modelo}")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:60]}")

        raise RuntimeError(
            "❌ No se pudo conectar con Gemini.\n"
            "1. Verifica que tu API key sea válida\n"
            "2. Asegúrate de tener instalado: pip install requests\n"
            "3. Verifica que la API esté habilitada en Google Cloud Console"
        )

    def _llamar_api(self, prompt):
        """Llama a la API con reintentos"""
        for intento in range(1, config.MAX_RETRIES + 1):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                }
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ]
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and result['candidates']:
                        texto = result['candidates'][0]['content']['parts'][0]['text']
                        return texto
                    else:
                        raise Exception("Respuesta sin candidates")
                elif response.status_code == 401:
                    raise Exception("Error de autenticación. Verifica tu API key.")
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:100]}")
                    
            except Exception as e:
                logger.warning("Intento %d/%d falló: %s", intento, config.MAX_RETRIES, str(e)[:100])
                
                if intento < config.MAX_RETRIES:
                    time.sleep(config.RETRY_DELAY_SECONDS * intento)
                else:
                    raise RuntimeError(f"API no disponible: {str(e)[:100]}")
        
        raise RuntimeError("No se pudo obtener respuesta después de múltiples intentos")

    def leer_archivo(self, ruta):
        """Lee txt, pdf o docx y devuelve su contenido como texto."""
        if not os.path.exists(ruta):
            logger.error("Archivo no encontrado: %s", ruta)
            return None

        extension = ruta.rsplit(".", 1)[-1].lower()
        logger.info("Leyendo archivo '%s'", os.path.basename(ruta))

        try:
            if extension in ("txt", "text", "md"):
                with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            elif extension == "pdf":
                try:
                    import PyPDF2
                    with open(ruta, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        return "\n".join(page.extract_text() or "" for page in reader.pages)
                except ImportError:
                    logger.error("PyPDF2 no instalado. Ejecuta: pip install PyPDF2")
                    return None
            elif extension in ("docx", "doc"):
                try:
                    from docx import Document
                    doc = Document(ruta)
                    texto = "\n".join(p.text for p in doc.paragraphs)
                    return texto if texto.strip() else self._leer_texto_fallback(ruta)
                except ImportError:
                    logger.error("python-docx no instalado. Ejecuta: pip install python-docx")
                    return None
                except:
                    return self._leer_texto_fallback(ruta)
            else:
                with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
        except Exception as e:
            logger.error("Error leyendo %s: %s", ruta, e)
            return None

    def _leer_texto_fallback(self, ruta):
        try:
            with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except:
            try:
                with open(ruta, "rb") as f:
                    return f.read().decode("utf-8", errors="ignore")
            except:
                return None

    def extraer_texto_archivo(self, ruta):
        return self.leer_archivo(ruta)

    def procesar_rubrica(self, contenido):
        """Procesa la rúbrica y la convierte a JSON estructurado EN UNA SOLA LLAMADA."""
        logger.info("Procesando rúbrica (%d chars)", len(contenido))

        schema = '''
{
  "categorias": [
    {
      "nombre": "string",
      "criterios": [
        {
          "nombre": "string",
          "descripcion": "string",
          "maxima": 10
        }
      ]
    }
  ]
}
'''

        prompt = (
            "Eres un experto en evaluación médica clínica (ECOE/OSCE).\n"
            "Lee la siguiente rúbrica y extrae TODOS los criterios de evaluación.\n"
            "Devuelve SOLO un JSON con exactamente este schema:\n"
            + schema +
            "\n\nREGLAS:\n"
            "- No incluyas texto adicional, solo el JSON.\n"
            "- 'maxima' debe ser un número entero mayor que 0.\n"
            "- Si no hay puntuación explícita, asigna 10 por defecto.\n"
            "- Agrupa los criterios en categorías lógicas si no están explícitas.\n\n"
            "RÚBRICA:\n" + contenido[:config.MAX_CHARS_RUBRICA]
        )

        try:
            texto_json = self._llamar_api(prompt)
            rubrica = json.loads(self._limpiar_json(texto_json))
            self._validar_rubrica(rubrica)
            logger.info("Rúbrica procesada: %d categorías", len(rubrica.get("categorias", [])))
            return rubrica
        except Exception as e:
            logger.error("Error procesando rúbrica: %s", e)
            raise RuntimeError(f"No se pudo procesar la rúbrica: {e}") from e

    def _validar_rubrica(self, rubrica):
        if "categorias" not in rubrica or not rubrica["categorias"]:
            raise ValueError("Rúbrica sin categorías")
        for cat in rubrica["categorias"]:
            for c in cat.get("criterios", []):
                if not isinstance(c.get("maxima"), (int, float)) or c["maxima"] <= 0:
                    raise ValueError("Criterio '{}' con máxima inválida".format(c.get("nombre")))

    def evaluar_conversacion(self, conversacion, rubrica):
        """Evalúa la conversación EN UNA SOLA PASADA."""
        logger.info("Iniciando evaluación en una sola pasada")
        criterios = self._extraer_criterios_planos(rubrica)

        criterios_json = json.dumps(criterios, indent=2, ensure_ascii=False)
        schema_eval = '''
{
  "evaluacion": [
    {
      "criterio": "nombre exacto del criterio",
      "categoria": "nombre de la categoría",
      "puntuacion": 0,
      "maxima": 0,
      "nivel": "DEFICIENTE | REGULAR | BUENO | EXCELENTE",
      "fortalezas": "lo que hizo bien",
      "debilidades": "lo que falló",
      "justificacion": "justificación con cita textual"
    }
  ],
  "total": 0,
  "maximo_posible": 0,
  "porcentaje": 0,
  "nivel_global": "DEFICIENTE | REGULAR | BUENO | EXCELENTE",
  "fortalezas_globales": "resumen",
  "areas_mejora": "resumen",
  "observaciones": "comentario final"
}
'''

        prompt = (
            "Eres un evaluador médico ESTRICTO y JUSTO.\n"
            "Evalúa la siguiente conversación según los criterios proporcionados.\n\n"
            "ESCALA OBLIGATORIA:\n"
            "  0-39% → DEFICIENTE\n"
            "  40-59% → REGULAR\n"
            "  60-79% → BUENO\n"
            "  80-100% → EXCELENTE\n\n"
            "CRITERIOS (con puntuación máxima):\n" + criterios_json + "\n\n"
            "CONVERSACIÓN:\n" + conversacion[:config.MAX_CHARS_CONV] + "\n\n"
            "REGLAS:\n"
            "- Devuelve SOLO el JSON con el schema de abajo.\n"
            "- Cada criterio debe aparecer UNA vez.\n"
            "- Asigna puntuaciones DIFERENCIADAS y justificadas.\n"
            "- No inventes información que no esté en la conversación.\n"
            "- Si no puedes evaluar algo, indícalo en la justificación.\n\n"
            "SCHEMA:\n" + schema_eval
        )

        try:
            texto_json = self._llamar_api(prompt)
            evaluacion = json.loads(self._limpiar_json(texto_json))
            evaluacion = self._post_procesar_evaluacion(evaluacion, criterios)
            logger.info("Evaluación completada: %d/%d", evaluacion["total"], evaluacion["maximo_posible"])
            return evaluacion
        except Exception as e:
            logger.error("Error en evaluación: %s", e)
            raise RuntimeError(f"No se pudo evaluar la conversación: {e}") from e

    def _post_procesar_evaluacion(self, evaluacion, criterios):
        total = 0
        maximo = 0

        for item in evaluacion.get("evaluacion", []):
            punt = item.get("puntuacion", 0)
            max_val = item.get("maxima", 10)
            item["puntuacion"] = max(0, min(punt, max_val))
            item["maxima"] = max_val
            pct = (item["puntuacion"] / float(max_val)) * 100 if max_val > 0 else 0
            item["nivel"] = self._nivel_desempeno(pct)
            total += item["puntuacion"]
            maximo += max_val

        evaluacion["total"] = total
        evaluacion["maximo_posible"] = maximo
        evaluacion["porcentaje"] = round((total / float(maximo)) * 100, 1) if maximo > 0 else 0
        evaluacion["nivel_global"] = self._nivel_desempeno(evaluacion["porcentaje"])
        evaluacion.setdefault("fortalezas_globales", "")
        evaluacion.setdefault("areas_mejora", "")
        evaluacion.setdefault("observaciones", "Sin observaciones adicionales")
        return evaluacion

    def _extraer_criterios_planos(self, rubrica):
        resultado = []
        for cat in rubrica.get("categorias", []):
            for c in cat.get("criterios", []):
                resultado.append({
                    "nombre": c["nombre"],
                    "descripcion": c.get("descripcion", ""),
                    "maxima": c["maxima"],
                    "categoria": cat["nombre"],
                })
        return resultado

    @staticmethod
    def _nivel_desempeno(porcentaje):
        if porcentaje >= 80:
            return "EXCELENTE"
        elif porcentaje >= 60:
            return "BUENO"
        elif porcentaje >= 40:
            return "REGULAR"
        return "DEFICIENTE"

    @staticmethod
    def _limpiar_json(texto):
        texto = re.sub(r"```(?:json)?\s*", "", texto)
        texto = re.sub(r"```\s*", "", texto)
        inicio = texto.find("{")
        fin = texto.rfind("}") + 1
        if inicio != -1 and fin > 0:
            return texto[inicio:fin]
        return texto.strip()

    def generar_informe(self, evaluacion):
        SEP = "═" * 65
        sep = "─" * 65

        lineas = [
            SEP,
            "  INFORME DE EVALUACIÓN ECOE / OSCE",
            SEP,
            "",
            "  Puntuación Total : {}/{}".format(evaluacion["total"], evaluacion["maximo_posible"]),
            "  Porcentaje       : {}%".format(evaluacion["porcentaje"]),
            "  Nivel Global     : {}".format(evaluacion.get("nivel_global", "")),
            "",
            sep,
            "  FORTALEZAS GLOBALES",
            sep,
            "  {}".format(evaluacion.get("fortalezas_globales", "—")),
            "",
            sep,
            "  ÁREAS DE MEJORA",
            sep,
            "  {}".format(evaluacion.get("areas_mejora", "—")),
            "",
            sep,
            "  DETALLE POR CRITERIO",
            sep,
        ]

        for item in evaluacion.get("evaluacion", []):
            punt = item["puntuacion"]
            max_v = item["maxima"]
            pct = round((punt / float(max_v)) * 100, 1) if max_v > 0 else 0
            barra = ("█" * int(pct / 10)).ljust(10, "░")

            lineas += [
                "",
                "  [{nivel}] {criterio}  ({categoria})".format(
                    nivel=item.get("nivel", "").center(10),
                    criterio=item["criterio"],
                    categoria=item.get("categoria", "")
                ),
                "  [{barra}] {punt}/{max} ({pct}%)".format(
                    barra=barra, punt=punt, max=max_v, pct=pct
                ),
                "  ✔ {}".format(item.get("fortalezas", "—")),
                "  ✘ {}".format(item.get("debilidades", "—")),
                "  ➜ {}".format(item.get("justificacion", "—")),
            ]

        lineas += [
            "",
            sep,
            "  OBSERVACIONES FINALES",
            sep,
            "  {}".format(evaluacion.get("observaciones", "—")),
            "",
            SEP,
        ]

        return "\n".join(lineas)