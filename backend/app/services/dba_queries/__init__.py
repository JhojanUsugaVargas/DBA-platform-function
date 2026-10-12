"""Módulo de queries DBA - Consultas de telemetría y diagnóstico para SQL Server y PostgreSQL."""
from app.services.dba_queries.alwayson_monitor import query_alwayson_status
from app.services.dba_queries.database_sizes import query_database_sizes
from app.services.dba_queries.disk_space import query_disk_space, query_disk_space_summary
from app.services.dba_queries.instance_monitor import query_instance_monitor
from app.services.dba_queries.job_monitor import query_job_monitor
from app.services.dba_queries.tempdb_monitor import query_tempdb_usage
from app.services.dba_queries.blocking_monitor import query_blocking_chain
from app.services.dba_queries.wait_stats_monitor import query_wait_stats
from app.services.dba_queries.postgres_diagnostics import query_pg_bloat, query_pg_autovacuum

__all__ = [
    "query_alwayson_status",
    "query_database_sizes",
    "query_disk_space",
    "query_disk_space_summary",
    "query_instance_monitor",
    "query_job_monitor",
    "query_tempdb_usage",
    "query_blocking_chain",
    "query_wait_stats",
    "query_pg_bloat",
    "query_pg_autovacuum",
]
