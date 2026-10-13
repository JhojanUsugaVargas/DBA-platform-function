"""Remote Database Connection and Execution Service.

Provides multi-engine (SQL Server / PostgreSQL) connection handling,
safe execution cursors, and session termination.
"""
import logging
from contextlib import contextmanager
from typing import Dict, Tuple, Any, Generator
import pyodbc
from sqlalchemy import create_engine
from app.core.security import decrypt_data

# In-memory store for user active connections (in multi-pod setups, replace with Redis)
USER_ACTIVE_CONNECTIONS: Dict[str, str] = {}


class NoInstanceSelected(Exception):
    """Exception raised when a user executes a DBA action without selecting an instance."""
    pass


def get_remote_db_connection(dynamic_conn_str: str):
    """Establece conexión con una base de datos remota (Soporte Multimotor)."""
    conn_str = decrypt_data(dynamic_conn_str)

    try:
        # PostgreSQL detection
        if conn_str.startswith("postgresql"):
            engine = create_engine(conn_str, pool_pre_ping=True)
            return engine.raw_connection()

        # SQL Server default via pyodbc
        return pyodbc.connect(conn_str, autocommit=True, timeout=5)

    except Exception as error:
        logging.error(f"Error al conectar a la BD remota: {str(error)}")
        raise RuntimeError(str(error))


def get_active_engine_type(username: str) -> str:
    """Determine database engine type (postgres vs sqlserver)."""
    conn_str = USER_ACTIVE_CONNECTIONS.get(username, "")
    if conn_str.startswith("postgresql"):
        return "postgres"
    return "sqlserver"


def get_active_conn(username: str):
    """Retrieve raw active database connection for user."""
    conn_str = USER_ACTIVE_CONNECTIONS.get(username)
    if not conn_str:
        raise NoInstanceSelected("No hay instancia seleccionada")
    return get_remote_db_connection(conn_str)


@contextmanager
def remote_cursor(username: str) -> Generator[Tuple[Any, str], None, None]:
    """Context manager yielding (cursor, engine_type) and ensuring connection closure."""
    conn = get_active_conn(username)
    try:
        yield conn.cursor(), get_active_engine_type(username)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def kill_session(cursor: Any, engine: str, spid: int) -> None:
    """Termina una sesión remota de forma segura sin vectores de inyección."""
    if engine == "postgres":
        cursor.execute("SELECT pg_terminate_backend(%s)", (spid,))
    else:
        cursor.execute(f"KILL {int(spid)}")


def test_remote_connection(dynamic_or_plain_conn_str: str) -> Dict[str, Any]:
    """Prueba la conectividad y mide la latencia hacia un motor remoto."""
    import time
    from sqlalchemy import text
    start = time.perf_counter()
    try:
        try:
            conn_str = decrypt_data(dynamic_or_plain_conn_str)
        except Exception:
            conn_str = dynamic_or_plain_conn_str

        if conn_str.startswith("postgresql"):
            engine = create_engine(conn_str, pool_pre_ping=True)
            with engine.connect() as conn:
                res = conn.execute(text("SELECT version()")).scalar()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": True,
                "latency_ms": latency_ms,
                "engine": "PostgreSQL",
                "version": str(res).split(",")[0] if res else "PostgreSQL",
                "message": f"Conexión exitosa a PostgreSQL ({latency_ms} ms)"
            }
        else:
            conn = pyodbc.connect(conn_str, autocommit=True, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            row = cursor.fetchone()
            version = str(row[0]).split("\n")[0] if row else "SQL Server"
            conn.close()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "success": True,
                "latency_ms": latency_ms,
                "engine": "SQL Server",
                "version": version,
                "message": f"Conexión exitosa a SQL Server ({latency_ms} ms)"
            }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        err_msg = str(exc)
        return {
            "success": False,
            "latency_ms": latency_ms,
            "error": err_msg,
            "message": f"Fallo al conectar ({latency_ms} ms): {err_msg[:200]}"
        }


def get_backup_status(cursor: Any, engine: str) -> Dict[str, Any]:
    """Consulta el estado del último respaldo para las bases de datos."""
    if engine == "postgres":
        cursor.execute("""
            SELECT 
                current_database() AS database_name,
                pg_is_in_recovery() AS is_replica,
                CASE WHEN pg_is_in_recovery() THEN 'Standby / Réplica' ELSE 'Primario' END AS recovery_model,
                current_timestamp AS checked_at,
                (SELECT last_archived_time FROM pg_stat_archiver) AS last_archived_wal,
                (SELECT failed_count FROM pg_stat_archiver) AS failed_wal_count;
        """)
        row = cursor.fetchone()
        db_name = row[0] if row else "postgres"
        rec_model = row[2] if row else "Primario"
        last_wal = str(row[4]) if row and row[4] else "N/A"
        failed_cnt = row[5] if row and row[5] is not None else 0

        status_flag = "OK" if failed_cnt == 0 else "WARNING"
        return {
            "engine": "PostgreSQL",
            "summary": f"Base de Datos: {db_name} | Modo: {rec_model} | Último WAL archivado: {last_wal}",
            "databases": [
                {
                    "database_name": db_name,
                    "recovery_model": rec_model,
                    "last_full_backup": last_wal,
                    "hours_since_full": None,
                    "status": status_flag
                }
            ],
            "critical_count": 0,
            "warning_count": 1 if failed_cnt > 0 else 0
        }

    # SQL Server: Query backupset in msdb
    cursor.execute("""
        SELECT 
            d.name AS database_name,
            d.recovery_model_desc,
            CONVERT(VARCHAR(19), MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END), 120) AS last_full,
            CONVERT(VARCHAR(19), MAX(CASE WHEN b.type = 'I' THEN b.backup_finish_date END), 120) AS last_diff,
            CONVERT(VARCHAR(19), MAX(CASE WHEN b.type = 'L' THEN b.backup_finish_date END), 120) AS last_log,
            DATEDIFF(hour, MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END), GETDATE()) AS hours_since_full
        FROM sys.databases d
        LEFT JOIN msdb.dbo.backupset b ON d.name = b.database_name
        WHERE d.database_id > 4 AND d.state_desc = 'ONLINE'
        GROUP BY d.name, d.recovery_model_desc
        ORDER BY hours_since_full DESC, d.name ASC;
    """)
    rows = cursor.fetchall()
    databases = []
    critical_cnt = 0
    warning_cnt = 0

    for r in rows:
        name = r[0]
        rec = r[1]
        last_full = r[2] or "Nunca"
        last_diff = r[3] or "Nunca"
        last_log = r[4] or "Nunca"
        hours_raw = r[5]
        try:
            hours = int(hours_raw) if hours_raw is not None else None
        except (ValueError, TypeError):
            hours = None

        if hours is None or hours > 24:
            st = "CRITICAL"
            critical_cnt += 1
        elif hours > 12:
            st = "WARNING"
            warning_cnt += 1
        else:
            st = "OK"

        databases.append({
            "database_name": name,
            "recovery_model": rec,
            "last_full_backup": last_full,
            "last_diff_backup": last_diff,
            "last_log_backup": last_log,
            "hours_since_full": hours,
            "status": st
        })

    return {
        "engine": "SQL Server",
        "databases": databases,
        "critical_count": critical_cnt,
        "warning_count": warning_cnt,
        "total_databases": len(databases)
    }

