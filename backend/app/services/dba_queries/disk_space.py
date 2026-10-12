import logging

def query_disk_space(cursor, engine_type="sqlserver"):

    if engine_type == "postgres":
        query = """
            SELECT 
                d.datname AS "Drive",
                CAST(pg_database_size(d.datname) / 1073741824.0 AS NUMERIC(10,2)) AS "TotalGB"
            FROM pg_database d
            ORDER BY "TotalGB" DESC
        """
    else:
        query = """
            SELECT DISTINCT
                vs.volume_mount_point AS Drive,
                CAST(vs.total_bytes / 1073741824.0 AS DECIMAL(18,2)) AS TotalGB,
                CAST(vs.available_bytes / 1073741824.0 AS DECIMAL(18,2)) AS FreeGB,
                CAST((vs.total_bytes - vs.available_bytes) / 1073741824.0 AS DECIMAL(18,2)) AS UsedGB,
                CAST(vs.available_bytes * 100.0 / vs.total_bytes AS DECIMAL(5,2)) AS FreePct
            FROM sys.master_files AS mf
            CROSS APPLY sys.dm_os_volume_stats(mf.database_id, mf.file_id) AS vs
            ORDER BY vs.volume_mount_point
        """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        results = []
        for row in rows:
            disco = {}
            for i, col in enumerate(columns):
                val = row[i]
                # If using pg8000, Decimal is returned. Convert to float to round safely.
                if hasattr(val, 'quantize') or isinstance(val, (float, int)):
                    val = round(float(val), 2)
                disco[col] = str(val)
            results.append(disco)
        return results
    except Exception as e:
        logging.error(f"Error al consultar espacio en disco/bd: {e}")
        raise

def query_disk_space_summary(cursor):
    return []
