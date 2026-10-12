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
