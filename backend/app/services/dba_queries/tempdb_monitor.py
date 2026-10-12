import logging

def query_tempdb_usage(cursor, engine_type="sqlserver"):
    """
    Obtiene el estado de archivos de uso temporal (TempDB en SQL, temp_files en Postgres)
    """
    if engine_type == "postgres":
        query = """
            SELECT 
                datname AS FileName,
                'N/A (Dinámico)' AS PhysicalPath,
                CAST(temp_bytes / 1048576.0 AS NUMERIC(10,2)) AS SizeMB,
                'TEMP_FILES' AS FileType
            FROM pg_stat_database 
            WHERE temp_bytes > 0
            ORDER BY temp_bytes DESC
        """
        try:
            cursor.execute(query)
            files_rows = cursor.fetchall()
            files = []
            for r in files_rows:
                val = r[2] if r[2] is not None else 0
                if hasattr(val, 'quantize') or isinstance(val, (float, int)):
                    val = round(float(val), 2)
                files.append({
                    'name': str(r[0]),
                    'path': str(r[1]),
                    'size': str(val),
                    'type': str(r[3])
                })
            
            # Si no hay bases usando temp_bytes, agregamos una dummy para mostrar que funciona
            if not files:
                files.append({
                    'name': 'Bases_de_Datos_PG',
                    'path': 'Archivos efímeros gestionados por el SO',
                    'size': '0',
                    'type': 'TEMP_FILES'
                })

            return {
                'files': files,
                'active_sessions': [] # Postgres tracking per session is complex without extensions
            }
        except Exception as e:
            logging.error(f"Error al consultar Temp Files en Postgres: {e}")
            raise
    else:
        # 1. Archivos físicos (SQL Server)
        files_query = """
            SELECT 
                name AS FileName,
                physical_name AS PhysicalPath,
                size * 8 / 1024 AS SizeMB,
                type_desc AS FileType
            FROM sys.master_files
            WHERE database_id = DB_ID('tempdb')
        """
        
        # 2. Uso por sesión
        sessions_query = """
            SELECT 
                s.session_id AS SessionID,
                s.login_name AS LoginName,
                s.status AS Status,
                (su.user_objects_alloc_page_count * 8.0 / 1024) AS UserObjectsMB,
                (su.internal_objects_alloc_page_count * 8.0 / 1024) AS InternalObjectsMB,
                CAST(r.text AS NVARCHAR(MAX)) AS LastQuery
            FROM sys.dm_db_session_space_usage AS su
            JOIN sys.dm_exec_sessions AS s ON s.session_id = su.session_id
            LEFT JOIN sys.dm_exec_requests req ON s.session_id = req.session_id
            OUTER APPLY sys.dm_exec_sql_text(req.sql_handle) AS r
            WHERE (su.user_objects_alloc_page_count > 0 OR su.internal_objects_alloc_page_count > 0)
            AND s.session_id > 50
            ORDER BY (su.user_objects_alloc_page_count + su.internal_objects_alloc_page_count) DESC
        """
        
        try:
            cursor.execute(files_query)
            files_rows = cursor.fetchall()
            files = []
            for r in files_rows:
                files.append({
                    'name': str(r[0]),
                    'path': str(r[1]),
                    'size': str(r[2]),
                    'type': str(r[3])
                })
                
            cursor.execute(sessions_query)
            sessions_rows = cursor.fetchall()
            sessions = []
            for r in sessions_rows:
                sessions.append({
                    'sid': str(r[0]),
                    'login': str(r[1]),
                    'status': str(r[2]),
                    'user_mb': str(round(float(r[3]), 2)),
                    'internal_mb': str(round(float(r[4]), 2)),
                    'query': str(r[5]) if r[5] else 'N/A'
                })
                
            return {
                'files': files,
                'active_sessions': sessions
            }
        except Exception as e:
            logging.error(f"Error al consultar TempDB: {e}")
            raise
