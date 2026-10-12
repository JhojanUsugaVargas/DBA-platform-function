"""Blocking Chain Monitor.

Inspired by Erik Darling's PerformanceMonitor (DmvBlockingSnapshotCollector & PgBlockingCollector).
Captures real-time blocker -> blocked pair trees without requiring Extended Events.
Resolves contentious objects (schema.table), transaction start times, and queries even for idle blockers.
"""
import logging
from typing import List, Dict, Any

_SQLSERVER_BLOCKING_QUERY = """
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

SELECT TOP 50
    database_name = DB_NAME(der_b.database_id),
    blocked_spid = CONVERT(integer, wt.session_id),
    blocked_login = ses_b.login_name,
    blocked_host = ses_b.host_name,
    blocked_app = ses_b.program_name,
    blocking_spid = CONVERT(integer, wt.blocking_session_id),
    blocking_login = ses_k.login_name,
    blocking_host = ses_k.host_name,
    blocking_app = ses_k.program_name,
    blocking_status = ISNULL(der_k.status, ses_k.status),
    wait_time_sec = CAST(wt.wait_duration_ms / 1000.0 AS DECIMAL(10, 2)),
    lock_mode = REPLACE(REPLACE(REPLACE(wt.wait_type, N'LCK_M_', N''), N'PAGEIOLATCH_', N''), N'PAGELATCH_', N''),
    contentious_object =
        CASE
            WHEN objparse.object_id IS NOT NULL
            THEN ISNULL(QUOTENAME(OBJECT_SCHEMA_NAME(objparse.object_id, objparse.database_id)) + N'.' + QUOTENAME(OBJECT_NAME(objparse.object_id, objparse.database_id)), der_b.wait_resource)
            WHEN resparse.resource_database_id IS NOT NULL
            THEN N'Unresolved: ' +
                 CASE WHEN resparse.lock_type IS NULL THEN N'' ELSE LOWER(resparse.lock_type) + N' lock, ' END +
                 N'database: ' + COALESCE(DB_NAME(resparse.resource_database_id), DB_NAME(der_b.database_id), N'unknown')
            ELSE der_b.wait_resource
        END,
    blocked_sql = SUBSTRING(dest_b.text, 1, 300),
    blocking_sql = SUBSTRING(dest_k.text, 1, 300)
FROM sys.dm_os_waiting_tasks AS wt
JOIN sys.dm_exec_sessions AS ses_b
  ON ses_b.session_id = wt.session_id
LEFT JOIN sys.dm_exec_requests AS der_b
  ON der_b.session_id = wt.session_id
LEFT JOIN sys.dm_exec_sessions AS ses_k
  ON ses_k.session_id = wt.blocking_session_id
LEFT JOIN sys.dm_exec_requests AS der_k
  ON der_k.session_id = wt.blocking_session_id
LEFT JOIN sys.dm_exec_connections AS con_k
  ON con_k.session_id = wt.blocking_session_id
OUTER APPLY sys.dm_exec_sql_text(der_b.sql_handle) AS dest_b
OUTER APPLY sys.dm_exec_sql_text(COALESCE(der_k.sql_handle, con_k.most_recent_sql_handle)) AS dest_k
OUTER APPLY
(
    SELECT
        database_id = TRY_CONVERT(integer, PARSENAME(REPLACE(SUBSTRING(der_b.wait_resource, 9, 200), N':', N'.'), 3)),
        object_id = TRY_CONVERT(integer, PARSENAME(REPLACE(SUBSTRING(der_b.wait_resource, 9, 200), N':', N'.'), 2))
    WHERE der_b.wait_resource LIKE N'OBJECT: %'
) AS objparse
OUTER APPLY
(
    SELECT
        resource_database_id =
            TRY_CONVERT
            (
                integer,
                NULLIF(LEFT(d.tail, PATINDEX(N'%[^0-9]%', d.tail + N'.') - 1), N'')
            ),
        lock_type =
            CASE
                WHEN der_b.wait_resource LIKE N'%KEY: %'    THEN N'KEY'
                WHEN der_b.wait_resource LIKE N'%OBJECT: %' THEN N'OBJECT'
                WHEN der_b.wait_resource LIKE N'%RID: %'    THEN N'RID'
                WHEN der_b.wait_resource LIKE N'%PAGE: %'   THEN N'PAGE'
                ELSE LEFT(UPPER(LEFT(der_b.wait_resource, CHARINDEX(N':', der_b.wait_resource + N':') - 1)), 32)
            END
    FROM
    (
        SELECT tail = SUBSTRING(wt.resource_description, CHARINDEX(N'dbid=', wt.resource_description) + 5, 10)
    ) AS d
    WHERE wt.wait_type LIKE N'LCK[_]%'
    AND   der_b.wait_resource IS NOT NULL
    AND   der_b.wait_resource <> N''
    AND   CHARINDEX(N'dbid=', wt.resource_description) > 0
) AS resparse
WHERE wt.blocking_session_id IS NOT NULL
AND   wt.blocking_session_id <> 0
AND   wt.blocking_session_id <> wt.session_id
AND   wt.session_id > 50
AND   wt.session_id <> @@SPID
AND   (
          wt.wait_type LIKE N'LCK[_]%'
          OR wt.wait_type LIKE N'PAGELATCH[_]%'
          OR wt.wait_type LIKE N'PAGEIOLATCH[_]%'
          OR wt.wait_type = N'RESOURCE_SEMAPHORE'
      )
ORDER BY wt.wait_duration_ms DESC
OPTION(RECOMPILE);
"""

_POSTGRES_BLOCKING_QUERY = """
SELECT
    blocked.pid AS blocked_pid,
    blocked.usename AS blocked_user,
    blocked.application_name AS blocked_app,
    blocked.state AS blocked_state,
    blocked.wait_event_type || ': ' || COALESCE(blocked.wait_event, 'Lock') AS wait_event,
    ROUND(EXTRACT(EPOCH FROM (clock_timestamp() - blocked.query_start))::numeric, 1) AS blocked_duration_sec,
    blocker.pid AS blocking_pid,
    blocker.usename AS blocking_user,
    blocker.application_name AS blocking_app,
    blocker.state AS blocking_state,
    CASE WHEN blocker.state = 'idle in transaction' THEN 'SI (Idle in TX)' ELSE 'NO' END AS blocker_idle_tx,
    ROUND(EXTRACT(EPOCH FROM (clock_timestamp() - blocker.xact_start))::numeric, 1) AS blocker_tx_duration_sec,
    SUBSTRING(blocked.query FROM 1 FOR 150) AS blocked_query,
    SUBSTRING(blocker.query FROM 1 FOR 150) AS blocking_query
FROM pg_stat_activity blocked
CROSS JOIN LATERAL unnest(pg_blocking_pids(blocked.pid)) AS blocker_pid
JOIN pg_stat_activity blocker ON blocker.pid = blocker_pid
WHERE blocked.pid <> pg_backend_pid()
ORDER BY blocked_duration_sec DESC NULLS LAST
LIMIT 50;
"""


def query_blocking_chain(cursor: Any, engine: str) -> List[Dict[str, Any]]:
    """Capture real-time blocking chains with full blocker/blocked diagnostics."""
    results: List[Dict[str, Any]] = []

    try:
        if engine == "postgres":
            cursor.execute(_POSTGRES_BLOCKING_QUERY)
            rows = cursor.fetchall()
            for r in rows:
                results.append({
                    "Blocked_PID": str(r[0]),
                    "Blocked_User": str(r[1] or ""),
                    "Blocked_App": str(r[2] or ""),
                    "Wait_Event": str(r[4] or ""),
                    "Wait_Sec": float(r[5] or 0),
                    "Blocking_PID": str(r[6]),
                    "Blocking_User": str(r[7] or ""),
                    "Blocking_Status": str(r[9] or ""),
                    "Blocker_Idle_In_TX": str(r[10] or "NO"),
                    "Blocker_TX_Sec": float(r[11] or 0),
                    "Blocked_Query": " ".join(str(r[12] or "").split()),
                    "Blocking_Query": " ".join(str(r[13] or "").split()),
                })
        else:
            cursor.execute(_SQLSERVER_BLOCKING_QUERY)
            rows = cursor.fetchall()
            for r in rows:
                results.append({
                    "DB": str(r[0] or ""),
                    "Blocked_SPID": str(r[1]),
                    "Blocked_User": str(r[2] or ""),
                    "Blocking_SPID": str(r[5]),
                    "Blocking_User": str(r[6] or ""),
                    "Blocking_Status": str(r[9] or ""),
                    "Wait_Sec": float(r[10] or 0),
                    "Lock_Mode": str(r[11] or ""),
                    "Contentious_Object": str(r[12] or ""),
                    "Blocked_SQL": " ".join(str(r[13] or "").split()),
                    "Blocking_SQL": " ".join(str(r[14] or "").split()),
                })
    except Exception as exc:
        logging.error("Error executing query_blocking_chain on %s: %s", engine, exc, exc_info=True)
        raise

    return results
