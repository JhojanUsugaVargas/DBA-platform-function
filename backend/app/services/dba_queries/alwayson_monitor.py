"""
Servicio para validar el estado de Always On Availability Groups.
"""
import logging

def query_alwayson_status(cursor):
    """
    Ejecuta la validación de Always On y devuelve el estado o una tabla con los AGs.
    """
    # 1. Verificar si Always On est\u00e1 habilitado
    check_enabled_query = "SELECT CONVERT(BIT, SERVERPROPERTY('IsHadrEnabled'))"
    
    try:
        cursor.execute(check_enabled_query)
        is_enabled = cursor.fetchone()[0]
        
        if not is_enabled:
            return {
                'type': 'info',
                'message': (
                    f"**Always On no est\u00e1 habilitado** en la instancia **{cursor.execute('SELECT @@SERVERNAME').fetchone()[0]}**.\n\n"
                    "**Requerimientos:**\n"
                    "• Windows Server Failover Cluster (WSFC)\n"
                    "• SQL Server Enterprise Edition\n"
                    "• Feature habilitada vía SSMS o PowerShell"
                )
            }

        # 2. Consultar grupos de disponibilidad
        ag_query = """
        SELECT 
            ag.name                                 AS AvailabilityGroup_Name,
            ar.replica_server_name                  AS Replica,
            ar.availability_mode_desc               AS Modo_Sincronizacion,
            ar.failover_mode_desc                   AS Modo_Failover,
            ars.role_desc                           AS Rol_Actual,
            ars.operational_state_desc              AS Estado_Operacional,
            ars.connected_state_desc                AS Estado_Conexion,
            drs.synchronization_state_desc          AS Estado_Sincronizacion,
            drs.synchronization_health_desc         AS Salud_Sincronizacion,
            FORMAT(drs.last_commit_time, 'yyyy-MM-dd HH:mm:ss') AS Ultimo_Commit,
            DATEDIFF(MINUTE, drs.last_commit_time, GETDATE()) AS Minutos_Desfaso
        FROM sys.availability_groups ag
        INNER JOIN sys.availability_replicas ar ON ag.group_id = ar.group_id
        INNER JOIN sys.dm_hadr_availability_replica_states ars ON ar.replica_id = ars.replica_id
        INNER JOIN sys.dm_hadr_database_replica_states drs ON ar.replica_id = drs.replica_id
        WHERE drs.is_local = 1
        ORDER BY ag.name, ar.replica_server_name;
        """
        
        cursor.execute(ag_query)
        rows = cursor.fetchall()
        
        if not rows:
            return {
                'type': 'info',
                'message': f"**Always On habilitado**, pero no existenAvailability Groups creados en **{cursor.execute('SELECT @@SERVERNAME').fetchone()[0]}**."
            }

        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in rows:
            results.append(dict(zip(columns, [str(val) if val is not None else 'N/A' for val in row])))
            
        return {
            'type': 'table',
            'title': '🔗 Estado Always On Availability Groups',
            'data': results
        }

    except Exception as e:
        logging.error(f"Error al consultar Always On: {e}")
        raise
