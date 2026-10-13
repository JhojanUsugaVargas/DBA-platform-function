"""Database Maintenance & Statistics Health Monitor (Multi-Engine).

Supports:
- Microsoft SQL Server: Outdated statistics detection (modifications counter, stale percentage, days since last stats update, critical rebuild alerts).
- PostgreSQL: Autovacuum progress monitoring and candidate table maintenance backlog.
"""
import logging
from typing import List, Dict, Any

_SQLSERVER_STATS_QUERY = """
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

SELECT TOP 50
    Esquema = s.name,
    Tabla = t.name,
    Estadistica = st.name,
    Filas_Totales = ISNULL(sp.rows, 0),
    Filas_Modificadas = ISNULL(sp.modification_counter, 0),
    Pct_Modificado = CASE WHEN ISNULL(sp.rows, 0) > 0
                          THEN CAST(ROUND((sp.modification_counter * 100.0) / sp.rows, 1) AS NUMERIC(5, 1))
                          ELSE 0 END,
    Ultima_Actualizacion = COALESCE(CONVERT(VARCHAR(19), sp.last_updated, 120), 'NUNCA'),
    Dias_Sin_Actualizar = ISNULL(DATEDIFF(DAY, sp.last_updated, GETDATE()), 999),
    Diagnostico = CASE
        WHEN sp.last_updated IS NULL THEN '⚠️ CRÍTICO: Nunca actualizada'
        WHEN (sp.rows > 1000 AND (sp.modification_counter * 100.0) / sp.rows > 20) OR DATEDIFF(DAY, sp.last_updated, GETDATE()) > 30 THEN '⚠️ CRÍTICO: Recompilar Stats'
        WHEN (sp.rows > 1000 AND (sp.modification_counter * 100.0) / sp.rows > 10) OR DATEDIFF(DAY, sp.last_updated, GETDATE()) > 14 THEN '⚡ Advertencia: Desactualizada'
        ELSE 'Al día'
    END
FROM sys.stats st
JOIN sys.tables t ON st.object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
CROSS APPLY sys.dm_db_stats_properties(st.object_id, st.stats_id) sp
WHERE t.is_ms_shipped = 0
ORDER BY sp.modification_counter DESC, Dias_Sin_Actualizar DESC;
"""

# Version-agnostic for PostgreSQL 12-17
_POSTGRES_AUTOVACUUM_PROGRESS_QUERY = """
SELECT
    p.pid,
    p.datname AS database_name,
    c.relname AS table_name,
    p.phase,
    p.heap_blks_total,
    p.heap_blks_scanned,
    p.heap_blks_vacuumed,
    p.index_vacuum_count
FROM pg_stat_progress_vacuum p
LEFT JOIN pg_class c ON c.oid = p.relid;
"""

_POSTGRES_AUTOVACUUM_CANDIDATES_QUERY = """
SELECT
    schemaname AS schema_name,
    relname AS table_name,
    n_dead_tup AS dead_tuples,
    n_live_tup AS live_tuples,
    autovacuum_count,
    vacuum_count,
    COALESCE(TO_CHAR(last_autovacuum, 'YYYY-MM-DD HH24:MI:SS'), 'Nunca') AS last_autovacuum,
    ROUND(n_dead_tup * 100.0 / GREATEST(n_live_tup, 1), 1) AS dead_ratio_pct
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 50;
"""


def query_maintenance_stats(cursor: Any, engine: str) -> List[Dict[str, Any]]:
    """Capture statistics maintenance health for SQL Server or Autovacuum state for PostgreSQL."""
    results: List[Dict[str, Any]] = []

    try:
        if engine == "postgres":
            # 1. Active vacuum tasks (tolerant to PG versions)
            try:
                cursor.execute(_POSTGRES_AUTOVACUUM_PROGRESS_QUERY)
                active_rows = cursor.fetchall()
                for r in active_rows:
                    results.append({
                        "Motor": "PostgreSQL",
                        "Estado": "⚡ EN EJECUCIÓN",
                        "Tabla": f"{r[1]}.{r[2]}" if r[2] else "N/A",
                        "Fase": str(r[3] or "scanning"),
                        "Progreso_Bloques": f"{r[5]}/{r[4]}",
                        "Detalle": f"PID: {r[0]} - Vacuum activo en curso",
                    })
            except Exception as prog_exc:
                logging.debug("pg_stat_progress_vacuum omitido o no soportado: %s", prog_exc)

            # 2. Table maintenance backlog
            cursor.execute(_POSTGRES_AUTOVACUUM_CANDIDATES_QUERY)
            candidates = cursor.fetchall()
            for c in candidates:
                results.append({
                    "Motor": "PostgreSQL",
                    "Estado": "Candidato Autovacuum" if (c[2] or 0) > 1000 else "Saludable",
                    "Tabla": f"{c[0]}.{c[1]}",
                    "Fase": f"Tuplas muertas: {c[2]:,}",
                    "Progreso_Bloques": f"{c[7]}% dead ratio",
                    "Detalle": f"Ejecuciones: {c[4]} auto / {c[5]} manuales | Último: {c[6]}",
                })
        else:
            # SQL Server Statistics Health
            cursor.execute(_SQLSERVER_STATS_QUERY)
            rows = cursor.fetchall()
            for r in rows:
                results.append({
                    "Motor": "SQL Server",
                    "Esquema": str(r[0]),
                    "Tabla": str(r[1]),
                    "Estadistica": str(r[2]),
                    "Filas": int(r[3] or 0),
                    "Filas_Modificadas": int(r[4] or 0),
                    "Pct_Modificado": f"{float(r[5] or 0):.1f}%",
                    "Ultima_Actualizacion": str(r[6]),
                    "Dias_Sin_Actualizar": int(r[7] or 0),
                    "Diagnostico": str(r[8]),
                })
    except Exception as exc:
        logging.error("Error executing query_maintenance_stats on %s: %s", engine, exc, exc_info=True)
        raise

    return results
