"""
Servicio para consultar el historial y estado de los Jobs de SQL Server.
"""
import logging

def query_job_monitor(cursor):
    """
    Ejecuta la consulta de historial de jobs y formatea los resultados para la tabla.
    """
    query = """
    WITH JobHistory AS (
        SELECT 
            j.name AS Job_Name,
            h.run_status,
            h.run_duration,
            msdb.dbo.agent_datetime(h.run_date, h.run_time) AS ExecutionDateTime
        FROM msdb.dbo.sysjobs j
        INNER JOIN msdb.dbo.sysjobhistory h 
            ON j.job_id = h.job_id
        WHERE 
            h.step_id = 0
            AND msdb.dbo.agent_datetime(h.run_date, h.run_time) >= DATEADD(DAY, -1, GETDATE())
    ),
    Durations AS (
        SELECT 
            Job_Name,
            run_status,
            ExecutionDateTime,
            (run_duration / 10000) * 3600 + 
            ((run_duration / 100) % 100) * 60 + 
            (run_duration % 100) AS Duracion_Segundos
        FROM JobHistory
    )
    SELECT
        Job_Name,
        COUNT(*)                                    AS Total_Ejecuciones,
        SUM(CASE WHEN run_status = 1 THEN 1 ELSE 0 END) AS Exitos,
        SUM(CASE WHEN run_status = 0 THEN 1 ELSE 0 END) AS Fallos,
        SUM(CASE WHEN run_status = 2 THEN 1 ELSE 0 END) AS Retries,
        SUM(CASE WHEN run_status = 3 THEN 1 ELSE 0 END) AS Cancelados,
        SUM(CASE WHEN run_status = 4 THEN 1 ELSE 0 END) AS En_Progreso,
        
        FORMAT(MIN(ExecutionDateTime), 'yyyy-MM-dd HH:mm:ss') AS Primera_Ejecucion,
        FORMAT(MAX(ExecutionDateTime), 'yyyy-MM-dd HH:mm:ss') AS Ultima_Ejecucion,

        RIGHT('0' + CAST(FLOOR(AVG(Duracion_Segundos) / 3600) AS VARCHAR(10)), 2) + ':' +
        RIGHT('0' + CAST(FLOOR((AVG(Duracion_Segundos) % 3600) / 60) AS VARCHAR(2)), 2) + ':' +
        RIGHT('0' + CAST(CAST(AVG(Duracion_Segundos) AS INT) % 60 AS VARCHAR(2)), 2) 
                                                    AS Duracion_Promedio
    FROM Durations
    GROUP BY Job_Name
    ORDER BY Total_Ejecuciones DESC, Fallos DESC;
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        results = []
        for row in rows:
            results.append(dict(zip(columns, [str(val) if val is not None else '0' for val in row])))
            
        return results
    except Exception as e:
        logging.error(f"Error al consultar el monitor de jobs: {e}")
        raise
