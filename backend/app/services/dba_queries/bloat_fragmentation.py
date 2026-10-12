"""Table Bloat & Index Fragmentation Monitor (Multi-Engine).

Supports:
- Microsoft SQL Server: Table space allocation, wasted space (bloat in MB and %), heaps without clustered indexes, and unused indexes.
- PostgreSQL: Table bloat, dead tuples ratio, heap vs index size, and dead tuple accumulation.
"""
import logging
from typing import List, Dict, Any

_SQLSERVER_BLOAT_QUERY = """
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

SELECT TOP 50
    Esquema = s.name,
    Tabla = t.name,
    Indice = ISNULL(i.name, '(HEAP sin índice)'),
    Tipo = i.type_desc,
    Filas = p.rows,
    Total_MB = CAST(ROUND((SUM(a.total_pages) * 8.0) / 1024, 2) AS NUMERIC(18, 2)),
    Usado_MB = CAST(ROUND((SUM(a.used_pages) * 8.0) / 1024, 2) AS NUMERIC(18, 2)),
    Espacio_Libre_MB = CAST(ROUND(((SUM(a.total_pages) - SUM(a.used_pages)) * 8.0) / 1024, 2) AS NUMERIC(18, 2)),
    Desperdicio_Pct = CASE WHEN SUM(a.total_pages) > 0
                           THEN CAST(ROUND(((SUM(a.total_pages) - SUM(a.used_pages)) * 100.0) / SUM(a.total_pages), 1) AS NUMERIC(5, 1))
                           ELSE 0 END,
    Lecturas_User = ISNULL(ius.user_seeks + ius.user_scans + ius.user_lookups, 0),
    Escrituras_User = ISNULL(ius.user_updates, 0),
    Diagnostico = CASE
        WHEN i.type_desc = 'HEAP' AND p.rows > 5000 THEN '⚠️ Heap sin índice Clustered'
        WHEN (SUM(a.total_pages) - SUM(a.used_pages)) * 8.0 / 1024 > 50 AND ((SUM(a.total_pages) - SUM(a.used_pages)) * 100.0) / SUM(a.total_pages) > 25 THEN '⚠️ Alto espacio no usado (Bloat)'
        WHEN ius.user_updates > 5000 AND (ius.user_seeks + ius.user_scans + ius.user_lookups) = 0 THEN '⚠️ Índice no usado (Costo de I/O)'
        ELSE 'Saludable'
    END
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.indexes i ON t.object_id = i.object_id
JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
JOIN sys.allocation_units a ON p.partition_id = a.container_id
LEFT JOIN sys.dm_db_index_usage_stats ius
    ON ius.object_id = i.object_id
    AND ius.index_id = i.index_id
    AND ius.database_id = DB_ID()
WHERE t.is_ms_shipped = 0
GROUP BY s.name, t.name, i.name, i.type_desc, p.rows, ius.user_seeks, ius.user_scans, ius.user_lookups, ius.user_updates
HAVING SUM(a.total_pages) > 10
ORDER BY Espacio_Libre_MB DESC, Total_MB DESC;
"""

_POSTGRES_BLOAT_QUERY = """
SELECT
    schemaname AS schema_name,
    relname AS table_name,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    CASE WHEN (n_live_tup + n_dead_tup) > 0
         THEN ROUND(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 1)
         ELSE 0.0 END AS dead_tuple_pct,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(pg_indexes_size(relid)) AS index_size,
    COALESCE(TO_CHAR(last_autovacuum, 'YYYY-MM-DD HH24:MI:SS'), 'Nunca') AS last_autovacuum,
    COALESCE(TO_CHAR(last_autoanalyze, 'YYYY-MM-DD HH24:MI:SS'), 'Nunca') AS last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC, pg_total_relation_size(relid) DESC
LIMIT 50;
"""


def query_bloat_fragmentation(cursor: Any, engine: str) -> List[Dict[str, Any]]:
    """Capture table bloat, index space waste, and fragmentation for SQL Server or PostgreSQL."""
    results: List[Dict[str, Any]] = []

    try:
        if engine == "postgres":
            cursor.execute(_POSTGRES_BLOAT_QUERY)
            rows = cursor.fetchall()
            for r in rows:
                results.append({
                    "Motor": "PostgreSQL",
                    "Esquema": str(r[0]),
                    "Tabla": str(r[1]),
                    "Tuplas_Vivas": int(r[2] or 0),
                    "Tuplas_Muertas": int(r[3] or 0),
                    "Bloat_Estimado": f"{float(r[4] or 0):.1f}%",
                    "Tamano_Total": str(r[5]),
                    "Tamano_Tabla": str(r[6]),
                    "Tamano_Indices": str(r[7]),
                    "Ultimo_Autovacuum": str(r[8]),
                })
        else:
            cursor.execute(_SQLSERVER_BLOAT_QUERY)
            rows = cursor.fetchall()
            for r in rows:
                results.append({
                    "Motor": "SQL Server",
                    "Esquema": str(r[0]),
                    "Tabla": str(r[1]),
                    "Indice": str(r[2]),
                    "Tipo": str(r[3]),
                    "Filas": int(r[4] or 0),
                    "Total_MB": float(r[5] or 0),
                    "Usado_MB": float(r[6] or 0),
                    "Espacio_Libre_MB": float(r[7] or 0),
                    "Desperdicio_Bloat": f"{float(r[8] or 0):.1f}%",
                    "Lecturas": int(r[9] or 0),
                    "Escrituras": int(r[10] or 0),
                    "Diagnostico": str(r[11]),
                })
    except Exception as exc:
        logging.error("Error executing query_bloat_fragmentation on %s: %s", engine, exc, exc_info=True)
        raise

    return results
