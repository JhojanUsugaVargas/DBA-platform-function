# 🚀 DataCheck Platform (v2.6.0)

Plataforma empresarial de monitoreo, telemetría y gestión inteligente de bases de datos (SQL Server / PostgreSQL) con asistente DBA potenciado por IA (Google Gemini), cumplimiento de privacidad (Ley 1581 de 2012 / Habeas Data) y estándares de accesibilidad WCAG 2.1 AA.

---

## 🏗️ Arquitectura del Sistema

El proyecto está diseñado bajo una arquitectura desacoplada y moderna que separa completamente el **Backend** y el **Frontend**, siguiendo principios de diseño limpio (*Clean/Layered Architecture*), separación de responsabilidades y tipado estricto.

```
DataCheck-web/
├── backend/                  # API REST con FastAPI (Python 3.12+)
│   ├── app/
│   │   ├── api/              # Routers de FastAPI agrupados por dominio (/auth, /admin, /dba, /chat, /feedback)
│   │   ├── core/             # Configuración central (Pydantic), seguridad (JWT/bcrypt/Fernet), dependencias
│   │   ├── db/               # Sesión de base de datos SQLAlchemy, inicialización y seeding
│   │   ├── models/           # Modelos ORM (User, Contract, Instance, ChatMessage, Feedback)
│   │   ├── repositories/     # Capa de acceso a datos (patrón Repository)
│   │   ├── schemas/          # Esquemas de validación y serialización Pydantic
│   │   ├── services/         # Lógica de negocio (IA Gemini, telemetría DBA, correo OTP, tickets)
│   │   └── main.py           # Punto de entrada de la aplicación FastAPI y ciclo de vida (lifespan)
│   ├── tests/                # Suite de pruebas unitarias automatizadas (unittest)
│   ├── Dockerfile            # Imagen Docker optimizada para producción (python:3.12-slim)
│   ├── requirements.txt      # Dependencias versionadas
│   └── smoke_test.py         # Script de pruebas de humo sobre endpoints activos
│
├── frontend/                 # Single Page Application con Angular 18 (TypeScript)
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/         # Modelos TS, servicios HTTP, interceptores funcionales y guards
│   │   │   │   ├── guards/          # AuthGuard para control de rutas protegidas
│   │   │   │   ├── interceptors/   # AuthInterceptor funcional (JWT Bearer token)
│   │   │   │   ├── models/          # Interfaces TypeScript compartidas
│   │   │   │   └── services/        # AuthService, ApiService, DbaService, ChatService
│   │   │   ├── components/   # Componentes UI (Login, Dashboard interactivo con telemetría)
│   │   │   ├── app.config.ts # Configuración Standalone (HTTP con interceptores, routing)
│   │   │   └── app.routes.ts # Rutas declaradas con protección de sesión
│   │   └── environments/     # Configuración por entorno (dev / prod)
│   ├── Dockerfile            # Construcción multi-etapa (Node 20 + Nginx Alpine)
│   ├── nginx.conf            # Configuración Nginx para soporte SPA y compresión gzip
│   └── package.json          # Dependencias y scripts de Angular CLI
│
├── k8s/                      # Manifiestos de despliegue para Kubernetes
│   ├── deployment.yaml       # Deployment con probes /healthz y gestión de recursos
│   ├── service.yaml          # Servicio expuesto (LoadBalancer / ClusterIP)
│   ├── configmap.yaml        # ConfigMap para variables de entorno no sensibles
│   └── secrets.example.yaml  # Plantilla de secretos (Base64) sin credenciales reales
│
├── .env.example              # Plantilla documentada de variables de entorno
├── docker-compose.yml        # Orquestación completa (PostgreSQL + FastAPI + Angular)
├── Jenkinsfile               # Pipeline de integración y despliegue continuo (CI/CD)
└── start.ps1                 # Script PowerShell para iniciar ambos servicios en desarrollo local
```

## 🌐 Estructura y Diagrama de la Página Web (Frontend Architecture)

A continuación se ilustra la arquitectura de navegación, jerarquía de vistas, componentes y capas de la interfaz de usuario de **DataCheck Pro**:

```mermaid
flowchart TD
    %% Estilos de Nodos
    classDef root fill:#00e5ff,stroke:#0099cc,stroke-width:2px,color:#000,font-weight:bold;
    classDef page fill:#131c2e,stroke:#00e5ff,stroke-width:1.5px,color:#fff;
    classDef module fill:#1e293b,stroke:#38bdf8,stroke-width:1px,color:#e2e8f0;
    classDef modal fill:#2e1065,stroke:#a855f7,stroke-width:1.5px,color:#f3e8ff;
    classDef maint fill:#451a03,stroke:#f59e0b,stroke-width:1.5px,color:#fef3c7;
    classDef guard fill:#052e16,stroke:#22c55e,stroke-width:1.5px,color:#dcfce7;

    %% Flujo de Acceso
    A[🔑 Login Page / /login] -->|JWT Auth Success| G{🛡️ AuthGuard}
    G -->|Token Válido| B[🏠 Dashboard Principal / /dashboard]
    G -->|Admin Exclusivo| INC_PAGE[🎫 Portal de Incidentes & Req. / /admin/incidents]

    %% Estructura de la Página Principal
    subgraph LAYOUT["🖥️ Dashboard Layout (Home)"]
        direction TB
        B --> TOP["⚡ Barra Superior (Header & KPIs)"]
        B --> SIDEBAR["📑 Panel Lateral (Sidebar de Navegación)"]
        B --> MAIN_VIEW["📊 Vista Principal de Telemetría y Diagnóstico"]
        B --> AI_CHAT["🤖 Asistente DBA Flotante (Google Gemini AI)"]
        B --> MAINT_LAYER["🛠️ Capa de Mantenimiento y Control"]
    end

    %% Barra Superior
    subgraph TOP_BAR["⚡ Header & KPIs Bar"]
        TOP --> T1["📈 Tiras KPI en Tiempo Real (CPU, Conexiones, Buffer, Deadlocks)"]
        TOP --> T2["🔄 Refrescar Telemetría"]
        TOP --> T3["📄 Exportar Reporte a PDF"]
        TOP --> T4["ℹ️ Modal 'Acerca de DataCheck Pro'"]
        TOP --> T5["⭐ Feedback y Calificaciones"]
        TOP --> T6["🛠️ Botón Mantenimiento DBA (Con Temporizador)"]
    end

    %% Panel Lateral (Sidebar)
    subgraph SIDEBAR_NAV["📑 Panel Lateral (Jerarquía & Módulos)"]
        SIDEBAR --> S_HIERARCHY["🏢 Selector de Contratos & Instancias"]
        S_HIERARCHY --> MOD_CONTRACT["➕/✏️/🗑️ Modal CRUD Contratos"]
        S_HIERARCHY --> MOD_INSTANCE["➕ Modal Registro Instancias (SQL Server / PG)"]

        SIDEBAR --> S_ACTIONS["⚡ Acciones Rápidas & Telemetría"]
        S_ACTIONS --> M1["📊 Telemetría 24h (Overview)"]
        S_ACTIONS --> M2["⚡ Monitor de Salud & CPU"]
        S_ACTIONS --> M3["⏱️ Estadísticas de Espera"]
        S_ACTIONS --> M4["🔒 Análisis de Bloqueos"]
        S_ACTIONS --> M5["🧹 Bloat y Fragmentación"]
        S_ACTIONS --> M6["⚙️ Salud Mantenimiento"]
        S_ACTIONS --> M7["💾 Almacenamiento & Discos"]
        S_ACTIONS --> M8["🗂️ Uso de TempDB"]
        S_ACTIONS --> M9["👤 Sesiones Activas (WhoIsActive)"]
        S_ACTIONS --> M10["📋 Estado de Jobs"]
        S_ACTIONS --> M11["🔗 Nodos AlwaysOn"]
        S_ACTIONS --> M12["📈 Performance General"]
        S_ACTIONS --> M13["🔍 Validar Data y Log"]
        S_ACTIONS --> M14["❌ Forzar Cancelación (Kill - DBA Pral & Admin)"]

        SIDEBAR --> S_ADMIN["👥 Configuración & Gobernanza"]
        S_ADMIN --> MOD_AUDIT["📋 Modal Registro de Auditoría Inmutable"]
        S_ADMIN --> MOD_USERS["👥 Modal Gestión de Usuarios (CRUD, Invitar, Clave)"]
        S_ADMIN --> MOD_INCIDENTS["🎫 Acceso a Mesa de Incidentes & Requerimientos"]
        S_ADMIN --> MOD_PROFILE["👤 Modal Perfil & Seguridad MFA"]
    end

    %% Capa de Mantenimiento
    subgraph MAINTENANCE["🛠️ Capa de Mantenimiento & Temporizador"]
        MAINT_LAYER --> ML_GLOBAL["🛑 Bloqueo Total (Overlay Cyber Pantalla Completa)"]
        MAINT_LAYER --> ML_PARTIAL["⚠️ Banner Mantenimiento Modular (Botones específicos en ajuste)"]
        MAINT_LAYER --> ML_TIMER["⏱️ Temporizador Digital en Vivo (HH:MM:SS)"]
        MAINT_LAYER --> ML_CONFIG["⚙️ Modal Configuración de Mantenimiento (Admin)"]
    end

    %% Asignación de Estilos
    class A,B,INC_PAGE root;
    class G guard;
    class T1,T2,T3,T4,T5,T6,M1,M2,M3,M4,M5,M6,M7,M8,M9,M10,M11,M12,M13,M14 module;
    class MOD_CONTRACT,MOD_INSTANCE,MOD_AUDIT,MOD_USERS,MOD_INCIDENTS,MOD_PROFILE,ML_CONFIG modal;
    class ML_GLOBAL,ML_PARTIAL,ML_TIMER maint;
```

### 👥 Matriz de Roles y Permisos (RBAC)

| Módulo / Acción | Administrador | DBA Principal | Monitor |
| :--- | :---: | :---: | :---: |
| **Monitoreo & Telemetría en Vivo** | ✅ | ✅ | ✅ |
| **Consultas de Diagnóstico (CPU, Discos, TempDB, etc.)** | ✅ | ✅ | ✅ |
| **Forzar Cancelación de Consultas (`KILL` / `pg_terminate_backend`)** | ✅ | ✅ | ❌ *(Bloqueado)* |
| **Portal de Gestión de Incidentes y Requerimientos** | ✅ | ❌ | ❌ |
| **Gestión de Usuarios & Invitaciones por Correo** | ✅ | ❌ | ❌ |
| **Configuración de Ventana de Mantenimiento Global** | ✅ | ❌ | ❌ |
| **Registro y Eliminación de Instancias/Contratos** | ✅ | ❌ | ❌ |

### 🧩 Desglose de Componentes y Funcionalidades

| Componente / Módulo | Tipo | Responsabilidad / Descripción |
| :--- | :--- | :--- |
| **`LoginComponent`** | Página | Acceso seguro con credenciales, validación JWT y opción de doble factor (`OTP/MFA`). |
| **`DashboardComponent`** | Página / Hub | Contenedor principal de telemetría reactiva, visualización gráfica y gestión DBA. |
| **`IncidentManagementComponent`** | Página / Portal Admin | **Nueva Mesa de Control de Incidentes y Requerimientos (`/admin/incidents`)**. Permite a los administradores registrar, filtrar por prioridad/tipo, asignar, añadir notas técnicas del agente y resolver solicitudes operativas sin tocar la base de datos directamente. |
| **`Top Header & KPIs Strip`** | Componente UI | Barra superior con métricas críticas en vivo (CPU %, hilos de conexión, memoria buffer y deadlocks 24h). |
| **`Sidebar Hierarchy`** | Navegación | Gestión jerárquica con selectors de contratos clientes e instancias de BD registradas. |
| **`Quick Actions Grid`** | Control | 13 botones de diagnóstico directo que consultan DMVs de SQL Server y catálogos de PostgreSQL. |
| **`Performance Charts`** | Visualización | 4 paneles con gráficos interactivos (`Chart.js`) para CPU, esperas, contención de bloqueos y throughput. |
| **`AI Chat Widget`** | Asistente Flotante | Asistente conversacional DBA impulsado por Google Gemini con soporte de búsqueda en tiempo real e historial persistente. |
| **`Cyber Maintenance Overlay`** | Capa de Seguridad | Bloqueo animado de pantalla completa con temporizador digital activo para ventanas de mantenimiento globales. |
| **`Partial Maintenance Banner`** | Capa de Seguridad | Cinta informativa y deshabilitación visual (`⚙️ En ajuste`) de botones específicos cuando se modifican módulos individuales. |
| **`Maintenance Config Modal`** | Modal Admin | Panel para configurar ventanas de mantenimiento (Bloqueo Total vs. Modular) y elegir qué botones restringir. |
| **`User Management Modal`** | Modal Admin | Administración completa de usuarios (creación, asignación de roles, invitaciones automáticas por correo y restablecimiento de contraseña). |
| **`Audit Logs Modal`** | Modal Admin | Visor de pistas de auditoría inmutables para monitorear acciones críticas realizadas en el sistema. |
| **`About Project Modal`** | Modal Informativo | Ficha técnica del sistema (DataCheck Pro v2.6.0, arquitectura, versiones del stack y autoría). |
| **`LegalPageComponent`** | Página Pública | Portal legal accesible en `/legal/:slug` (`privacidad`, `terminos`, `cookies`, `licencias`) con soporte para impresión y lectura accesible. |
| **`CookieBannerComponent`** | Diálogo Global | Centro de consentimiento de cookies conforme a privacidad; sin patrones oscuros, opciones equitativas de aceptación/rechazo y configuración técnica/analítica. |

## 🛠️ Requisitos Previos

- **Python**: 3.11 o superior
- **Node.js**: v20 o superior y npm
- **Docker & Docker Compose** (opcional, para despliegue contenerizado)
- **ODBC Driver**: Si se conecta a instancias remotas de Microsoft SQL Server (MS ODBC 17 o 18)

---

## ⚙️ Configuración del Entorno (.env)

Copia el archivo `.env.example` en la raíz del proyecto como `.env`:

```bash
cp .env.example .env
```

Configura tus credenciales y parámetros clave:

| Variable | Descripción | Valor por defecto / Ejemplo |
| :--- | :--- | :--- |
| `SECRET_KEY` | Clave secreta para firmar tokens JWT | *Generar con openssl rand -hex 32* |
| `FERNET_KEY` | Clave simétrica para encriptar cadenas de conexión | *Clave Fernet de 32 bytes base64* |
| `DATABASE_URL` | Cadena de conexión SQLAlchemy principal | `postgresql+pg8000://user:pass@localhost:5432/dbname` |
| `GEMINI_API_KEY` | Llave de API para el asistente Google Gemini | *Tu API Key de Google AI* |
| `SMTP_USER` / `SMTP_PASSWORD` | Correo y contraseña de aplicación para envío de OTP | *Credenciales SMTP* |
| `CORS_ORIGINS` | Orígenes HTTP permitidos para el Frontend | `http://localhost:4200,http://localhost:8005` |
| `DATA_CONTROLLER_NAME` | Razón social responsable del tratamiento de datos | `DataCheck Platform` |
| `PRIVACY_CONTACT_EMAIL` | Correo oficial de atención al titular (Habeas Data) | `privacidad@datacheck.internal` |
| `LEGAL_VERSION` | Versión vigente de términos y política de privacidad | `2026.1` |
| `FRONTEND_URL` | URL pública base del Frontend (enlaces en correos) | `http://localhost:4200` |
| `PUBLIC_API_URL` | URL pública base del Backend (enlaces de baja RFC 8058) | `http://localhost:8000` |
| `UNSUBSCRIBE_TOKEN_EXPIRE_DAYS` | Vigencia en días del enlace de desuscripción de correo | `180` |

---

## 💻 Desarrollo Local

### Opción 1: Inicio Rápido con PowerShell (Windows)

Ejecuta el script unificado que arranca tanto el Backend (`:8005`) como el Frontend (`:4200`) en ventanas independientes:

```powershell
.\start.ps1
```

Para detener todos los servicios y procesos huérfanos:

```powershell
.\start.ps1 -Stop
```

### Opción 2: Inicio Manual

#### 1. Backend (FastAPI)
```bash
cd backend
python -m venv venv
# Activar entorno (Windows: .\venv\Scripts\activate | Linux: source venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8005 --reload
```
- Documentación Swagger interactiva: [http://127.0.0.1:8005/docs](http://127.0.0.1:8005/docs)
- Documentación ReDoc: [http://127.0.0.1:8005/redoc](http://127.0.0.1:8005/redoc)
- Health check: [http://127.0.0.1:8005/healthz](http://127.0.0.1:8005/healthz)

#### 2. Frontend (Angular)
```bash
cd frontend
npm install
npx ng serve --port 4200
```
- Aplicación Web: [http://localhost:4200](http://localhost:4200)

---

## 🧪 Pruebas Automatizadas

El backend incluye suites de pruebas unitarias sobre hashing de contraseñas, validación JWT, cifrado Fernet, cumplimiento de privacidad y repositorios:

```bash
cd backend
# Pruebas de API y seguridad
python -m unittest tests/test_api.py

# Pruebas integrales de Privacidad, Consentimiento, Desuscripción y Eliminación (Habeas Data)
python -m unittest tests/test_privacy.py

# Suite completa QA
python -m unittest tests/test_full_qa.py
```

Para ejecutar pruebas de humo sobre la API en ejecución:
```bash
cd backend
python smoke_test.py
```

---

## 🐳 Despliegue con Docker Compose

Puedes levantar toda la pila (Base de datos PostgreSQL + Backend FastAPI + Frontend Angular Nginx) en un solo comando:

```bash
docker compose up -d --build
```

- Frontend accesible en: `http://localhost:4200`
- Backend API accesible en: `http://localhost:8005`
- PostgreSQL accesible en: `localhost:5432`

---

## ☸️ Despliegue en Kubernetes (k8s)

1. Crear el ConfigMap:
   ```bash
   kubectl apply -f k8s/configmap.yaml
   ```
2. Crear los Secretos a partir de la plantilla:
   ```bash
   # Genera tu secrets.yaml a partir de k8s/secrets.example.yaml con tus valores base64
   kubectl apply -f k8s/secrets.yaml
   ```
3. Desplegar la aplicación y servicio:
   ```bash
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   ```

---

## 🔒 Buenas Prácticas de Seguridad y Cumplimiento Implementadas

1. **Gestión de Secretos**: Ninguna credencial, clave de correo o contraseña sensible se encuentra en el código fuente. Todas se cargan mediante variables de entorno (`.env` o Kubernetes Secrets).
2. **Cifrado Simétrico**: Las cadenas de conexión de bases de datos remotas se almacenan cifradas con `Fernet` de forma unificada.
3. **Autenticación y Autorización**: Contraseñas hasheadas con `bcrypt`, sesiones controladas con tokens `JWT (HS256)` y doble factor de autenticación (`OTP`).
4. **Protección de Red**: CORS configurado explícitamente y validación de endpoints protegidos mediante `Depends(get_current_user)` y `role_required`.
5. **Privacidad y Habeas Data (Ley 1581 de 2012)**:
   - Trazabilidad y versionamiento del consentimiento del titular (`consent_version`, `consent_accepted_at`).
   - Derecho de Portabilidad: Endpoint `/auth/profile/export` con descarga completa en JSON de perfil, chats y auditoría.
   - Derecho de Supresión: Endpoint `/auth/profile/delete-account` con borrado en cascada seguro y anonimización de eventos de auditoría (`usuario-eliminado-<hash>`).
   - Minimización de datos: Eliminación de PII (nombres de usuario) en consultas externas hacia IA (Gemini) y eliminación de correos en texto plano de logs de auditoría.
6. **Desuscripción de Correos (RFC 8058)**: Cabeceras `List-Unsubscribe` y `List-Unsubscribe-Post` en correos transaccionales con tokens HMAC firmados de un solo clic.
7. **Accesibilidad Web (WCAG 2.1 AA)**:
   - Navegación completa por teclado con indicador `:focus-visible` de alto contraste y tecla `Escape` para cerrar modales.
   - Enlace directo al contenido principal (*skip link*).
   - Ratios de contraste optimizados sobre tema dark cyber (texto secundario `#8f8f9a`, bordes y botones).
   - Textos alternativos descriptivos en gráficos (`role="img"`, `aria-label`), avatar y componentes interactivos.
8. **Soberanía y Seguridad de Activos**:
   - Sin dependencias de CDNs externas (`Chart.js`, `GSAP` y tipografía `@fontsource/inter` empaquetadas localmente).
   - Content-Security-Policy (CSP) estricto en Nginx (`script-src 'self'`, `font-src 'self'`, `style-src 'self' 'unsafe-inline'`).
   - Declaración de titularidad de derechos en carga de fotos de perfil.