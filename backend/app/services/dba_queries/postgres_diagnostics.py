"""PostgreSQL Diagnostic Service.

Inspired by Erik Darling's PerformanceMonitor (PgTableBloatStatsCollector & PgAutovacuumStatsCollector).
Provides deep visibility into:
1. Table & Index Bloat (Dead tuples, wasted heap space, bloated user tables).
2. Autovacuum health & activity (Workers in progress, tables closest to vacuum threshold, freeze age).
"""
import logging
from typing import List, Dict, Any

_PG_BLOAT_QUERY = """
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
WHERE (n_live_tup + n_dead_tup) > 100
ORDER BY n_dead_tup DESC, pg_total_relation_size(relid) DESC
LIMIT 50;
"""

_PG_AUTOVACUUM_PROGRESS_QUERY = """
SELECT
    p.pid,
    p.datname AS database_name,
    c.relname AS table_name,
    p.phase,
    p.heap_blks_total,
    p.heap_blks_scanned,
    p.heap_blks_vacuumed,
    p.index_vacuum_count,
    p.num_dead_tuples
FROM pg_stat_progress_vacuum p
LEFT JOIN pg_class c ON c.oid = p.relid;
"""

_PG_AUTOVACUUM_CANDIDATES_QUERY = """
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
LIMIT 25;
"""


def query_pg_bloat(cursor: Any) -> List[Dict[str, Any]]:
    """Estimate table bloat, dead tuples ratio and relation sizes for PostgreSQL."""
    results: List[Dict[str, Any]] = []
    try:
        cursor.execute(_PG_BLOAT_QUERY)
        rows = cursor.fetchall()
        for r in rows:
            results.append({
                "Esquema": str(r[0]),
                "Tabla": str(r[1]),
                "Tuplas_Vivas": int(r[2] or 0),
                "Tuplas_Muertas": int(r[3] or 0),
                "Bloat_Estimado_Pct": f"{float(r[4] or 0):.1f}%",
                "Tamano_Total": str(r[5]),
                "Tamano_Tabla": str(r[6]),
                "Tamano_Indices": str(r[7]),
                "Ultimo_Autovacuum": str(r[8]),
                "Ultimo_Autoanalyze": str(r[9]),
            })
    except Exception as exc:
        logging.error("Error executing query_pg_bloat: %s", exc, exc_info=True)
        raise
    return results


def query_pg_autovacuum(cursor: Any) -> List[Dict[str, Any]]:
    """Retrieve autovacuum workers and candidate tables needing maintenance."""
    results: List[Dict[str, Any]] = []
    try:
        # First check active progress
        cursor.execute(_PG_AUTOVACUUM_PROGRESS_QUERY)
        active_rows = cursor.fetchall()
        if active_rows:
            for r in active_rows:
                results.append({
                    "Estado": "⚡ EN EJECUCIÓN",
                    "PID": str(r[0]),
                    "BD": str(r[1] or ""),
                    "Tabla": str(r[2] or "N/A"),
                    "Fase": str(r[3] or "scanning"),
                    "Bloques_Escaneados": f"{r[5]}/{r[4]}",
                    "Tuplas_Muertas": int(r[8] or 0),
                    "Detalle": f"Limpieza activa en proceso (fase: {r[3]})",
                })

        # Next check table candidates
        cursor.execute(_PG_AUTOVACUUM_CANDIDATES_QUERY)
        candidates = cursor.fetchall()
        for c in candidates:
            results.append({
                "Estado": "Candidato Autovacuum",
                "PID": "-",
                "BD": "-",
                "Tabla": f"{c[0]}.{c[1]}",
                "Fase": f"Tuplas muertas: {c[2]:,}",
                "Bloques_Escaneados": f"{c[7]}% ratio",
                "Tuplas_Muertas": int(c[2] or 0),
                "Detalle": f"Ejecuciones previas: {c[4]} auto / {c[5]} manuales. Último: {c[6]}",
            })
    except Exception as exc:
        logging.error("Error executing query_pg_autovacuum: %s", exc, exc_info=True)
        raise
    return results
