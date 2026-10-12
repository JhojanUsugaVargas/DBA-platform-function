"""Artificial Intelligence and Web Search Assistance Service."""
import re
import logging
from typing import Dict, Any
from duckduckgo_search import DDGS
import google.generativeai as genai
from app.core.config import settings

# Initialize Gemini
GEMINI_AVAILABLE = False
ai_model = None

if settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        ai_model = genai.GenerativeModel("gemini-2.0-flash")
        GEMINI_AVAILABLE = True
    except Exception as exc:
        logging.error(f"Error configurando Gemini API: {exc}")

DDGS_AVAILABLE = True


def es_error_sql(texto: str) -> bool:
    """Detecta si el mensaje describe un error o excepción de SQL."""
    return bool(re.search(r"error|msg\s+\d+|invalid|cannot|timeout|deadlock|provider|\.database\.", texto, re.I))


def es_pregunta_sql(texto: str) -> bool:
    """Detecta si el mensaje es una pregunta o consulta técnica sobre bases de datos."""
    return bool(re.search(r"\?|cómo|explica|ejemplo|diferencia|join|group by|where|select|create|usuario|primary key|oracle|tamaño|ayuda|dime|como", texto, re.I))


def get_ai_response(texto: str, username: str) -> Dict[str, Any]:
    """Procesa consultas técnicas o conversacionales del chat."""
    if not texto or not isinstance(texto, str):
        return {"type": "info", "message": "✍️ Escribe un error SQL o una pregunta sobre bases de datos."}

    es_error = es_error_sql(texto)
    es_pregunta = es_pregunta_sql(texto)

    # 1. Gemini AI
    if GEMINI_AVAILABLE and ai_model:
        try:
            prompt = (
                f"El usuario {username} es un DBA usando la plataforma DataCheck. "
                f"Responde amigablemente o resuelve su error técnico de bases de datos "
                f"de forma concisa y en texto plano (Markdown básico permitido): {texto}"
            )
            response = ai_model.generate_content(prompt)
            if response and response.text:
                respuesta = response.text.strip()
                if len(respuesta) > 3800:
                    respuesta = respuesta[:3750] + "\n\n... (respuesta truncada)"
                return {"type": "ai", "message": respuesta, "source": "Gemini AI"}
        except Exception as exc:
            logging.error(f"Gemini API error: {exc}")

    # 2. DuckDuckGo fallback
    if DDGS_AVAILABLE and (es_error or es_pregunta):
        try:
            query = f'"{texto[:80]}" SQL Server solución' if es_error else f'"{texto}" SQL tutorial'
            with DDGS() as ddgs:
                resultados = list(ddgs.text(query, max_results=2))
            if resultados:
                contexto = "\n".join([f"{i+1}. {r['title']}\n{r['body'][:140]}..." for i, r in enumerate(resultados)])
                respuesta = f"Resultados para: {query}\n\n{contexto}"
                return {"type": "ai", "message": respuesta, "source": "Búsqueda Web"}
        except Exception as exc:
            logging.error(f"DuckDuckGo error: {exc}")

    if not GEMINI_AVAILABLE:
        return {
            "type": "info",
            "message": "ℹ️ Gemini AI no está configurado (falta GEMINI_API_KEY en variables de entorno)."
        }

    return {"type": "info", "message": "No se pudo obtener respuesta en este momento."}
