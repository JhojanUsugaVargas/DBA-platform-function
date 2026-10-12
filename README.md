# 🚀 DataCheck Platform

Plataforma empresarial de monitoreo, telemetría y gestión inteligente de bases de datos (SQL Server / PostgreSQL) con asistente DBA potenciado por IA (Google Gemini).

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

---

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

El backend incluye una suite de pruebas unitarias sobre hashing de contraseñas, validación JWT, cifrado Fernet y repositorios:

```bash
cd backend
python -m unittest tests/test_api.py
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

## 🔒 Buenas Prácticas de Seguridad Implementadas

1. **Gestión de Secretos**: Ninguna credencial, clave de correo o contraseña sensible se encuentra en el código fuente. Todas se cargan mediante variables de entorno (`.env` o Kubernetes Secrets).
2. **Cifrado Simétrico**: Las cadenas de conexión de bases de datos remotas se almacenan cifradas con `Fernet` de forma unificada.
3. **Autenticación y Autorización**: Contraseñas hasheadas con `bcrypt`, sesiones controladas con tokens `JWT (HS256)` y doble factor de autenticación (`OTP`).
4. **Protección de Red**: CORS configurado explícitamente y validación de endpoints protegidos mediante `Depends(get_current_user)` y `role_required`.