import logging

def query_instance_monitor(cursor, engine_type="sqlserver"):

    if engine_type == "postgres":
        query = """
            SELECT 
                current_timestamp as Fecha,
                (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active') as Sesiones_Ejecutando,
                (SELECT COUNT(*) FROM pg_stat_activity) as Sesiones_Totales
        """
        try:
            cursor.execute(query)
            row = cursor.fetchone()
            if not row: return None
            return {
                'fecha': str(row[0]),
                'sql_cpu_percent': "N/A (Postgres)",
                'cpu_idle': "N/A",
                'cpu_other': "N/A",
                'sql_mem_used_mb': "N/A",
                'sql_max_mem_mb': "N/A",
                'sql_mem_free_mb': "N/A",
                'sql_mem_usage_percent': "N/A",
                'sessions_running': int(row[1]) if row[1] is not None else 0,
                'sessions_user': int(row[2]) if row[2] is not None else 0,
                'requests_active': int(row[1]) if row[1] is not None else 0,
            }
        except Exception as e:
            logging.error(f"Error en monitor Postgres: {e}")
            raise
    else:
        query = """
            SET NOCOUNT ON;
            DECLARE @SQL_CPU INT
            DECLARE @SystemIdle INT
            SELECT TOP 1
                @SQL_CPU = record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int'),
                @SystemIdle = record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int')
            FROM (
                SELECT CONVERT(XML, record) AS record
                FROM sys.dm_os_ring_buffers
                WHERE ring_buffer_type = 'RING_BUFFER_SCHEDULER_MONITOR' AND record LIKE '%<SystemHealth>%'
            ) x ORDER BY record.value('(./Record/@id)[1]', 'int') DESC;

            DECLARE @TotalPhysicalMB INT
            DECLARE @AvailablePhysicalMB INT
            SELECT @TotalPhysicalMB = total_physical_memory_kb / 1024, @AvailablePhysicalMB = available_physical_memory_kb / 1024
            FROM sys.dm_os_sys_memory;

            SELECT
                GETDATE() AS Fecha,
                @SQL_CPU AS SQL_CPU_Porcentaje,
                @SystemIdle AS CPU_Libre_Servidor,
                (100 - ISNULL(@SQL_CPU, 0) - ISNULL(@SystemIdle, 0)) AS CPU_Otros_Procesos,
                (pm.physical_memory_in_use_kb / 1024) AS SQL_Memory_Usada_MB,
                @TotalPhysicalMB AS Server_Total_Memory_MB,
                @AvailablePhysicalMB AS Server_Memory_Libre_MB,
                ((@TotalPhysicalMB - @AvailablePhysicalMB) * 100.0 / @TotalPhysicalMB) AS OS_Memory_Usage_Percent,
                (SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE status = 'running') AS Sesiones_Ejecutando,
                (SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE is_user_process = 1) AS Sesiones_Usuario,
                (SELECT COUNT(*) FROM sys.dm_exec_requests) AS Requests_Activas
            FROM sys.dm_os_process_memory pm;
        """
        try:
            cursor.execute(query)
            row = cursor.fetchone()
            if not row: return None
            return {
                'fecha': str(row[0]),
                'sql_cpu_percent': int(row[1]) if row[1] is not None else 0,
                'cpu_idle': int(row[2]) if row[2] is not None else 0,
                'cpu_other': int(row[3]) if row[3] is not None else 0,
                'sql_mem_used_mb': int(row[4]) if row[4] is not None else 0,
                'sql_max_mem_mb': int(row[5]) if row[5] is not None else 0, 
                'sql_mem_free_mb': int(row[6]) if row[6] is not None else 0, 
                'sql_mem_usage_percent': round(float(row[7]), 1) if row[7] is not None else 0,
                'sessions_running': int(row[8]) if row[8] is not None else 0,
                'sessions_user': int(row[9]) if row[9] is not None else 0,
                'requests_active': int(row[10]) if row[10] is not None else 0,
            }
        except Exception as e:
            logging.error(f"Error en monitor SQL Server: {e}")
            raise
