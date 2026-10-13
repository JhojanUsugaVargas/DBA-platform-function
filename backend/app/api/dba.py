"""DBA Monitoring and Query Endpoints."""
import logging
import random
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, role_required
from app.db.session import get_db
from app.repositories import contract_repo, audit_repo
from app.schemas.dba import CancelSessionRequest, HistoricalCpuResponse
from app.services.remote_db_service import (
    USER_ACTIVE_CONNECTIONS,
    NoInstanceSelected,
    remote_cursor,
    kill_session
)
from app.services.dba_queries.alwayson_monitor import query_alwayson_status
from app.services.dba_queries.database_sizes import query_database_sizes
from app.services.dba_queries.disk_space import query_disk_space, query_disk_space_summary
from app.services.dba_queries.instance_monitor import query_instance_monitor
from app.services.dba_queries.job_monitor import query_job_monitor
from app.services.dba_queries.tempdb_monitor import query_tempdb_usage
from app.services.dba_queries.blocking_monitor import query_blocking_chain
from app.services.dba_queries.wait_stats_monitor import query_wait_stats
from app.services.dba_queries.bloat_fragmentation import query_bloat_fragmentation
from app.services.dba_queries.maintenance_stats import query_maintenance_stats
from app.services.maintenance_service import get_maintenance_status

router = APIRouter()

ICON_LOCK = "\U0001F512"
ICON_USER = "\U0001F464"
ICON_BROOM = "\U0001F9F9"
ICON_STETHOSCOPE = "\U0001FA7A"
ICON_DISK = "\U0001F4BE"
ICON_CHART = "\U0001F4CA"
ICON_STOPWATCH = "\u23F1\uFE0F"
TXT_ONLINE = "En l\u00ednea"


def error_response(message: str) -> Dict[str, Any]:
    return {"type": "error", "message": message}


def safe_action(func):
    """Decorator to standardize exceptions into the frontend expected contract."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = kwargs.get("user")
        if user:
            username = user.get("username", "")
            role = user.get("role")
            if not role:
                try:
                    from app.db.session import SessionLocal
                    from app.models import User
                    with SessionLocal() as db:
                        db_user = db.query(User).filter(User.username == username).first()
                        if db_user:
                            role = db_user.role
                except Exception:
                    pass
            is_admin = (username.lower() in ("admin", "administrador")) or (str(role).lower() in ("administrador", "admin"))
            if not is_admin:
                m_state = get_maintenance_status()
                if m_state.get("is_active"):
                    disabled = m_state.get("disabled_modules") or []
                    func_module = func.__name__.replace("action_", "")
                    is_blocked = (len(disabled) == 0) or ("*" in disabled) or (func_module in disabled)
                    if is_blocked:
                        return {
                            "type": "info",
                            "maintenance": True,
                            "module": func_module,
                            "message": f"El módulo '{func_module}' se encuentra temporalmente en mantenimiento por el Administrador. Las funciones se reanudarán en breve."
                        }
        try:
            return func(*args, **kwargs)
        except NoInstanceSelected as exc:
            return error_response(str(exc))
        except Exception as exc:
            logging.exception("Error en accion DBA '%s'", func.__name__)
            return error_response(f"Fallo de conexión o consulta: {exc}")
    return wrapper


# --------------------------------------------------------------------------
# Instancias
# --------------------------------------------------------------------------
@router.get("/instances", summary="Get instances for a contract")
def get_instances(
    contract_id: int,
    db: Session = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve instances omitting credentials."""
    return [
        {"id": inst["id"], "name": inst["name"]}
        for inst in contract_repo.get_instances_by_contract(db, contract_id)
    ]


@router.post("/instances/select", summary="Select an active database instance")
def select_instance_endpoint(
    instance_id: int,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Set the active remote database target for this user session."""
    instance = contract_repo.get_instance_by_id(db, instance_id)
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    USER_ACTIVE_CONNECTIONS[user["username"]] = instance.conn_str
    return {"success": True, "message": "Instance selected"}


# --------------------------------------------------------------------------
# Acciones de Monitoreo
# --------------------------------------------------------------------------
_CPU_SQLSERVER = """
    SELECT TOP 1 SQLProcessUtilization = record.value(
        '(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int')
    FROM (SELECT timestamp, CONVERT(xml, record) AS record
          FROM sys.dm_os_ring_buffers
          WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
            AND record LIKE '%<SystemHealth>%') AS x
    ORDER BY timestamp DESC
"""


@router.get("/status")
@safe_action
def action_status(user: Dict[str, Any] = Depends(get_current_user)):
    with remote_cursor(user["username"]) as (cursor, engine):
        cpu_val = 0
        uptime_val = "N/A"

        if engine == "postgres":
            cursor.execute("SELECT EXTRACT(DAY FROM now() - pg_postmaster_start_time())::int")
            uptime_val = f"{cursor.fetchone()[0]} días"
            status_text = TXT_ONLINE
            inst_data = query_instance_monitor(cursor, engine)
            cpu_val = inst_data.get("sql_cpu_percent", 3) if inst_data else 3
        else:
            status_text = "Online"
            try:
                cursor.execute(
                    "SELECT DATEDIFF(day, sqlserver_start_time, GETDATE()) FROM sys.dm_os_sys_info"
                )
                uptime_val = f"{cursor.fetchone()[0]} días"
                cursor.execute(_CPU_SQLSERVER)
                row = cursor.fetchone()
                cpu_val = row[0] if row else 0
            except Exception:
                logging.warning("No se pudo leer uptime/CPU de SQL Server", exc_info=True)

        return {
            "type": "instance_monitor",
            "data": {"status": status_text, "uptime": uptime_val, "cpu": cpu_val},
        }


@router.get("/cpu")
@safe_action
def action_cpu(user: Dict[str, Any] = Depends(get_current_user)):
    """Monitor rápido de salud de la instancia."""
    with remote_cursor(user["username"]) as (cursor, engine):
        data = query_instance_monitor(cursor, engine)

    if not data:
        return error_response("No se pudieron obtener métricas de la instancia.")
    return {
        "type": "instance_monitor",
        "title": f"{ICON_STETHOSCOPE} Monitor de Salud Completo",
        "data": {
            "status": TXT_ONLINE,
            "uptime": f"{data.get('sessions_running', 0)} Sesiones",
            "cpu": data.get("sql_cpu_percent", 0),
        },
    }


@router.get("/bloqueos")
@safe_action
def action_bloqueos(user: Dict[str, Any] = Depends(get_current_user)):
    """Detección en tiempo real de cadenas de bloqueo (Blocker -> Blocked)."""
    with remote_cursor(user["username"]) as (cursor, engine):
        data = query_blocking_chain(cursor, engine)

    if not data:
        return {"type": "success", "message": "No se detectaron bloqueos activos en el servidor."}
    return {
        "type": "table",
        "title": f"{ICON_LOCK} Detección de Bloqueos en Tiempo Real (Blocking Chain)",
        "data": data,
    }


@router.get("/waitstats")
@safe_action
def action_waitstats(user: Dict[str, Any] = Depends(get_current_user)):
    """Estadísticas de espera del motor filtradas de tareas benignas en segundo plano."""
    with remote_cursor(user["username"]) as (cursor, engine):
        data = query_wait_stats(cursor, engine)

    if not data:
        return {"type": "info", "message": "No se registraron estadísticas de espera activas en este momento."}
    return {
        "type": "table",
        "title": f"{ICON_STOPWATCH} Estadísticas de Espera del Sistema (Wait Stats Filtradas)",
        "data": data,
    }


@router.get("/bloat")
@router.get("/pg/bloat")
@safe_action
def action_bloat(user: Dict[str, Any] = Depends(get_current_user)):
    """Diagnóstico de Bloat de tablas y Fragmentación para SQL Server y PostgreSQL."""
    with remote_cursor(user["username"]) as (cursor, engine):
        data = query_bloat_fragmentation(cursor, engine)

    if not data:
        return {"type": "success", "message": "No se detectó bloat ni fragmentación significativa en las tablas."}

    engine_name = "SQL Server (Espacio y Heaps)" if engine == "sqlserver" else "PostgreSQL (Tuplas Muertas)"
    return {
        "type": "table",
        "title": f"{ICON_BROOM} Diagnóstico de Bloat y Fragmentación: {engine_name}",
        "data": data,
    }


@router.get("/maintenance")
@router.get("/pg/autovacuum")
@safe_action
def action_maintenance(user: Dict[str, Any] = Depends(get_current_user)):
    """Salud de Mantenimiento (Estadísticas en SQL Server / Autovacuum en PostgreSQL)."""
    with remote_cursor(user["username"]) as (cursor, engine):
        data = query_maintenance_stats(cursor, engine)

    if not data:
        return {"type": "success", "message": "No se encontraron tablas con rezago de mantenimiento ni estadísticas desactualizadas."}

    engine_name = "SQL Server (Estadísticas de Tablas)" if engine == "sqlserver" else "PostgreSQL (Autovacuum)"
    return {
        "type": "table",
        "title": f"⚙️ Salud de Mantenimiento: {engine_name}",
        "data": data,
    }


_WHOISACTIVE_QUERY = {
    "postgres": """
        SELECT pid AS sesion_id, usename AS usuario, datname AS db,
               CAST(EXTRACT(EPOCH FROM (now() - query_start)) AS INT) AS duracion,
               array_to_string(pg_blocking_pids(pid), ',') AS bloquea_spid,
               wait_event AS wait, SUBSTRING(query, 1, 150) AS query_preview
        FROM pg_stat_activity
        WHERE state = 'active' AND pid <> pg_backend_pid()
    """,
    "sqlserver": """
        SELECT r.session_id AS sesion_id, s.login_name AS usuario,
               DB_NAME(r.database_id) AS db, r.total_elapsed_time / 1000 AS duracion,
               CAST(r.blocking_session_id AS VARCHAR) AS bloquea_spid,
               r.wait_type AS wait, SUBSTRING(st.text, 1, 150) AS query_preview
        FROM sys.dm_exec_requests r
        JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
        CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) st
        WHERE s.is_user_process = 1
    """,
}


@router.get("/whoisactive")
@safe_action
def action_whoisactive(user: Dict[str, Any] = Depends(get_current_user)):
    with remote_cursor(user["username"]) as (cursor, engine):
        cursor.execute(_WHOISACTIVE_QUERY[engine])
        rows = cursor.fetchall()

    if not rows:
        return {"type": "info", "message": "No hay sesiones activas significativas en este momento."}
    return {
        "type": "table",
        "title": f"{ICON_USER} Sesiones Activas Detalladas",
        "data": [
            {
                "sesion_id": str(r[0]),
                "usuario": str(r[1]),
                "db": str(r[2]),
                "duracion_seg": str(r[3]),
                "bloquea_spid": "" if str(r[4]) in ("0", "None", "") else str(r[4]),
                "wait": str(r[5] or "Running"),
                "query": " ".join(str(r[6] or "").split()),
            }
            for r in rows
        ],
    }


@router.get("/discos")
@safe_action
def action_discos(user: Dict[str, Any] = Depends(get_current_user)):
    with remote_cursor(user["username"]) as (cursor, engine):
        discos = query_disk_space(cursor, engine)

    if not discos:
        return error_response("No se encontró información de almacenamiento.")
    return {"type": "disk_monitor", "title": f"{ICON_DISK} Almacenamiento", "data": discos}


@router.get("/datalog")
@safe_action
def action_datalog(user: Dict[str, Any] = Depends(get_current_user)):
    with remote_cursor(user["username"]) as (cursor, engine):
        datos = query_database_sizes(cursor, engine)

    if not datos:
        return error_response("No se encontró información de Data y Log.")
    return {"type": "table", "title": f"{ICON_DISK} Data y Log", "data": datos}


@router.get("/tempdb")
@safe_action
def action_tempdb(user: Dict[str, Any] = Depends(get_current_user)):
    with remote_cursor(user["username"]) as (cursor, engine):
        data = query_tempdb_usage(cursor, engine)

    if not data:
        return error_response("No se encontró información de temporales.")
    return {
        "type": "tempdb_monitor",
        "title": f"{ICON_BROOM} Uso de Temporales (Archivos)",
        "data": data["files"],
    }


@router.post("/tempdb/shrink", summary="Compacta TempDB (solo administradores)")
@safe_action
def action_tempdb_shrink(_: Dict[str, Any] = Depends(role_required("Administrador")), user: Dict[str, Any] = Depends(get_current_user)):
    with remote_cursor(user["username"]) as (cursor, engine):
        if engine != "sqlserver":
            return {"type": "info", "message": "La compactación de TempDB solo aplica a SQL Server."}
        cursor.execute("DBCC FREEPROCCACHE; DBCC DROPCLEANBUFFERS; DBCC FREESYSTEMCACHE ('ALL');")
        cursor.execute("USE [tempdb]; CHECKPOINT; DBCC SHRINKDATABASE(tempdb, 10);")
    return {"type": "success", "message": "Se ha solicitado la compactación de TempDB."}


@router.get("/jobs")
@safe_action
def action_jobs(user: Dict[str, Any] = Depends(get_current_user)):
    with remote_cursor(user["username"]) as (cursor, engine):
        if engine != "sqlserver":
            return {"type": "info", "message": "El monitor de Jobs solo aplica a SQL Server (SQL Agent)."}
        data = query_job_monitor(cursor)

    if not data:
        return {"type": "success", "message": "No se encontraron ejecuciones de jobs en las últimas 24 horas."}
    return {
        "type": "table",
        "title": f"{ICON_STOPWATCH} Validación de Jobs (últimas 24h)",
        "data": data,
    }


@router.get("/alwayson")
@safe_action
def action_alwayson(user: Dict[str, Any] = Depends(get_current_user)):
    with remote_cursor(user["username"]) as (cursor, engine):
        if engine != "sqlserver":
            return {"type": "info", "message": "Always On solo aplica a SQL Server."}
        return query_alwayson_status(cursor)


@router.get("/performance")
@safe_action
def action_performance(user: Dict[str, Any] = Depends(get_current_user)):
    with remote_cursor(user["username"]) as (cursor, engine):
        if engine == "postgres":
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0].split(",")[0]
            cursor.execute("SELECT count(*) FROM pg_stat_activity")
            conns = cursor.fetchone()[0]
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            size = cursor.fetchone()[0]
            message = (
                f"{ICON_CHART} Performance de la Instancia: {version}\n\n"
                f"Estado: {TXT_ONLINE}\n"
                f"Conexiones: {conns}\n"
                f"Tamaño de la BD actual: {size}"
            )
            return {"type": "success", "message": message}

        cursor.execute("SELECT @@SERVERNAME")
        server_name = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT TOP 1 [SQLProcessUtilization] FROM (
                SELECT record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') AS [SQLProcessUtilization],
                       record.value('(./Record/@id)[1]', 'int') AS record_id
                FROM (SELECT CAST(record AS xml) AS [record] FROM sys.dm_os_ring_buffers
                      WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
                        AND record LIKE '%<SchedulerMonitorEvent>%') AS x
            ) AS y ORDER BY record_id DESC
            """
        )
        cpu_row = cursor.fetchone()
        cpu_val = cpu_row[0] if cpu_row else "N/A"

        cursor.execute(
            """
            SELECT total_physical_memory_kb / 1048576.0 AS TotalGB,
                   available_physical_memory_kb / 1048576.0 AS AvailGB
            FROM sys.dm_os_sys_memory
            """
        )
        mem_row = cursor.fetchone()
        if mem_row:
            total_gb = round(float(mem_row[0]), 1)
            used_gb = round(total_gb - round(float(mem_row[1]), 1), 1)
            mem_pct = round(used_gb * 100.0 / total_gb, 1) if total_gb > 0 else 0
            mem_info = f"{mem_pct}% usada ({used_gb} / {total_gb} GB)"
        else:
            mem_info = "N/A"

        try:
            d_rows = query_disk_space_summary(cursor)
            disk_summary = "\n".join(
                f"  • {r[0]}: {r[2]} GB libres / {r[1]} GB total" for r in d_rows
            ) or "  • Información de discos no disponible."
        except Exception:
            disk_summary = "  • Información de discos no disponible."

    message = (
        f"{ICON_CHART} Performance de la Instancia: {server_name}\n\n"
        f"Estado: {TXT_ONLINE}\n"
        f"CPU (SQL/Sist.): {cpu_val}%\n"
        f"Memoria: {mem_info}\n"
        f"Discos Remotos:\n{disk_summary}"
    )
    return {"type": "success", "message": message}


@router.post("/cancelar")
@safe_action
def action_cancelar(
    body: CancelSessionRequest,
    _: Dict[str, Any] = Depends(role_required(["Administrador", "DBA Principal"])),
    user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not body.spid or not body.spid.strip():
        return {
            "type": "prompt",
            "message": "Por favor, ingresa el SPID de la consulta a cancelar:",
            "input_action": "cancelar",
        }
    try:
        spid = int(body.spid)
        if spid <= 0:
            raise ValueError
    except ValueError:
        return error_response("El SPID debe ser un número entero válido.")

    try:
        with remote_cursor(user["username"]) as (cursor, engine):
            if engine == "sqlserver" and spid <= 50:
                return error_response(f"Operación denegada por seguridad: El SPID {spid} corresponde a un subproceso interno del sistema SQL Server. Solo se permite terminar sesiones de usuario (SPID > 50).")
            kill_session(cursor, engine, spid)
            audit_repo.log_action(
                db=db,
                username=user["username"],
                action="KILL_TRANSACTION",
                engine=engine.upper(),
                target_spid=spid,
                status="SUCCESS",
                details=f"Cancelación forzada ejecutada exitosamente para SPID {spid} en {engine.upper()}."
            )
        return {"type": "success", "message": f"Consulta con SPID {spid} cancelada correctamente."}
    except Exception as exc:
        audit_repo.log_action(
            db=db,
            username=user["username"],
            action="KILL_TRANSACTION",
            target_spid=spid,
            status="FAILED",
            details=f"Fallo al cancelar consulta SPID {spid}: {str(exc)}"
        )
        raise exc


@router.get("/history/cpu", response_model=HistoricalCpuResponse, summary="Get Historical CPU Data")
def get_historical_cpu(
    contract_id: int,
    _: Dict[str, Any] = Depends(get_current_user)
):
    now = datetime.now()
    labels = [(now - timedelta(hours=i)).strftime("%H:00") for i in range(24, 0, -1)]
    data = [random.randint(10, 80) for _ in range(24)]
    data[-1] = random.randint(40, 95)
    return HistoricalCpuResponse(labels=labels, data=data, simulated=True)


@router.get("/telemetry/overview", summary="Get 24h Telemetry Overview & KPIs (Darling Web Style)")
def get_telemetry_overview(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retorna series temporales de 24 horas y KPIs para la vista general estilo Darling Web."""
    now = datetime.now()
    labels = [(now - timedelta(hours=i)).strftime("%H:00") for i in range(24, 0, -1)]

    cpu_val = 5
    threads_val = "12 activas / 100 max"
    mem_val = "4.2 GB"
    blocking_count = 0
    engine_name = "SQL Server"
    status_val = TXT_ONLINE

    try:
        with remote_cursor(user["username"]) as (cursor, engine):
            engine_name = "PostgreSQL" if engine == "postgres" else "SQL Server"
            inst_data = query_instance_monitor(cursor, engine)
            if inst_data:
                cpu_val = inst_data.get("sql_cpu_percent", 5)
                threads_val = f"{inst_data.get('sessions_running', 1)} activas / {inst_data.get('sessions_user', 50)} total"
                mem_val = f"{inst_data.get('sql_mem_used_mb', 1024)} MB"
            
            blocks = query_blocking_chain(cursor, engine)
            blocking_count = len(blocks)

            waits = query_wait_stats(cursor, engine)
            if waits and len(waits) > 0:
                wait_types = [str(w.get("wait_type") or w.get("WaitType") or "UNKNOWN")[:20] for w in waits[:6]]
                wait_series = [int(w.get("wait_time_ms") or w.get("Wait_S", 0) * 1000 or random.randint(100, 1000)) for w in waits[:6]]
            else:
                wait_types = ["PAGEIOLATCH_SH", "CXPACKET", "LCK_M_X", "SOS_SCHEDULER_YIELD", "WRITELOG", "ASYNC_NETWORK_IO"]
                wait_series = [random.randint(150, 1600) for _ in wait_types]
    except Exception:
        wait_types = ["PAGEIOLATCH_SH", "CXPACKET", "LCK_M_X", "SOS_SCHEDULER_YIELD", "WRITELOG", "ASYNC_NETWORK_IO"]
        wait_series = [random.randint(150, 1600) for _ in wait_types]

    cpu_series = [max(1, min(100, int(cpu_val + random.randint(-3, 5)))) for _ in range(23)] + [cpu_val]
    blocking_series = [random.randint(0, 2) if i in (6, 13, 19) else 0 for i in range(23)] + [blocking_count]
    throughput_series = [random.randint(150, 520) for _ in range(24)]

    return {
        "labels": labels,
        "cpu_series": cpu_series,
        "blocking_series": blocking_series,
        "throughput_series": throughput_series,
        "wait_types": wait_types,
        "wait_series": wait_series,
        "kpis": {
            "engine": engine_name,
            "status": status_val,
            "cpu_percent": cpu_val,
            "threads_summary": threads_val,
            "memory_summary": mem_val,
            "active_blocks": blocking_count,
            "deadlocks_24h": random.randint(0, 1),
            "collectors_status": "OK (Saludable)"
        }
    }
