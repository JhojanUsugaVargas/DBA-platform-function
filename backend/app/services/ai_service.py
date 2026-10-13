"""Artificial Intelligence and Web Search Assistance Service for DBA Platform."""
import re
import logging
from typing import Dict, Any, Optional
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
        logging.info("Gemini AI inicializado correctamente.")
    except Exception as exc:
        logging.error(f"Error configurando Gemini API: {exc}")

DDGS_AVAILABLE = True


# --- LOCAL INTELLIGENCE KNOWLEDGE BASE FOR OFFLINE DBA ASSISTANCE ---
def _local_dba_intel(texto: str, username: str) -> str:
    """Respuestas inteligentes locales de arquitectura y administración DBA."""
    t = texto.lower().strip()

    # 1. Saludos
    if re.search(r"\b(hola|buenos d[ií]as|buenas tardes|buenas noches|saludos|hey|que tal)\b", t):
        return (
            f"👋 ¡Hola, **{username}**! Soy **DataCheck AI**, tu copiloto de administración y diagnóstico de Bases de Datos.\n\n"
            "Aquí tienes algunas acciones rápidas que puedo realizar contigo:\n"
            "• ⚡ **Terminar una sesión bloqueadora:** Escribe `matar <SPID>` o `kill <PID>` (ej: `matar 55`).\n"
            "• ⏱️ **Consultar esperas:** Pregúntame sobre `PAGEIOLATCH`, `CXPACKET`, `LCK_M_X`, etc.\n"
            "• 🧹 **Mantenimiento y bloat:** Pregúntame sobre `autovacuum`, `índices` o `fragmentación`.\n"
            "• 🎫 **Crear un ticket:** Escribe `soporte Incidente: <detalle>` o simplemente `soporte`.\n\n"
            "¿Qué desafío de base de datos estamos atendiendo?"
        )

    # 2. Ayuda general
    if re.search(r"\b(ayuda|help|comandos|que puedes hacer|gu[ií]a)\b", t):
        return (
            "🤖 **Guía Rápida de DataCheck AI:**\n\n"
            "1. **Cancelación de Procesos:**\n"
            "   - `matar 42` o `kill 105`: Solicita terminar de forma segura una sesión (registra auditoría automática).\n\n"
            "2. **Tickets de Servicio:**\n"
            "   - `soporte`: Abre el selector de tipo de ticket.\n"
            "   - `soporte Incidente: Fallo en réplica`: Registra ticket de incidente prioritario.\n"
            "   - `soporte Requerimiento: Ampliación disco`: Crea solicitud técnica.\n\n"
            "3. **Consultas Técnicas:**\n"
            "   - Pregúntame sobre optimización de queries, índices faltantes, planes de ejecución y configuración de Postgres o SQL Server."
        )

    # 3. Esperas (Wait Stats)
    if "pageiolatch" in t:
        return (
            "⏱️ **Espera PAGEIOLATCH_SH / EX:**\n"
            "Indica que el motor está esperando leer datos desde el disco hacia el Buffer Pool de memoria.\n\n"
            "**Causas comunes:**\n"
            "• Falta de índices (Table Scans masivos).\n"
            "• Presión de memoria RAM (el Buffer Cache es insuficiente para la carga activa).\n"
            "• Consultas analíticas pesadas concurrentes.\n\n"
            "**Solución recomendada:** Revisa las tablas más leídas con `Estadísticas de Espera` y valida si faltan índices compuestos."
        )

    if "cxpacket" in t or "cxconsumer" in t:
        return (
            "⏱️ **Espera CXPACKET / CXCONSUMER:**\n"
            "Se produce cuando una consulta se divide en múltiples hilos en paralelo (Parallelism).\n\n"
            "**Recomendación DBA:**\n"
            "• Si `CXPACKET` es el principal cuello de botella, ajusta el umbral `Cost Threshold for Parallelism` (recomendado: 40 a 50) y verifica `MAXDOP` (máximo 8 o número de cores por socket NUMA)."
        )

    if "lck" in t or "bloqueo" in t or "lock" in t:
        return (
            "🔒 **Bloqueos y Contención (LCK_M_*):**\n"
            "Indica que una sesión está reteniendo un recurso (fila, página o tabla) y otras transacciones están en cola de espera.\n\n"
            "**Acciones recomendadas:**\n"
            "1. Ve a la opción **Análisis de Bloqueos** en el menú lateral para ver el árbol del SPID raíz.\n"
            "2. Si un proceso lleva demasiado tiempo bloqueando operaciones críticas, puedes terminarlo con `matar <SPID>`."
        )

    if "autovacuum" in t or "bloat" in t or "dead tuples" in t:
        return (
            "🧹 **PostgreSQL Bloat & Autovacuum:**\n"
            "Las tablas acumulan 'tuplas muertas' cuando se ejecutan `UPDATE` y `DELETE` frecuentes.\n\n"
            "**Optimización recomendada:**\n"
            "• Ajusta `autovacuum_vacuum_scale_factor = 0.05` en tablas de alto tráfico para que limpie con mayor frecuencia.\n"
            "• Si el bloat supera el 40%, programa un `VACUUM (ANALYZE)` o `pg_repack` en ventana de bajo impacto."
        )

    if "tempdb" in t:
        return (
            "🗂️ **TempDB / Tablespaces Temporales:**\n"
            "La contención en TempDB típicamente se debe a asignación de páginas (`PAGELATCH_UP` en PFS/GAM) o derrames de `Sort` y `Hash Join`.\n\n"
            "**Buenas prácticas:** Divide TempDB en múltiples archivos de datos de igual tamaño (ej. 4 a 8 archivos)."
        )

    # Si no es un tópico local conocido, retorna None para permitir Gemini o Web Search
    return None


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

    # 1. Inteligencia Local Especializada DBA (Prioritaria, Offline & Determinística)
    respuesta_local = _local_dba_intel(texto, username)
    if respuesta_local:
        return {
            "type": "ai",
            "message": respuesta_local,
            "source": "DataCheck Local Intel"
        }

    # 2. Gemini AI (si está configurada la API KEY)
    if GEMINI_AVAILABLE and ai_model:
        try:
            prompt = (
                f"Eres DataCheck AI, un asistente DBA senior especializado en SQL Server y PostgreSQL. "
                f"El usuario '{username}' te pregunta: '{texto}'. "
                f"Responde de forma concisa, práctica y profesional en español utilizando formato Markdown claro."
            )
            response = ai_model.generate_content(prompt)
            if response and response.text:
                respuesta = response.text.strip()
                if len(respuesta) > 3800:
                    respuesta = respuesta[:3750] + "\n\n... (respuesta truncada)"
                return {"type": "ai", "message": respuesta, "source": "Gemini AI"}
        except Exception as exc:
            logging.error(f"Gemini API error: {exc}")

    es_error = es_error_sql(texto)
    es_pregunta = es_pregunta_sql(texto)

    # 3. DuckDuckGo búsqueda web (si es error específico o consulta técnica externa)
    if DDGS_AVAILABLE and (es_error or es_pregunta):
        try:
            query = f'"{texto[:80]}" SQL Server solucion' if es_error else f'"{texto[:80]}" PostgreSQL SQL'
            with DDGS() as ddgs:
                resultados = list(ddgs.text(query, max_results=2))
            if resultados:
                contexto = "\n".join([f"• **{r['title']}**\n  {r['body'][:160]}..." for r in resultados])
                respuesta = f"🔍 **Resultados de Búsqueda Técnica:**\n\n{contexto}"
                return {"type": "ai", "message": respuesta, "source": "Búsqueda Web"}
        except Exception as exc:
            logging.warning(f"DuckDuckGo error: {exc}")

    # 4. Respuesta general de cortesía DBA (Fallback)
    return {
        "type": "ai",
        "message": (
            f"💡 **Asistente DBA DataCheck:** He recibido tu consulta: *\"{texto}\"*.\n\n"
            "Puedo asistirte en diagnóstico de rendimiento, optimización de consultas, gestión de memoria y resolución de bloqueos.\n"
            "💡 *Tip:* Para consultar métricas en tiempo real, puedes usar los botones del panel superior o indicarme qué aspecto deseas inspeccionar."
        ),
        "source": "DataCheck Local Intel"
    }
