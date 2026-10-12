import logging

def query_database_sizes(cursor, engine_type="sqlserver"):
    if engine_type == "postgres":
        query = """
            SELECT 
                d.datname AS DatabaseName,
                'DATA (Postgres)' AS FileType,
                CAST(pg_database_size(d.datname) / 1048576.0 AS NUMERIC(10,2)) AS SizeMB,
                'N/A' AS PhysicalPath
            FROM pg_database d
            WHERE d.datname NOT LIKE 'template%'
            ORDER BY SizeMB DESC
        """
    else:
        query = """
            SELECT 
                DB_NAME(database_id) AS DatabaseName,
                type_desc AS FileType,
                CAST(size * 8.0 / 1024 AS DECIMAL(18,2)) AS SizeMB,
                physical_name AS PhysicalPath
            FROM sys.master_files
            WHERE database_id > 4  -- Excluye bases de sistema
            ORDER BY DB_NAME(database_id), type_desc
        """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        results = []
        for row in rows:
            item = {}
            for i, col in enumerate(columns):
                val = row[i]
                if hasattr(val, 'quantize') or isinstance(val, (float, int)):
                    val = round(float(val), 2)
                item[col] = str(val)
            results.append(item)
        
        return results
    except Exception as e:
        logging.error(f"Error al consultar tamaños de bases de datos: {e}")
        raise
