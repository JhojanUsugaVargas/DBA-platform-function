# Auditoría de SDKs y Librerías de Terceros

**Plataforma**: DataCheck Pro  
**Fecha de corte**: 2026-10-20  
**Versión de política legal**: 2026-10-20  
**Marco de referencia**: Ley 1581 de 2012 / Decreto 1377 de 2013 (Colombia)

---

## 1. Frontend

Todos los recursos externos que antes se invocaban vía CDN o llamadas a terceros (`googleapis.com`, `cdnjs`, `jsdelivr`) fueron retirados del HTML y empaquetados localmente con `npm` para garantizar soberanía de datos y evitar rastreo pasivo de direcciones IP por parte de redes de distribución externas.

| Dependencia / Paquete | Versión instalada | Propósito en el sistema | Tipo de datos procesados | Impacto en Privacidad / Medidas adoptadas | Licencia |
| :--- | :---: | :--- | :--- | :--- | :---: |
| `@angular/core`, `common`, `forms`, `router` | `^18.2.0` | Framework SPA principal de interfaz | Datos de formulario en memoria del cliente | Totalmente local; no realiza telemetría a servidores de Google. | MIT |
| `rxjs` | `~7.8.0` | Manejo de flujos reactivos | Ninguno | Ninguno | Apache 2.0 |
| `zone.js`, `tslib` | `~0.14.10`, `^2.3.0` | Polyfills y tiempo de ejecución | Ninguno | Ninguno | MIT / 0BSD |
| `chart.js` | `^4.4.4` | Renderizado de gráficos de telemetría (CPU, Esperas, Throughput) en canvas | Valores numéricos agregados de métricas | **Antes**: se cargaba por CDN (`cdn.jsdelivr.net`).<br>**Ahora**: empaquetado 100% en el bundle local sin contacto externo. | MIT |
| `gsap` | `^3.12.5` | Animaciones micro-interactivas del login y lámpara | Ninguno | **Antes**: cargado desde `cdnjs.cloudflare.com`.<br>**Ahora**: importado localmente sin transferencias externas. | GreenSock Standard License |
| `@fontsource/inter` | `^5.1.0` | Tipografía Inter autoalojada | Ninguno | **Antes**: `@import url('fonts.googleapis.com')`.<br>**Ahora**: servida estáticamente desde los archivos locales del proyecto. Cero peticiones a Google Fonts. | SIL Open Font License 1.1 |

---

## 2. Backend

| Dependencia / SDK | Propósito | Datos compartidos / Destino | Medidas de minimización aplicadas |
| :--- | :--- | :--- | :--- |
| `fastapi`, `uvicorn`, `pydantic` | Framework de API REST y validación | Tráfico HTTP local | Cabeceras de seguridad OWASP (X-Frame-Options, X-Content-Type-Options, Referrer-Policy, CSP estricto). |
| `SQLAlchemy`, `pg8000`, `pyodbc` | Conectores de base de datos relacional | Credenciales y cadenas de conexión | Cifrado simétrico AES (Fernet) de cadenas de conexión. |
| `cryptography`, `passlib`, `bcrypt`, `PyJWT` | Criptografía, hashing y tokens | Contraseñas y autenticación | Hashing unidireccional con salt (bcrypt). Tokens de desuscripción separados con propósito único. |
| `google-generativeai` | Asistente DBA con IA (Google Gemini API) | Preguntas técnicas sobre SQL | **Minimización**: Se eliminó del prompt el nombre de usuario (`username`) y correo electrónico. Solo se transmiten preguntas estrictamente técnicas. Se advierte no ingresar datos sensibles. |
| `duckduckgo-search` | Búsqueda complementaria de errores SQL en la web | Primeros 80 caracteres de la consulta técnica | Anonimización: Solo se envía la frase del error, sin identificadores de usuario ni de servidor. |
| `smtplib` (Biblioteca estándar Python) | Envío de invitaciones y códigos OTP | Correo electrónico de destino | Incorpora cabeceras RFC 8058 (`List-Unsubscribe: <URL>`, `List-Unsubscribe-Post`) y enlace directo de baja. |

---

## 3. Almacenamiento Local (Cookies / Storage Audit)

La plataforma **no instala cookies de terceros ni rastreadores analíticos**. Únicamente se utilizan elementos de `localStorage` bajo la categoría de estrictamente necesarios:

1. `access_token`: Token JWT firmado portador de sesión (caducidad configurable).
2. `datacheck_cookie_consent`: Registro de la preferencia del usuario sobre almacenamiento y versión legal auditada.
