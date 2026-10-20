import { environment } from '../../../environments/environment';

export type LegalBlock =
  | { type: 'p'; text: string }
  | { type: 'h3'; text: string }
  | { type: 'ul'; items: string[] }
  | { type: 'table'; head: string[]; rows: string[][] };

export interface LegalDoc {
  slug: string;
  title: string;
  summary: string;
  blocks: LegalBlock[];
}

const L = environment.legal;
const CONTACT = L.privacyEmail;
const CONTROLLER = L.controllerName;

export const LEGAL_VERSION = L.version;

const PRIVACY: LegalDoc = {
  slug: 'privacidad',
  title: 'Política de Privacidad y Tratamiento de Datos Personales',
  summary: 'Qué datos tratamos, para qué, con quién los compartimos y cómo ejercer tus derechos (Ley 1581 de 2012).',
  blocks: [
    { type: 'h3', text: '1. Responsable del tratamiento' },
    { type: 'p', text: `${CONTROLLER} es el responsable del tratamiento de los datos personales recolectados en DataCheck Pro, conforme a la Ley 1581 de 2012, el Decreto 1377 de 2013 (compilado en el Decreto 1074 de 2015) y demás normas de protección de datos de Colombia. Contacto para temas de privacidad: ${CONTACT}.` },

    { type: 'h3', text: '2. Datos que recolectamos' },
    { type: 'table', head: ['Dato', 'Origen', 'Obligatorio'], rows: [
      ['Nombre de usuario, nombre completo, rol', 'Lo registra el administrador al crear tu cuenta', 'Sí'],
      ['Contraseña (guardada solo como hash bcrypt, nunca en texto plano)', 'Tú o el administrador', 'Sí'],
      ['Correo electrónico', 'Administrador, para invitación y códigos de verificación (MFA)', 'No'],
      ['Foto de perfil', 'La subes tú', 'No'],
      ['Mensajes enviados al asistente DBA', 'Los escribes tú en el chat', 'No'],
      ['Calificaciones, comentarios y tickets', 'Los escribes tú', 'No'],
      ['Registro de auditoría (acción, fecha, instancia, resultado)', 'Generado por el sistema al realizar acciones administrativas', 'Sí, por seguridad'],
      ['Evidencia de tu autorización (versión de documentos y fecha de aceptación)', 'Generado cuando aceptas estos documentos', 'Sí'],
    ] },
    { type: 'p', text: 'No recolectamos datos sensibles (salud, biometría, origen étnico, orientación política, etc.), ni datos de menores de edad. La plataforma no está dirigida a menores.' },
    { type: 'p', text: 'La telemetría de las bases de datos monitoreadas (CPU, bloqueos, sesiones activas) es información técnica de las instancias. Puede incluir nombres de inicio de sesión de bases de datos; solo se muestra a usuarios autorizados y no se usa para fines distintos al diagnóstico.' },

    { type: 'h3', text: '3. Finalidades' },
    { type: 'ul', items: [
      'Crear y administrar tu cuenta y controlar el acceso según tu rol.',
      'Verificar tu identidad (inicio de sesión y código de verificación MFA).',
      'Prestar el servicio de monitoreo y el asistente DBA.',
      'Gestionar incidentes, requerimientos y comentarios.',
      'Mantener un registro de auditoría para seguridad y trazabilidad.',
      'Enviarte la invitación a la plataforma y comunicaciones de seguridad indispensables.',
    ] },
    { type: 'p', text: 'No vendemos tus datos ni los usamos para publicidad ni para perfilamiento comercial.' },

    { type: 'h3', text: '4. Autorización' },
    { type: 'p', text: 'Tratamos tus datos con tu autorización previa, expresa e informada. La das al aceptar estos documentos (queda registrada la versión y la fecha) y en los formularios que recogen datos opcionales mediante una casilla que tú marcas, nunca premarcada. Puedes revocarla en cualquier momento eliminando tu cuenta desde tu perfil o escribiendo a ' + CONTACT + '.' },

    { type: 'h3', text: '5. Terceros y transferencias' },
    { type: 'table', head: ['Tercero', 'Qué recibe', 'Para qué'], rows: [
      ['Google (Gemini API), Estados Unidos', 'El texto de tu pregunta al asistente. No enviamos tu nombre de usuario ni tu correo', 'Generar respuestas del asistente DBA'],
      ['Buscador web (DuckDuckGo/Bing)', 'Los primeros 80 caracteres de preguntas técnicas, como consulta de búsqueda', 'Complementar respuestas del asistente'],
      ['Proveedor SMTP de correo', 'Tu correo y el contenido del mensaje', 'Enviar invitaciones y códigos de verificación'],
    ] },
    { type: 'p', text: 'Por eso te pedimos no escribir en el chat contraseñas, cadenas de conexión ni datos personales de terceros. Algunos de estos proveedores están fuera de Colombia, lo que implica transferencia internacional de datos con las garantías contractuales de cada proveedor.' },

    { type: 'h3', text: '6. Conservación' },
    { type: 'ul', items: [
      'Tu cuenta, foto, historial de chat y comentarios se conservan mientras tu cuenta esté activa y se eliminan cuando la eliminas.',
      'El registro de auditoría puede conservarse de forma anonimizada (sin tu nombre, usuario ni correo) mientras sea necesario para seguridad y obligaciones legales.',
    ] },

    { type: 'h3', text: '7. Tus derechos como titular' },
    { type: 'p', text: 'Conforme al artículo 8 de la Ley 1581 de 2012 puedes:' },
    { type: 'ul', items: [
      'Conocer, actualizar y rectificar tus datos.',
      'Solicitar prueba de la autorización otorgada.',
      'Ser informado sobre el uso que se ha dado a tus datos.',
      'Revocar la autorización y solicitar la supresión de tus datos.',
      'Acceder gratuitamente a tus datos personales.',
      'Presentar quejas ante la Superintendencia de Industria y Comercio (SIC) tras agotar el trámite ante el responsable.',
    ] },
    { type: 'p', text: 'Cómo ejercerlos: desde la aplicación, en tu perfil, puedes descargar todos tus datos y eliminar tu cuenta. También puedes escribir a ' + CONTACT + '. Las consultas se responden en máximo 10 días hábiles y los reclamos en máximo 15 días hábiles (artículos 14 y 15 de la Ley 1581).' },

    { type: 'h3', text: '8. Seguridad' },
    { type: 'p', text: 'Aplicamos contraseñas con hash bcrypt, tokens firmados, cifrado de cadenas de conexión (Fernet), control de acceso por roles, bloqueo ante intentos fallidos, cabeceras de seguridad HTTP y registro de auditoría. Ningún sistema es infalible; si ocurre un incidente que afecte tus datos, te informaremos conforme a la ley.' },

    { type: 'h3', text: '9. Correos electrónicos' },
    { type: 'p', text: 'Los correos informativos incluyen un enlace para darte de baja con un solo clic, y puedes cambiar esta preferencia desde tu perfil. Los mensajes de seguridad indispensables (por ejemplo, el código de verificación MFA cuando lo activas) se siguen enviando porque son necesarios para el servicio.' },

    { type: 'h3', text: '10. Cambios a esta política' },
    { type: 'p', text: `Si cambiamos esta política de forma relevante, actualizaremos su versión y te pediremos aceptarla de nuevo. Versión vigente: ${LEGAL_VERSION}.` },
  ]
};

const TERMS: LegalDoc = {
  slug: 'terminos',
  title: 'Términos y Condiciones de Uso',
  summary: 'Reglas para usar DataCheck Pro, responsabilidades y límites del servicio.',
  blocks: [
    { type: 'h3', text: '1. Aceptación' },
    { type: 'p', text: `Al usar DataCheck Pro aceptas estos términos y la Política de Privacidad. ${CONTROLLER} presta el servicio. Si no estás de acuerdo, no uses la plataforma; puedes eliminar tu cuenta desde tu perfil.` },

    { type: 'h3', text: '2. Cuentas y roles' },
    { type: 'ul', items: [
      'Las cuentas las crea un administrador y tienen un rol (Administrador, DBA Principal o Monitor) que define qué puedes hacer.',
      'Eres responsable de la confidencialidad de tu contraseña y de lo que se haga con tu cuenta. Cambia la contraseña inicial en tu primer acceso.',
      'Avísanos de inmediato si sospechas un acceso no autorizado.',
    ] },

    { type: 'h3', text: '3. Uso aceptable' },
    { type: 'ul', items: [
      'Usa la plataforma solo para administrar y monitorear bases de datos sobre las que tengas autorización.',
      'Las acciones críticas (por ejemplo, cancelar sesiones con KILL) quedan registradas en auditoría con tu usuario.',
      'No intentes eludir controles de seguridad, sobrecargar el servicio ni acceder a datos de otros usuarios.',
      'No ingreses en el chat contraseñas, cadenas de conexión ni datos personales de terceros.',
    ] },

    { type: 'h3', text: '4. Conexiones a bases de datos' },
    { type: 'p', text: 'Al registrar una instancia declaras tener autorización para conectarte a ella y monitorearla. Las cadenas de conexión se almacenan cifradas. Eres responsable de las consecuencias operativas de las acciones que ejecutes sobre tus bases de datos.' },

    { type: 'h3', text: '5. Asistente con inteligencia artificial' },
    { type: 'p', text: 'Las respuestas del asistente las genera un modelo de IA y pueden ser incorrectas o incompletas. Verifícalas antes de aplicarlas en producción. El asistente no sustituye el criterio profesional de un DBA.' },

    { type: 'h3', text: '6. Disponibilidad y mantenimiento' },
    { type: 'p', text: 'Podemos programar ventanas de mantenimiento que limiten total o parcialmente el uso del servicio. No garantizamos disponibilidad ininterrumpida.' },

    { type: 'h3', text: '7. Propiedad intelectual' },
    { type: 'p', text: 'La plataforma y su código son del responsable del servicio o de sus licenciantes. Las librerías de terceros se usan bajo sus licencias (ver Licencias y Créditos). Tú conservas los derechos sobre el contenido que subes (por ejemplo, tu foto) y nos concedes permiso limitado para almacenarlo y mostrarlo dentro de la plataforma. Solo subas imágenes sobre las que tengas derechos.' },

    { type: 'h3', text: '8. Limitación de responsabilidad' },
    { type: 'p', text: 'En la medida permitida por la ley, el servicio se ofrece «tal cual». No respondemos por daños indirectos ni por pérdidas derivadas de acciones ejecutadas desde la plataforma sobre tus bases de datos, ni por decisiones tomadas con base en las respuestas del asistente de IA.' },

    { type: 'h3', text: '9. Terminación y eliminación de datos' },
    { type: 'p', text: 'Puedes eliminar tu cuenta y tus datos personales en cualquier momento desde tu perfil. Podemos suspender cuentas que incumplan estos términos o pongan en riesgo la seguridad.' },

    { type: 'h3', text: '10. Ley aplicable y cambios' },
    { type: 'p', text: `Estos términos se rigen por las leyes de la República de Colombia. Si los modificamos de forma relevante, te pediremos aceptarlos de nuevo. Versión vigente: ${LEGAL_VERSION}. Contacto: ${CONTACT}.` },
  ]
};

const COOKIES: LegalDoc = {
  slug: 'cookies',
  title: 'Política de Cookies y Almacenamiento Local',
  summary: 'Qué guardamos en tu navegador, para qué y cómo cambiar tu elección.',
  blocks: [
    { type: 'h3', text: '1. Qué usamos' },
    { type: 'p', text: 'DataCheck Pro no usa cookies de publicidad ni de analítica de terceros. Solo usa almacenamiento local del navegador (localStorage) estrictamente necesario para funcionar:' },
    { type: 'table', head: ['Nombre', 'Tipo', 'Finalidad', 'Duración'], rows: [
      ['access_token', 'Necesaria', 'Mantener tu sesión iniciada (token de acceso firmado)', 'Hasta cerrar sesión o expirar el token'],
      ['datacheck_cookie_consent', 'Necesaria', 'Recordar tu decisión sobre cookies y su versión', 'Hasta que la borres o cambie la política'],
    ] },

    { type: 'h3', text: '2. Categorías' },
    { type: 'ul', items: [
      'Necesarias: siempre activas; sin ellas no puedes iniciar sesión. No requieren consentimiento.',
      'Analítica: hoy no se usa ninguna. Está desactivada por defecto y, si la agregáramos, no se cargaría sin tu permiso previo.',
    ] },

    { type: 'h3', text: '3. Recursos de terceros' },
    { type: 'p', text: 'La tipografía (Inter) y las librerías de gráficos y animación (Chart.js, GSAP) se sirven desde nuestro propio servidor, por lo que tu navegador no contacta a terceros para cargarlas.' },

    { type: 'h3', text: '4. Cómo cambiar tu elección' },
    { type: 'p', text: 'Usa el enlace «Preferencias de cookies» al pie de la página para reabrir el panel y cambiar tu decisión cuando quieras. También puedes borrar el almacenamiento local desde la configuración de tu navegador; deberás iniciar sesión de nuevo.' },
    { type: 'p', text: `Versión vigente: ${LEGAL_VERSION}. Dudas: ${CONTACT}.` },
  ]
};

const LICENSES: LegalDoc = {
  slug: 'licencias',
  title: 'Licencias y Créditos',
  summary: 'Software, fuentes e imágenes de terceros que usa DataCheck Pro y bajo qué licencia.',
  blocks: [
    { type: 'h3', text: '1. Software y tipografía de terceros' },
    { type: 'table', head: ['Componente', 'Uso', 'Licencia'], rows: [
      ['Angular, Angular CLI', 'Framework de la interfaz', 'MIT'],
      ['RxJS', 'Programación reactiva', 'Apache 2.0'],
      ['zone.js, tslib', 'Soporte de Angular', 'MIT / 0BSD'],
      ['Chart.js', 'Gráficos de telemetría', 'MIT'],
      ['GSAP (GreenSock)', 'Animaciones del inicio de sesión', 'Licencia estándar de GSAP (uso gratuito; ver gsap.com/standard-license)'],
      ['Inter (vía @fontsource/inter)', 'Tipografía', 'SIL Open Font License 1.1'],
    ] },

    { type: 'h3', text: '2. Imágenes e iconos' },
    { type: 'ul', items: [
      'Los iconos de la interfaz son caracteres emoji Unicode que dibuja la fuente de tu sistema; no se distribuyen archivos de imagen de terceros para ellos.',
      'Las ilustraciones del inicio de sesión (lámpara) son gráficos vectoriales SVG creados dentro del proyecto.',
      'El favicon proviene de la plantilla de Angular CLI (licencia MIT).',
      'Las fotos de perfil las sube cada usuario, quien declara tener derechos sobre ellas al cargarlas. Si crees que una imagen vulnera tus derechos, escribe a ' + CONTACT + ' y la retiraremos.',
    ] },

    { type: 'p', text: 'El inventario completo con versiones está en el repositorio, en docs/THIRD_PARTY_AUDIT.md y docs/ASSETS_LICENSES.md.' },
  ]
};

export const LEGAL_DOCS: Record<string, LegalDoc> = {
  privacidad: PRIVACY,
  terminos: TERMS,
  cookies: COOKIES,
  licencias: LICENSES
};
