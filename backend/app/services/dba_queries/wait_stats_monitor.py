"""Wait Statistics Monitor.

Inspired by Erik Darling's PerformanceMonitor (WaitStatsCollector & IgnoredWaitDefaults).
Retrieves top system waits while filtering out benign background engine waits
to expose true performance bottlenecks (CPU pressure, disk I/O, locking, memory).
"""
import logging
from typing import List, Dict, Any

_SQLSERVER_WAIT_STATS_QUERY = """
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

SELECT TOP 25
    wait_type = ws.wait_type,
    waiting_tasks_count = ws.waiting_tasks_count,
    wait_time_sec = CAST(ws.wait_time_ms / 1000.0 AS DECIMAL(18, 2)),
    signal_wait_sec = CAST(ws.signal_wait_time_ms / 1000.0 AS DECIMAL(18, 2)),
    signal_wait_pct = CASE WHEN ws.wait_time_ms > 0
                           THEN CAST((ws.signal_wait_time_ms * 100.0) / ws.wait_time_ms AS DECIMAL(5, 2))
                           ELSE 0 END,
    avg_wait_ms = CASE WHEN ws.waiting_tasks_count > 0
                       THEN CAST(ws.wait_time_ms * 1.0 / ws.waiting_tasks_count AS DECIMAL(18, 2))
                       ELSE 0 END
FROM sys.dm_os_wait_stats AS ws
WHERE ws.wait_time_ms > 0
  AND ws.wait_type NOT IN (
      'AZURE_IMDS_VERSIONS', 'BMPALLOCATION', 'BMPBUILD', 'BMPREPARTITION',
      'BROKER_EVENTHANDLER', 'BROKER_RECEIVE_WAITFOR', 'BROKER_TASK_STOP',
      'BROKER_TO_FLUSH', 'BROKER_TRANSMITTER', 'BUFFERPOOL_SCAN',
      'CHECKPOINT_QUEUE', 'CHKPT', 'CLR_AUTO_EVENT', 'CLR_MANUAL_EVENT',
      'CLR_SEMAPHORE', 'COLUMNSTORE_BUILD_THROTTLE', 'DAC_INIT',
      'DBMIRRORING_CMD', 'DBMIRROR_DBM_EVENT', 'DBMIRROR_DBM_MUTEX',
      'DBMIRROR_EVENTS_QUEUE', 'DBMIRROR_SEND', 'DBMIRROR_WORKER_QUEUE',
      'DIRTY_PAGE_POLL', 'DIRTY_PAGE_TABLE_LOCK', 'DISPATCHER_QUEUE_SEMAPHORE',
      'FSAGENT', 'FT_IFTSHC_MUTEX', 'FT_IFTS_SCHEDULER_IDLE_WAIT',
      'HADR_CLUSAPI_CALL', 'HADR_FABRIC_CALLBACK', 'HADR_FILESTREAM_IOMGR_IOCOMPLETION',
      'HADR_LOGCAPTURE_WAIT', 'HADR_NOTIFICATION_DEQUEUE', 'HADR_TIMER_TASK',
      'HADR_WORK_QUEUE', 'KSOURCE_WAKEUP', 'LAZYWRITER_SLEEP', 'LOGMGR_QUEUE',
      'MEMORY_ALLOCATION_EXT', 'ONDEMAND_TASK_QUEUE', 'PARALLEL_REDO_DRAIN_WORKER',
      'PARALLEL_REDO_FLOW_CONTROL', 'PARALLEL_REDO_LOG_CACHE', 'PARALLEL_REDO_TRAN_LIST',
      'PARALLEL_REDO_TRAN_TURN', 'PARALLEL_REDO_WORKER_SYNC', 'PARALLEL_REDO_WORKER_WAIT_WORK',
      'PERFORMANCE_COUNTERS_RWLOCK', 'PREEMPTIVE_OS_FLUSHFILEBUFFERS', 'PREEMPTIVE_XE_CALLBACKEXECUTE',
      'PREEMPTIVE_XE_DISPATCHER', 'PREEMPTIVE_XE_GETTARGETSTATE', 'PREEMPTIVE_XE_SESSIONCOMMIT',
      'PREEMPTIVE_XE_TARGETFINALIZE', 'PREEMPTIVE_XE_TARGETINIT', 'PRINT_ROLLBACK_PROGRESS',
      'PURVIEW_POLICY_SDK_PREEMPTIVE_SCHEDULING', 'PVS_PREALLOCATE', 'PWAIT_ALL_COMPONENTS_INITIALIZED',
      'PWAIT_DIRECTLOGCONSUMER_GETNEXT', 'PWAIT_EXTENSIBILITY_CLEANUP_TASK', 'PWAIT_HADRSIM',
      'PWAIT_HADR_ACTION_COMPLETED', 'PWAIT_HADR_CHANGE_NOTIFIER_TERMINATION_SYNC',
      'PWAIT_HADR_CLUSTER_INTEGRATION', 'PWAIT_HADR_FAILOVER_COMPLETED', 'PWAIT_HADR_JOIN',
      'PWAIT_HADR_OFFLINE_COMPLETED', 'PWAIT_HADR_ONLINE_COMPLETED', 'PWAIT_HADR_POST_ONLINE_COMPLETED',
      'PWAIT_HADR_SERVER_READY_CONNECTIONS', 'PWAIT_HADR_WORKITEM_COMPLETED', 'PWAIT_MASTERDBREADY',
      'QDS_ASYNC_QUEUE', 'QDS_CLEANUP_STALE_QUERIES_TASK_MAIN_LOOP_SLEEP',
      'QDS_PERSIST_TASK_MAIN_LOOP_SLEEP', 'QDS_SHUTDOWN_QUEUE', 'REDO_THREAD_PENDING_WORK',
      'REQUEST_FOR_DEADLOCK_SEARCH', 'RESOURCE_QUEUE', 'SERVER_IDLE_CHECK',
      'SLEEP_BPOOL_FLUSH', 'SLEEP_DBSTARTUP', 'SLEEP_DCOMSTARTUP', 'SLEEP_MASTERDBREADY',
      'SLEEP_MASTERMDREADY', 'SLEEP_MASTERUPGRADED', 'SLEEP_MSDBSTARTUP',
      'SLEEP_SYSTEMTASK', 'SLEEP_TASK', 'SLEEP_TEMPDBSTARTUP', 'SNI_CRITICAL_SECTION',
      'SOS_WORK_DISPATCHER', 'SP_SERVER_DIAGNOSTICS_SLEEP', 'SQLTRACE_BUFFER_FLUSH',
      'SQLTRACE_FILE_BUFFER', 'SQLTRACE_FILE_READ_IO_COMPLETION', 'SQLTRACE_FILE_WRITE_IO_COMPLETION',
      'SQLTRACE_INCREMENTAL_FLUSH_SLEEP', 'SQLTRACE_PENDING_BUFFER_WRITERS', 'STARTUP_DEPENDENCY_MANAGER',
      'UCS_SESSION_REGISTRATION', 'VDI_CLIENT_OTHER', 'WAITFOR', 'WAITFOR_TASKSHUTDOWN',
      'WAIT_FOR_RESULTS', 'WAIT_XTP_CKPT_CLOSE', 'WAIT_XTP_HOST_WAIT', 'WAIT_XTP_OFFLINE_CKPT_NEW_LOG',
      'WAIT_XTP_RECOVERY', 'XE_BUFFERMGR_ALLPROCESSED_EVENT', 'XE_BUFFERMGR_FREEBUF_EVENT',
      'XE_DISPATCHER_JOIN', 'XE_DISPATCHER_WAIT', 'XE_LIVE_TARGET_TVF', 'XE_TIMER_EVENT'
  )
ORDER BY ws.wait_time_ms DESC
OPTION(RECOMPILE);
"""

_POSTGRES_WAIT_STATS_QUERY = """
SELECT
    COALESCE(wait_event_type, 'CPU / Active Compute') AS wait_type,
    COALESCE(wait_event, 'Executing on CPU') AS wait_event,
    COUNT(*) AS active_sessions,
    ROUND(MAX(EXTRACT(EPOCH FROM (clock_timestamp() - query_start)))::numeric, 1) AS max_duration_sec,
    string_agg(DISTINCT usename, ', ') AS users,
    string_agg(DISTINCT application_name, ', ') AS apps
FROM pg_stat_activity
WHERE state = 'active'
  AND pid <> pg_backend_pid()
GROUP BY wait_event_type, wait_event
ORDER BY active_sessions DESC, max_duration_sec DESC;
"""


def query_wait_stats(cursor: Any, engine: str) -> List[Dict[str, Any]]:
    """Retrieve top diagnostic wait stats filtered of benign engine background tasks."""
    results: List[Dict[str, Any]] = []

    try:
        if engine == "postgres":
            cursor.execute(_POSTGRES_WAIT_STATS_QUERY)
            rows = cursor.fetchall()
            for r in rows:
                results.append({
                    "Wait_Type": str(r[0] or ""),
                    "Wait_Event": str(r[1] or ""),
                    "Active_Sessions": int(r[2] or 0),
                    "Max_Duration_Sec": float(r[3] or 0),
                    "Users": str(r[4] or ""),
                    "Apps": str(r[5] or ""),
                })
        else:
            cursor.execute(_SQLSERVER_WAIT_STATS_QUERY)
            rows = cursor.fetchall()
            for r in rows:
                results.append({
                    "Tipo_Espera": str(r[0]),
                    "Tareas_Esperando": int(r[1]),
                    "Tiempo_Total_Seg": float(r[2]),
                    "Tiempo_CPU_Seg": float(r[3]),
                    "CPU_Pressure_Pct": f"{float(r[4]):.1f}%",
                    "Promedio_Espera_Ms": float(r[5]),
                })
    except Exception as exc:
        logging.error("Error executing query_wait_stats on %s: %s", engine, exc, exc_info=True)
        raise

    return results
