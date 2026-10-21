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
                f"Un usuario de la plataforma te pregunta: '{texto}'. "
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


def diagnose_sql_query(
    query_text: str,
    engine: str = "sqlserver",
    execution_count: int = 1,
    cpu_total_ms: float = 0.0,
    logical_reads: int = 0
) -> Dict[str, Any]:
    """Diagnoses a slow/heavy query and suggests index creation and query rewrites."""
    if not query_text or not query_text.strip():
        return {
            "success": False,
            "message": "No se proporcionó texto de consulta SQL para diagnosticar.",
            "source": "Local"
        }

    q_clean = query_text.strip()
    is_pg = "postgres" in engine.lower()

    # 1. Gemini AI Analysis (if configured)
    if GEMINI_AVAILABLE and ai_model:
        try:
            prompt = f"""Eres un Arquitecto DBA Senior especializado en optimización y afinamiento de consultas (Query Tuning) para {engine.upper()}.
Analiza la siguiente consulta identificada en el Top Queries de la plataforma:
- Motor: {engine.upper()}
- Total Ejecuciones: {execution_count}
- CPU Total consumido: {cpu_total_ms} ms
- Lecturas Lógicas: {logical_reads}

Consulta SQL:
```sql
{q_clean}
```

Proporciona una respuesta en Markdown estructurada con:
1. **🔍 Diagnóstico del Cuello de Botella**: Identifica anti-patrones (ej. SELECT *, comodines '%' al inicio, funciones en cláusula WHERE, conversiones implícitas, falta de filtrado o joins cartesianos).
2. **⚡ Índice Sugerido (CREATE INDEX)**: Sentencia DDL completa lista para ejecutar con columnas de búsqueda y columnas INCLUDE para un index seek con cobertura total.
3. **🛠️ Reescritura SQL Optimizada**: La consulta reescrita de forma óptima.
4. **📊 Impacto Estimado**: Estimación de reducción en lecturas de disco y CPU.
Sé muy conciso, directo y técnico."""
            res = ai_model.generate_content(prompt)
            if res and res.text:
                return {
                    "success": True,
                    "diagnosis": res.text.strip(),
                    "query_text": q_clean,
                    "engine": engine,
                    "source": "Gemini 2.0 Flash"
                }
        except Exception as exc:
            logging.warning("Error llamando a Gemini para diagnóstico SQL: %s", exc)

    # 2. Local Static Heuristic DBA Diagnostic Engine (Fallback)
    anti_patterns = []
    suggested_indexes = []
    rewritten_sql = q_clean

    upper_q = q_clean.upper()
    if "SELECT *" in upper_q:
        anti_patterns.append("• **Proyección completa (SELECT *):** Fuerza la lectura de todas las columnas de la página de datos, impidiendo index seeks cubiertos y consumiendo memoria innecesaria en el Buffer Pool.")
    if "LIKE '%" in upper_q:
        anti_patterns.append("• **Comodín inicial (LIKE '%...'):** Hace que el predicado sea no-SARGable, forzando un escaneo de índice completo (Index Scan) o de tabla (Table Scan).")
    if "NOT IN (SELECT" in upper_q:
        anti_patterns.append("• **Subconsulta NOT IN:** Si existen valores nulos en el conjunto resultante, la consulta se evalúa secuencialmente. Se recomienda reemplazar por `NOT EXISTS`.")

    # Match possible table name from FROM clause
    table_match = re.search(r"FROM\s+([A-Za-z0-9_.]+)", q_clean, re.I)
    table_name = table_match.group(1) if table_match else "tu_tabla"

    # Match WHERE columns
    where_match = re.search(r"WHERE\s+([A-Za-z0-9_.]+)", q_clean, re.I)
    where_col = where_match.group(1) if where_match else "columna_filtro"

    if is_pg:
        index_ddl = f"CREATE INDEX idx_{table_name.replace('.', '_')}_{where_col} ON {table_name} ({where_col});"
    else:
        index_ddl = f"CREATE NONCLUSTERED INDEX IX_{table_name.replace('.', '_')}_{where_col} ON {table_name} ({where_col}) WITH (FILLFACTOR = 90, ONLINE = ON);"

    if not anti_patterns:
        anti_patterns.append("• **Consumo acumulado:** La consulta presenta alto uso de lecturas o CPU; verificar estadísticas desactualizadas o falta de índice de cobertura.")

    diagnosis_text = f"""### 🔍 Diagnóstico Técnico de Copiloto DBA ({engine.upper()})

**Anti-patrones y Puntos de Atención Detectados:**
{chr(10).join(anti_patterns)}

---

### ⚡ Índice Recomendado (DDL Sugerido):
```sql
-- Ejecutar en ventana de bajo impacto
{index_ddl}
```

---

### 💡 Buenas Prácticas de Reescritura:
1. Reemplaza `SELECT *` por las columnas exactas requeridas por la aplicación.
2. Asegúrate de que los tipos de datos en la cláusula `WHERE` coincidan exactamente con la definición de la tabla para evitar *Implicit Conversions*.
3. Si la tabla es grande, incluye filtros con fechas o claves particionadas para permitir *Partition Elimination*."""

    return {
        "success": True,
        "diagnosis": diagnosis_text,
        "suggested_sql": rewritten_sql,
        "suggested_index": index_ddl,
        "query_text": q_clean,
        "engine": engine,
        "source": "DataCheck Local Intel Engine"
    }


def suggest_incident_solution(
    title: str,
    description: str,
    module: str = "General",
    priority: str = "Media",
    ticket_type: str = "Incidente"
) -> Dict[str, Any]:
    """Generates an automated DBA technical resolution suggestion for a ticket."""
    clean_title = (title or "").strip()
    clean_desc = (description or "").strip()

    # 1. Gemini AI Generation
    if GEMINI_AVAILABLE and ai_model:
        try:
            prompt = f"""Eres un Ingeniero DBA Senior especializado en resolución de incidentes de misión crítica en SQL Server y PostgreSQL.
Analiza el siguiente ticket de soporte reportado en la plataforma:
- Tipo: {ticket_type}
- Módulo afectado: {module}
- Prioridad: {priority}
- Título: {clean_title}
- Descripción: {clean_desc}

Genera una recomendación de resolución técnica en Markdown con la siguiente estructura:
1. **🎯 Causa Raíz Probable**: Qué fenómeno técnico (bloqueos, bloat, autovacuum, desbordamiento tempdb, espacio en disco, estadísticas) está originando el problema.
2. **🛠️ Plan de Acción Paso a Paso**: Comandos SQL específicos de diagnóstico o remediación inmediata.
3. **⚠️ Consideraciones de Impacto / Rollback**: Precauciones antes de ejecutar en producción.
4. **📝 Borrador de Notas para el Ticket**: Un resumen conciso listo para ser copiado al campo de notas del ticket cuando se resuelva."""
            res = ai_model.generate_content(prompt)
            if res and res.text:
                return {
                    "success": True,
                    "suggestion": res.text.strip(),
                    "source": "Gemini 2.0 Flash"
                }
        except Exception as exc:
            logging.warning("Error llamando a Gemini para sugerencia de ticket: %s", exc)

    # 2. Local DBA Incident Knowledge Matrix
    mod_lower = module.lower()
    desc_lower = (clean_title + " " + clean_desc).lower()

    if "bloqueo" in mod_lower or "lock" in desc_lower or "deadlock" in desc_lower:
        steps = (
            "1. Abre la sección **Análisis de Bloqueos** para identificar el `SPID` raíz.\n"
            "2. Valida la transacción abierta más antigua (`DBCC OPENTRAN` o `pg_stat_activity`).\n"
            "3. Si es un proceso colgado sin actividad transaccional, ejecuta la terminación controlada con `matar <SPID>` desde el chat.\n"
            "4. Revisa los niveles de aislamiento y solicita al equipo de desarrollo reducir el tiempo de transacción."
        )
        cause = "Contención de recursos en filas o páginas compartidas debido a transacciones abiertas no finalizadas (open transactions)."
        draft = "Se identificó y mitigó contención de bloqueos en la base de datos. Se finalizó la sesión bloqueadora y se restableció el flujo normal de transacciones."
    elif "tempdb" in mod_lower or "temp" in desc_lower:
        steps = (
            "1. Consulta el uso de archivos en **Uso de TempDB** para validar si el espacio está tomado por el Version Store o tablas temporales (#temp).\n"
            "2. Verifica si hay consultas con sorts y hash joins masivos desbordando a disco.\n"
            "3. Configura múltiples archivos de datos (.mdf / .ndf) de igual tamaño acordes al número de núcleos lógicos."
        )
        cause = "Alto consumo de TempDB generado por derrames de memoria (Spill to Workfile) o acumulación de instantáneas en Version Store (RCSI/Snapshot)."
        draft = "Se verificó la contención en TempDB y se liberó espacio en el Version Store. Se normalizó la utilización de tablas temporales."
    elif "disco" in mod_lower or "almacenamiento" in mod_lower or "espacio" in desc_lower:
        steps = (
            "1. Inspecciona el tamaño de los archivos `.ldf` o transaccionales WAL.\n"
            "2. Realiza un respaldo del Transaction Log (`BACKUP LOG ... TO DISK`) para truncar el log virtual (VLF).\n"
            "3. En PostgreSQL, programa `VACUUM FULL` o `pg_repack` durante ventana de mantenimiento para recuperar espacio libre del sistema operativo."
        )
        cause = "Crecimiento desmedido de archivos de datos o bitácora de transacciones debido a modelos de recuperación FULL sin frecuencia de respaldo adecuada."
        draft = "Se ejecutó respaldo de bitácora y optimización de almacenamiento, liberando espacio disponible en el disco afectado."
    else:
        steps = (
            "1. Revisa el **Monitor de Salud** y la gráfica de CPU/Throughput en la pestaña Telemetría 24h.\n"
            "2. Valida el Top 10 de Consultas Lentas para aislar queries con picos de recursos.\n"
            "3. Confirma la conectividad y latencia de red contra el host de base de datos.\n"
            "4. Registra los cambios aplicados y valida que los tiempos de respuesta del aplicativo se encuentren dentro del SLA."
        )
        cause = "Degradación general de rendimiento o solicitud de soporte sobre la instancia de base de datos."
        draft = "Se analizó el comportamiento de la instancia en el panel de telemetría y se aplicaron las validaciones requeridas según la política de servicio."

    suggestion_text = f"""### 🎯 Recomendación Técnica Automatizada (Copiloto DBA)

**Diagnóstico Preliminar:**
{cause}

---

**🛠️ Plan de Acción Recomendado:**
{steps}

---

**📝 Texto Sugerido para Notas del Agente:**
> *"{draft}"*"""

    return {
        "success": True,
        "suggestion": suggestion_text,
        "suggested_notes": draft,
        "source": "DataCheck Incident Intelligence Matrix"
    }

