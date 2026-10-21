import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { trigger, transition, style, animate, query, stagger } from '@angular/animations';
import { ApiService } from '../../core/services/api.service';
import { DbaService } from '../../core/services/dba.service';
import { ChatService } from '../../core/services/chat.service';
import { ConsentService } from '../../core/services/consent.service';
import { ToastService } from '../../core/services/toast.service';
import { LegalLinksComponent } from '../legal/legal-links.component';
import { Chart as ChartJS, registerables } from 'chart.js';

// Chart.js desde el paquete local (npm): ya no se descarga de un CDN de terceros
ChartJS.register(...registerables);
const Chart: any = ChartJS;

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LegalLinksComponent],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
  animations: [
    trigger('staggerSidebar', [
      transition('* => true', [
        query('.action-btn', [
          style({ opacity: 0, transform: 'translateX(-20px)' }),
          stagger('40ms', [
            animate('400ms cubic-bezier(0.16, 1, 0.3, 1)', style({ opacity: 1, transform: 'none' }))
          ])
        ], { optional: true })
      ])
    ]),
    trigger('fadeSlideUp', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(20px)' }),
        animate('600ms cubic-bezier(0.16, 1, 0.3, 1)', style({ opacity: 1, transform: 'translateY(0)' }))
      ]),
      transition(':leave', [
        animate('300ms ease-in', style({ opacity: 0, transform: 'translateY(-20px)' }))
      ])
    ]),
    trigger('popIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'scale(0.95)' }),
        animate('400ms cubic-bezier(0.16, 1, 0.3, 1)', style({ opacity: 1, transform: 'scale(1)' }))
      ])
    ])
  ]
})
export class DashboardComponent implements OnInit, OnDestroy {
  contracts: any[] = [];
  instances: any[] = [];
  
  selectedContractId: number | null = null;
  selectedInstanceId: number | null = null;
  
  actionResult: any = null;
  isLoadingAction: boolean = false;
  isLoaded: boolean = false;
  currentUser: string = 'User';
  currentUserInitials: string = 'U'; 
  currentUserRole: string = 'Monitor';
  isAdmin: boolean = false;
  isDbaPrincipal: boolean = false;
  canCancelQueries: boolean = false;
  canTestInstance: boolean = false;
  canManageContracts: boolean = false;
  canManageInstances: boolean = false;
  canViewAudit: boolean = false;
  canManageUsers: boolean = false;

  updateRolePermissions(role: string, username: string) {
    this.currentUserRole = role || 'Monitor';
    const rLower = (this.currentUserRole || '').trim().toLowerCase();
    const uLower = (username || '').trim().toLowerCase();
    this.isAdmin = rLower === 'administrador' || rLower === 'admin' || uLower === 'admin';
    this.isDbaPrincipal = rLower === 'dba principal' || rLower === 'dba';
    this.canCancelQueries = this.isAdmin || this.isDbaPrincipal;
    this.canTestInstance = this.isAdmin || this.isDbaPrincipal;
    this.canManageContracts = this.isAdmin;
    this.canManageInstances = this.isAdmin;
    this.canViewAudit = this.isAdmin;
    this.canManageUsers = this.isAdmin;
  }

  // Darling Web / PerformanceMonitor Telemetry State & Tabs
  activeTab: string = 'overview';
  telemetryData: any = null;
  isTelemetryLoading: boolean = false;
  telemetryCpuChart: any = null;
  telemetryWaitsChart: any = null;
  telemetryBlockingChart: any = null;
  telemetryThroughputChart: any = null;

  // Auto-refresh properties (0 = off, 10, 30, 60s)
  autoRefreshInterval: number = 0;
  autoRefreshCountdown: number = 0;
  private autoRefreshTimer: any = null;
  private countdownTimer: any = null;

  // Time range & Date filtering (1h, 6h, 24h, 7d, 30d, custom)
  selectedTimeRange: string = '24h';
  showCustomRange: boolean = false;
  customStartDate: string = '';
  customEndDate: string = '';

  // Zoomed chart modal state
  zoomedChartType: 'cpu' | 'waits' | 'blocking' | 'throughput' | null = null;
  zoomedChartInstance: any = null;
  zoomedChartTitle: string = '';
  zoomedChartBadge: string = '';
  zoomedChartColor: string = '#00e5ff';
  zoomedChartStats: { label: string; value: string }[] = [];

  // Chat properties
  chatInput: string = '';
  isChatMinimized: boolean = true;
  toggleChat() { 
    this.isChatMinimized = !this.isChatMinimized; 
    if (!this.isChatMinimized) {
        this.scrollToBottom();
    }
  }
  chatMessages: any[] = [];
  isChatLoading: boolean = false;

  // Modal properties
  isUserModalOpen: boolean = false;
  isProfileModalOpen: boolean = false;
  userManagementTab: 'list' | 'create' = 'list';
  usersList: any[] = [];
  isLoadingUsers: boolean = false;
  newUser = {
    username: '',
    full_name: '',
    email: '',
    password: '',
    role: 'Monitor'
  };
  /** El administrador confirma que tiene autorización del titular para registrar su correo. Nunca premarcada. */
  newUserConsent: boolean = false;
  isChangePasswordModalOpen: boolean = false;
  targetUserForPassword: any = null;
  newPasswordForUser: string = '';
  isChangingPassword: boolean = false;

  // Edit User Modal
  isEditUserModalOpen: boolean = false;
  editingUserForm = {
    id: 0,
    username: '',
    full_name: '',
    email: '',
    role: 'Monitor'
  };
  isUpdatingUser: boolean = false;

  // Profile properties
  profileForm = {
    oldPassword: '',
    newPassword: '',
    mfaEnabled: false
  };
  profilePhotoUrl: string | null | undefined = null;
  isSavingProfile: boolean = false;

  // Privacidad y derechos del titular
  photoChanged: boolean = false;
  photoRightsConfirmed: boolean = false;
  emailOptOut: boolean = false;
  isConsentModalOpen: boolean = false;
  isDeleteAccountOpen: boolean = false;
  deleteAccountPassword: string = '';
  isDeletingAccount: boolean = false;
  feedbackConsent: boolean = false;

  isCreatingUser = false;

  isFeedbackModalOpen: boolean = false;
  feedbackRating: number = 5;
  feedbackComment: string = '';

  // Contract Modal
  isContractModalOpen: boolean = false;
  newContractName: string = '';
  isCreatingContract: boolean = false;
  isEditContractModalOpen: boolean = false;
  editingContractId: number | null = null;
  editingContractName: string = '';
  isUpdatingContract: boolean = false;

  // Instance Modal
  isInstanceModalOpen: boolean = false;
  newInstance = {
    name: '',
    engine: 'sqlserver',
    host: 'localhost',
    port: 1433,
    database: '',
    username: 'sa',
    password: '',
    contractId: null as number | null
  };
  isCreatingInstance: boolean = false;
  isTestingConnection: boolean = false;
  testConnectionFeedback: string = '';

  // Audit Logs Modal
  isAuditModalOpen: boolean = false;
  auditLogs: any[] = [];
  isAuditLoading: boolean = false;

  // Maintenance & System Adjustments Animation & Granular Lockout
  isMaintenanceActive: boolean = false;
  maintenanceTitle: string = 'Ajustes del Sistema en Progreso';
  maintenanceSubtitle: string = 'Optimizando motores de bases de datos, reindexando y aplicando configuraciones DBA...';
  maintenanceProgress: number = 68;
  isServerMaintenanceActive: boolean = false;
  maintenancePollTimer: any = null;

  // Granular Maintenance & Live Timer State
  disabledModules: string[] = [];
  maintenanceActivatedAt: string | null = null;
  maintenanceElapsedFormatted: string = '00:00:00';
  elapsedTimerInterval: any = null;
  isMaintenanceConfigModalOpen: boolean = false;
  isGlobalMaintenanceOption: boolean = true;
  selectedModulesToDisable: { [key: string]: boolean } = {};
  isSavingMaintenanceConfig: boolean = false;

  availableMaintenanceModules: { key: string; label: string; icon: string }[] = [
    { key: 'cpu', label: 'Monitor de Salud & CPU', icon: '⚡' },
    { key: 'esperas', label: 'Estadísticas de Espera', icon: '⏱️' },
    { key: 'bloqueos', label: 'Análisis de Bloqueos', icon: '🔒' },
    { key: 'bloat', label: 'Bloat y Fragmentación', icon: '🧹' },
    { key: 'mantenimiento', label: 'Salud Mantenimiento & Autovacuum', icon: '⚙️' },
    { key: 'discos', label: 'Almacenamiento e I/O', icon: '💾' },
    { key: 'tempdb', label: 'Uso de TempDB', icon: '🗂️' },
    { key: 'whoisactive', label: 'Sesiones Activas (WhoIsActive)', icon: '👤' },
    { key: 'jobs', label: 'Estado de Jobs / Tareas', icon: '📋' },
    { key: 'alwayson', label: 'Nodos AlwaysOn / Réplicas', icon: '🔗' },
    { key: 'performance', label: 'Performance General', icon: '📈' },
    { key: 'topqueries', label: 'Top Consultas Lentas', icon: '🔥' },
    { key: 'datalog', label: 'Validar Data y Log', icon: '🔍' },
    { key: 'backups', label: 'Estado de Respaldos (Backups)', icon: '💾' },
    { key: 'cancelar', label: 'Forzar Cancelación (Kill)', icon: '❌' }
  ];

  // About Project Modal
  isAboutModalOpen: boolean = false;
  appVersion: string = '2.5.5';

  // Dedicated Instance CPU Chart instance
  instanceCpuChart: any = null;

  constructor(
    private router: Router,
    private apiService: ApiService,
    private dbaService: DbaService,
    private chatService: ChatService,
    public consent: ConsentService,
    public toast: ToastService
  ) {}

  // --- Contract Management Modal ---
  openContractModal() {
    this.newContractName = '';
    this.isContractModalOpen = true;
  }

  closeContractModal() {
    this.isContractModalOpen = false;
  }

  submitContract() {
    if (!this.newContractName.trim()) {
      this.toast.warning('Ingresa el nombre del contrato.');
      return;
    }
    this.isCreatingContract = true;
    this.apiService.createContract(this.newContractName.trim()).subscribe({
      next: (res) => {
        this.toast.success(`Contrato '${this.newContractName}' creado exitosamente.`);
        this.isCreatingContract = false;
        this.closeContractModal();
        this.loadContracts();
      },
      error: (err) => {
        this.toast.error(err.error?.detail || 'Error al crear contrato');
        this.isCreatingContract = false;
      }
    });
  }

  openEditContractModal(contract?: any) {
    const c = contract || this.contracts.find(item => item.id === this.selectedContractId);
    if (!c) {
      this.toast.warning('Por favor selecciona un contrato para editar.');
      return;
    }
    this.editingContractId = c.id;
    this.editingContractName = c.name;
    this.isEditContractModalOpen = true;
  }

  closeEditContractModal() {
    this.isEditContractModalOpen = false;
    this.editingContractId = null;
    this.editingContractName = '';
  }

  submitUpdateContract() {
    if (!this.editingContractId || !this.editingContractName.trim()) {
      this.toast.warning('Ingresa un nombre válido para el contrato.');
      return;
    }
    this.isUpdatingContract = true;
    this.apiService.updateContract(this.editingContractId, this.editingContractName.trim()).subscribe({
      next: (res) => {
        this.toast.success(`Contrato actualizado exitosamente a '${this.editingContractName}'.`);
        this.isUpdatingContract = false;
        this.closeEditContractModal();
        this.loadContracts();
      },
      error: (err) => {
        this.toast.error(err.error?.detail || 'Error al actualizar el contrato');
        this.isUpdatingContract = false;
      }
    });
  }

  confirmDeleteContract(contractId?: number, contractName?: string) {
    const cid = contractId || this.selectedContractId;
    if (!cid) {
      this.toast.warning('Por favor selecciona un contrato para eliminar.');
      return;
    }
    const c = this.contracts.find(item => item.id === cid);
    const name = contractName || (c ? c.name : `ID ${cid}`);

    if (confirm(`¿Estás seguro de eliminar el contrato "${name}" y desactivar sus instancias asociadas?`)) {
      this.apiService.deleteContract(cid).subscribe({
        next: () => {
          this.toast.success(`Contrato "${name}" eliminado correctamente.`);
          if (this.selectedContractId === cid) {
            this.selectedContractId = null;
          }
          this.loadContracts();
        },
        error: (err) => {
          this.toast.error(err.error?.detail || 'Error al eliminar el contrato.');
        }
      });
    }
  }

  // --- Instance Management Modal ---
  openInstanceModal() {
    this.newInstance = {
      name: '',
      engine: 'sqlserver',
      host: 'localhost',
      port: 1433,
      database: '',
      username: 'sa',
      password: '',
      contractId: this.selectedContractId
    };
    this.isInstanceModalOpen = true;
  }

  closeInstanceModal() {
    this.isInstanceModalOpen = false;
  }

  onEngineSelectChange() {
    if (this.newInstance.engine === 'postgres') {
      this.newInstance.port = 5432;
      if (this.newInstance.username === 'sa') {
        this.newInstance.username = 'postgres';
      }
    } else {
      this.newInstance.port = 1433;
      if (this.newInstance.username === 'postgres') {
        this.newInstance.username = 'sa';
      }
    }
  }

  submitInstance() {
    if (!this.newInstance.name.trim() || !this.newInstance.host.trim() || !this.newInstance.database.trim()) {
      this.toast.warning('Por favor completa Nombre, Servidor/Host y Base de Datos.');
      return;
    }
    const contractId = this.newInstance.contractId || this.selectedContractId;
    if (!contractId) {
      this.toast.warning('Debes seleccionar un contrato para la instancia.');
      return;
    }

    const host = this.newInstance.host.trim();
    const port = this.newInstance.port;
    const db = this.newInstance.database.trim();
    const u = encodeURIComponent(this.newInstance.username.trim());
    const p = encodeURIComponent(this.newInstance.password.trim());

    let connStr = '';
    if (this.newInstance.engine === 'postgres') {
      connStr = `postgresql+pg8000://${u}:${p}@${host}:${port}/${db}`;
    } else {
      connStr = `DRIVER={ODBC Driver 18 for SQL Server};SERVER=${host},${port};DATABASE=${db};UID=${u};PWD=${p};TrustServerCertificate=yes;Encrypt=no;`;
    }

    this.isCreatingInstance = true;
    this.apiService.createInstance(contractId, this.newInstance.name.trim(), connStr).subscribe({
      next: (res) => {
        this.toast.success(`Instancia '${this.newInstance.name}' registrada correctamente.`);
        this.isCreatingInstance = false;
        this.closeInstanceModal();
        this.loadInstances();
      },
      error: (err) => {
        this.toast.error(err.error?.detail || 'Error al registrar instancia');
        this.isCreatingInstance = false;
      }
    });
  }

  buildNewInstanceConnStr(): string {
    const host = this.newInstance.host.trim();
    const port = this.newInstance.port;
    const db = this.newInstance.database.trim();
    const u = encodeURIComponent(this.newInstance.username.trim());
    const p = encodeURIComponent(this.newInstance.password.trim());

    if (this.newInstance.engine === 'postgres') {
      return `postgresql+pg8000://${u}:${p}@${host}:${port}/${db}`;
    } else {
      return `DRIVER={ODBC Driver 18 for SQL Server};SERVER=${host},${port};DATABASE=${db};UID=${u};PWD=${p};TrustServerCertificate=yes;Encrypt=no;`;
    }
  }

  testInstanceFormConnection() {
    if (!this.newInstance.host.trim() || !this.newInstance.database.trim()) {
      this.toast.warning('Ingresa al menos Servidor/Host y Base de Datos para probar la conexión.');
      return;
    }
    const connStr = this.buildNewInstanceConnStr();
    this.isTestingConnection = true;
    this.testConnectionFeedback = 'Probando conexión...';

    this.apiService.testConnectionString(connStr).subscribe({
      next: (res) => {
        this.isTestingConnection = false;
        if (res.success) {
          this.testConnectionFeedback = `✅ ¡Conexión exitosa! (${res.latency_ms} ms) - Motor: ${res.engine}`;
          this.toast.success(`✅ ¡Conexión Exitosa!\n\nMotor: ${res.engine}\nLatencia: ${res.latency_ms} ms\nVersión: ${res.version || 'OK'}`);
        } else {
          this.testConnectionFeedback = `❌ Error: ${res.error || 'No se pudo conectar'}`;
          this.toast.error(`❌ Error al conectar (${res.latency_ms} ms):\n\n${res.error || 'Verifica host, puerto o credenciales.'}`);
        }
      },
      error: (err) => {
        this.isTestingConnection = false;
        const msg = err.error?.detail || 'Error al probar conexión remota';
        this.testConnectionFeedback = `❌ Error: ${msg}`;
        this.toast.error(`❌ ${msg}`);
      }
    });
  }

  testCurrentInstance() {
    if (!this.selectedInstanceId) {
      this.toast.warning('Por favor selecciona una instancia primero.');
      return;
    }
    this.apiService.testInstanceConnection(this.selectedInstanceId).subscribe({
      next: (res) => {
        if (res.success) {
          this.toast.success(`✅ ¡Instancia en Línea!\n\nMotor: ${res.engine}\nLatencia de respuesta: ${res.latency_ms} ms\nVersión: ${res.version || 'OK'}`);
        } else {
          this.toast.error(`⚠️ Falla en Instancia (${res.latency_ms} ms):\n\n${res.error || 'El servidor no responde o credenciales inválidas.'}`);
        }
      },
      error: (err) => {
        this.toast.error(err.error?.detail || 'Error al probar la instancia');
      }
    });
  }

  // --- Audit Logs Modal ---
  openAuditModal() {
    this.isAuditModalOpen = true;
    this.loadAuditLogs();
  }

  closeAuditModal() {
    this.isAuditModalOpen = false;
  }

  loadAuditLogs() {
    this.isAuditLoading = true;
    this.apiService.getAuditLogs().subscribe({
      next: (logs) => {
        this.auditLogs = logs;
        this.isAuditLoading = false;
      },
      error: (err) => {
        console.error('Error cargando logs de auditoría', err);
        this.isAuditLoading = false;
      }
    });
  }

  exportAuditToCsv() {
    if (!this.auditLogs || !this.auditLogs.length) {
      this.toast.info('No hay registros de auditoría para exportar.');
      return;
    }
    const headers = ['ID', 'Usuario', 'Accion', 'Motor', 'SPID', 'Estado', 'Detalles', 'Fecha'];
    const rows = this.auditLogs.map(item => [
      item.id,
      `"${(item.username || '').replace(/"/g, '""')}"`,
      `"${(item.action || '').replace(/"/g, '""')}"`,
      `"${(item.engine || '').replace(/"/g, '""')}"`,
      `"${(item.target_spid || '')}"`,
      `"${(item.status || '').replace(/"/g, '""')}"`,
      `"${(item.details || '').replace(/"/g, '""')}"`,
      `"${item.created_at || ''}"`
    ]);

    const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(e => e.join(','))].join('\r\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `auditoria_datacheck_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }


  openProfileModal() {
    this.isProfileModalOpen = true;
    this.loadProfile();
  }
  closeProfileModal() {
    this.isProfileModalOpen = false;
  }

  loadProfile() {
    this.apiService.getProfile().subscribe({
      next: (res) => {
        this.profileForm.mfaEnabled = res.mfa_enabled;
        this.profilePhotoUrl = res.profile_photo;
        this.photoChanged = false;
        this.emailOptOut = !!res.email_opt_out;
        this.isConsentModalOpen = !!res.consent_required;
        if (res.role) {
          this.updateRolePermissions(res.role, res.username || this.currentUser);
        }
      },
      error: (err) => console.error("Error loading profile", err)
    });
  }

  onPhotoSelected(event: any) {
    const file = event.target.files?.[0];
    if (file) {
      if (file.size > 3 * 1024 * 1024) {
        this.toast.error('⚠️ La imagen seleccionada es muy pesada (máximo 3 MB). Por favor selecciona una imagen más liviana.');
        return;
      }
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.profilePhotoUrl = e.target.result;
        this.photoChanged = true;
        this.photoRightsConfirmed = false;
      };
      reader.readAsDataURL(file);
    }
  }

  removePhoto() {
    this.profilePhotoUrl = '';
    this.photoChanged = true;
  }

  saveProfileChanges() {
    this.isSavingProfile = true;
    
    // Save MFA
    this.apiService.toggleMfa({ mfa_enabled: this.profileForm.mfaEnabled }).subscribe({
      next: () => {},
      error: (err) => console.error("Error saving MFA", err)
    });

    // Save Photo only if the user changed or removed it (a new photo requires declaring image rights)
    if (this.photoChanged && this.profilePhotoUrl !== null && this.profilePhotoUrl !== undefined) {
      if (this.profilePhotoUrl && !this.photoRightsConfirmed) {
        this.toast.warning('Para guardar la foto debes declarar que tienes derechos para usar la imagen.');
        this.isSavingProfile = false;
        return;
      }
      this.apiService.updatePhoto({ photo_base64: this.profilePhotoUrl, rights_confirmed: this.photoRightsConfirmed }).subscribe({
        next: () => { this.photoChanged = false; },
        error: (err) => this.toast.error(err.error?.detail || 'Error al guardar la foto')
      });
    }

    // Save Password if filled
    if (this.profileForm.oldPassword && this.profileForm.newPassword) {
      this.apiService.updatePassword({
        old_password: this.profileForm.oldPassword,
        new_password: this.profileForm.newPassword
      }).subscribe({
        next: (res) => {
          this.toast.success('✅ Perfil actualizado exitosamente (contraseña y foto guardadas).');
          this.profileForm.oldPassword = '';
          this.profileForm.newPassword = '';
          this.isSavingProfile = false;
          this.closeProfileModal();
        },
        error: (err) => {
          this.toast.error(err.error?.detail || 'Error al cambiar contraseña');
          this.isSavingProfile = false;
        }
      });
    } else {
      setTimeout(() => {
        this.isSavingProfile = false;
        this.toast.success('✅ Foto de perfil y ajustes guardados con éxito.');
        this.closeProfileModal();
      }, 500);
    }
  }

  openUserModal() {
    this.isUserModalOpen = true;
    this.userManagementTab = 'list';
    this.newUser = {
      username: '',
      full_name: '',
      email: '',
      password: '',
      role: 'Monitor'
    };
    this.loadUsers();
  }

  closeUserModal() {
    this.isUserModalOpen = false;
  }

  loadUsers() {
    this.isLoadingUsers = true;
    this.apiService.getUsers().subscribe({
      next: (data) => {
        this.usersList = data;
        this.isLoadingUsers = false;
      },
      error: (err) => {
        console.error('Error al cargar usuarios', err);
        this.isLoadingUsers = false;
      }
    });
  }

  generateRandomPassword() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%';
    let pwd = '';
    for (let i = 0; i < 10; i++) {
      pwd += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    this.newUser.password = pwd;
  }

  openChangePasswordModal(user: any) {
    this.targetUserForPassword = user;
    this.newPasswordForUser = '';
    this.isChangePasswordModalOpen = true;
  }

  closeChangePasswordModal() {
    this.isChangePasswordModalOpen = false;
    this.targetUserForPassword = null;
    this.newPasswordForUser = '';
  }

  submitChangePassword() {
    if (!this.targetUserForPassword) return;
    if (!this.newPasswordForUser || this.newPasswordForUser.length < 8) {
      this.toast.info('Por seguridad (OWASP), la contraseña debe tener al menos 8 caracteres.');
      return;
    }
    this.isChangingPassword = true;
    this.apiService.changeUserPassword(this.targetUserForPassword.id, this.newPasswordForUser).subscribe({
      next: (res) => {
        this.toast.success(`Contraseña actualizada con éxito para el usuario '${this.targetUserForPassword.username}'.`);
        this.isChangingPassword = false;
        this.closeChangePasswordModal();
      },
      error: (err) => {
        this.toast.error(err.error?.detail || 'Error al cambiar contraseña');
        this.isChangingPassword = false;
      }
    });
  }

  confirmDeleteUser(user: any) {
    if (user.username === this.currentUser) {
      this.toast.info('No puedes eliminar tu propia cuenta en sesión activa.');
      return;
    }
    if (confirm(`¿Estás seguro de eliminar al usuario "${user.username}"?`)) {
      this.apiService.deleteUser(user.id).subscribe({
        next: () => {
          this.toast.success(`Usuario "${user.username}" eliminado correctamente.`);
          this.loadUsers();
        },
        error: (err) => {
          this.toast.error(err.error?.detail || 'Error al eliminar usuario.');
        }
      });
    }
  }

  openEditUserModal(user: any) {
    this.editingUserForm = {
      id: user.id,
      username: user.username,
      full_name: user.full_name || '',
      email: user.email || '',
      role: user.role || 'Monitor'
    };
    this.isEditUserModalOpen = true;
  }

  closeEditUserModal() {
    this.isEditUserModalOpen = false;
  }

  submitUpdateUser() {
    if (!this.editingUserForm.id) return;
    this.isUpdatingUser = true;
    this.apiService.updateUser(this.editingUserForm.id, {
      full_name: this.editingUserForm.full_name.trim() || undefined,
      email: this.editingUserForm.email.trim() || undefined,
      role: this.editingUserForm.role
    }).subscribe({
      next: (res) => {
        this.toast.success(`Usuario '${this.editingUserForm.username}' actualizado exitosamente.`);
        this.isUpdatingUser = false;
        this.closeEditUserModal();
        this.loadUsers();
      },
      error: (err) => {
        this.toast.error(err.error?.detail || 'Error al actualizar usuario.');
        this.isUpdatingUser = false;
      }
    });
  }

  // --- Maintenance Mode Animation, Granular Logic & Server Sync ---
  checkServerMaintenanceStatus() {
    this.apiService.getMaintenanceStatus().subscribe({
      next: (status) => {
        this.isServerMaintenanceActive = !!status.is_active;
        if (status.title) this.maintenanceTitle = status.title;
        if (status.subtitle) this.maintenanceSubtitle = status.subtitle;
        this.disabledModules = Array.isArray(status.disabled_modules) ? status.disabled_modules : [];
        this.maintenanceActivatedAt = status.activated_at || null;

        if (this.isServerMaintenanceActive && this.maintenanceActivatedAt) {
          this.startElapsedTimer();
        } else {
          this.stopElapsedTimer();
        }

        // Lockout behavior:
        // - Global lockout (empty disabled_modules or ['*']): Non-admins get full-screen overlay
        // - Granular lockout: Non-admins stay in app; only specific buttons disabled, and top banner shows
        if (this.isServerMaintenanceActive) {
          if (this.isGlobalLock()) {
            if (!this.isAdmin) {
              this.isMaintenanceActive = true;
            }
          } else {
            if (!this.isAdmin) {
              this.isMaintenanceActive = false;
            }
          }
        } else {
          if (!this.isAdmin) {
            this.isMaintenanceActive = false;
          }
        }
      },
      error: (err) => console.error('Error verificando estado de mantenimiento', err)
    });
  }

  isGlobalLock(): boolean {
    if (!this.isServerMaintenanceActive) return false;
    return this.disabledModules.length === 0 || this.disabledModules.includes('*') || this.disabledModules.includes('all');
  }

  get isMaintenanceOverlayVisible(): boolean {
    if (this.isServerMaintenanceActive) {
      if (!this.isAdmin) {
        // Non-admins ONLY see the full-screen lockdown overlay if it is a global lockdown
        return this.isGlobalLock();
      }
      return this.isMaintenanceActive;
    }
    return this.isMaintenanceActive;
  }

  isModuleDisabled(key: string): boolean {
    if (!this.isServerMaintenanceActive) return false;
    if (this.isGlobalLock()) return true;

    const normalizedKey = key.toLowerCase();
    const aliases: { [k: string]: string[] } = {
      'waitstats': ['esperas', 'waitstats'],
      'esperas': ['esperas', 'waitstats'],
      'cpu': ['cpu'],
      'bloqueos': ['bloqueos'],
      'bloat': ['bloat', 'pg_bloat'],
      'mantenimiento': ['mantenimiento', 'maintenance', 'pg_autovacuum'],
      'maintenance': ['mantenimiento', 'maintenance', 'pg_autovacuum'],
      'discos': ['discos'],
      'tempdb': ['tempdb'],
      'whoisactive': ['whoisactive'],
      'jobs': ['jobs'],
      'alwayson': ['alwayson'],
      'performance': ['performance'],
      'datalog': ['datalog'],
      'cancelar': ['cancelar']
    };

    const list = aliases[normalizedKey] || [normalizedKey];
    return this.disabledModules.some(m => list.includes(m.toLowerCase()));
  }

  getDisabledModuleLabels(): string {
    if (this.isGlobalLock()) return 'Plataforma Completa';
    const matched = this.availableMaintenanceModules
      .filter(mod => this.isModuleDisabled(mod.key))
      .map(mod => mod.label);
    return matched.join(', ') || 'Módulos Seleccionados';
  }

  startElapsedTimer() {
    if (this.elapsedTimerInterval) {
      clearInterval(this.elapsedTimerInterval);
    }
    this.updateElapsedTimer();
    this.elapsedTimerInterval = setInterval(() => {
      this.updateElapsedTimer();
    }, 1000);
  }

  stopElapsedTimer() {
    if (this.elapsedTimerInterval) {
      clearInterval(this.elapsedTimerInterval);
      this.elapsedTimerInterval = null;
    }
    this.maintenanceElapsedFormatted = '00:00:00';
  }

  updateElapsedTimer() {
    if (!this.maintenanceActivatedAt) {
      this.maintenanceElapsedFormatted = '00:00:00';
      return;
    }
    const start = new Date(this.maintenanceActivatedAt).getTime();
    const now = new Date().getTime();
    const diffSec = Math.max(0, Math.floor((now - start) / 1000));

    const hours = Math.floor(diffSec / 3600);
    const minutes = Math.floor((diffSec % 3600) / 60);
    const seconds = diffSec % 60;

    const pad = (n: number) => n.toString().padStart(2, '0');
    this.maintenanceElapsedFormatted = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
  }

  openMaintenanceConfigModal() {
    if (!this.isAdmin) return;
    this.isGlobalMaintenanceOption = this.isGlobalLock();
    this.selectedModulesToDisable = {};
    this.availableMaintenanceModules.forEach(mod => {
      this.selectedModulesToDisable[mod.key] = this.isModuleDisabled(mod.key);
    });
    this.isMaintenanceConfigModalOpen = true;
  }

  closeMaintenanceConfigModal() {
    this.isMaintenanceConfigModalOpen = false;
  }

  toggleAllModulesSelection(select: boolean) {
    this.availableMaintenanceModules.forEach(mod => {
      this.selectedModulesToDisable[mod.key] = select;
    });
  }

  submitMaintenanceConfig(activate: boolean) {
    if (!this.isAdmin) return;
    this.isSavingMaintenanceConfig = true;

    let modulesToDisable: string[] = [];
    if (activate) {
      if (this.isGlobalMaintenanceOption) {
        modulesToDisable = ['*'];
      } else {
        modulesToDisable = Object.keys(this.selectedModulesToDisable).filter(k => this.selectedModulesToDisable[k]);
        if (modulesToDisable.length === 0) {
          this.toast.warning('Por favor selecciona al menos un botón/módulo a deshabilitar o activa el "Bloqueo Global".');
          this.isSavingMaintenanceConfig = false;
          return;
        }
      }
    }

    this.apiService.setMaintenanceStatus({
      is_active: activate,
      title: this.maintenanceTitle.trim() || 'Ajustes del Sistema en Progreso',
      subtitle: this.maintenanceSubtitle.trim() || 'Optimizando motores de bases de datos, reindexando y aplicando configuraciones DBA...',
      disabled_modules: modulesToDisable
    }).subscribe({
      next: (res) => {
        this.isSavingMaintenanceConfig = false;
        this.isMaintenanceConfigModalOpen = false;
        this.checkServerMaintenanceStatus();
        if (activate) {
          if (this.isGlobalMaintenanceOption) {
            this.toast.info('🛠️ Bloqueo Global Activado:\nTodos los usuarios que no son Administradores tienen la pantalla bloqueada con temporizador en tiempo real.');
          } else {
            this.toast.info(`🛠️ Mantenimiento Modular Activado:\nSe han deshabilitado ${modulesToDisable.length} botones específicos. El resto de la base de datos y la plataforma siguen operativos para los usuarios.`);
          }
        } else {
          this.toast.success('✅ Modo Mantenimiento DESACTIVADO.\nTodos los módulos y la plataforma han sido restablecidos con normalidad.');
        }
      },
      error: (err) => {
        this.isSavingMaintenanceConfig = false;
        this.toast.error(err.error?.detail || 'Error al actualizar configuración de mantenimiento');
      }
    });
  }

  toggleServerMaintenance(forceState?: boolean) {
    if (!this.isAdmin) return;
    if (this.isServerMaintenanceActive && forceState === false) {
      this.submitMaintenanceConfig(false);
      return;
    }
    this.openMaintenanceConfigModal();
  }

  toggleMaintenanceMode() {
    if (this.isAdmin) {
      this.openMaintenanceConfigModal();
    } else {
      this.isMaintenanceActive = !this.isMaintenanceActive;
    }
  }

  dismissAdminPreview() {
    // Admin closes preview for their local view so they can continue working
    this.isMaintenanceActive = false;
  }

  triggerTemporaryMaintenance(title: string = 'Ajustes del Sistema en Progreso', durationMs: number = 3500) {
    this.maintenanceTitle = title;
    this.isMaintenanceActive = true;
    setTimeout(() => {
      this.isMaintenanceActive = false;
    }, durationMs);
  }

  // --- About Project Modal ---
  openAboutModal() {
    this.isAboutModalOpen = true;
  }

  closeAboutModal() {
    this.isAboutModalOpen = false;
  }

  copySystemInfo() {
    const info = `DataCheck Pro Version: ${this.appVersion}
Architecture: Jhojan Usuga Vargas
Frontend: Angular 18.2 + Chart.js
Backend: FastAPI 0.142 + Python 3.14 + SQLAlchemy 2.0
Supported Engines: Microsoft SQL Server (ODBC 18) & PostgreSQL (PG12-PG17)
Security: AES-128 Fernet & JWT & Immutable Audit Logs
Date: 2026-10-12`;
    navigator.clipboard.writeText(info).then(() => {
      this.toast.info('Información del sistema copiada al portapapeles.');
    }).catch(() => {
      this.toast.info(info);
    });
  }

  // --- Feedback & Export ---
  exportToPDF() {
    window.print();
  }

  openDocs() {
    window.open('https://github.com/arus-com-co/datacheck-docs', '_blank', 'noopener,noreferrer');
  }

  openFeedbackModal() {
    this.feedbackRating = 5;
    this.feedbackComment = '';
    this.feedbackConsent = false;
    this.isFeedbackModalOpen = true;
  }

  submitFeedback() {
    if (this.feedbackComment.trim() && !this.feedbackConsent) {
      this.toast.warning('Para enviar tu comentario debes autorizar su tratamiento marcando la casilla.');
      return;
    }
    this.apiService.submitFeedback(this.feedbackRating, this.feedbackComment, true).subscribe({
      next: () => {
        this.toast.info('Gracias, recibimos tu comentario.');
        this.isFeedbackModalOpen = false;
      },
      error: (err) => {
        this.toast.error("Error enviando feedback: " + (err.error?.detail || err.message));
      }
    });
  }

  submitUser() {
    if (!this.newUser.username.trim()) {
      this.toast.warning("Por favor ingresa un nombre de usuario.");
      return;
    }
    this.isCreatingUser = true;
    const payload = {
      username: this.newUser.username.trim(),
      full_name: this.newUser.full_name.trim() || this.newUser.username.trim(),
      email: this.newUser.email.trim() || undefined,
      password: this.newUser.password.trim() || undefined,
      role: this.newUser.role,
      consent_confirmed: this.newUserConsent
    };

    this.apiService.createUser(payload).subscribe({
      next: (res) => {
        let msg = `Usuario '${payload.username}' creado con éxito.`;
        if (res.invitation && res.invitation.sent) {
          msg += `\n📧 Se despachó el correo de invitación a ${payload.email} con las credenciales de acceso.`;
        } else if (payload.password) {
          msg += `\nContraseña configurada: ${payload.password}`;
        }
        this.toast.info(msg);
        this.isCreatingUser = false;
        this.userManagementTab = 'list';
        this.loadUsers();
      },
      error: (err) => {
        this.toast.error(err.error?.detail || "Error al crear usuario");
        this.isCreatingUser = false;
      }
    });
  }

  ngOnInit() {
    const token = localStorage.getItem('access_token');
    if(token) {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if(payload.sub) {
                this.currentUser = payload.sub;
                this.currentUserInitials = this.currentUser.substring(0, 2).toUpperCase();
            }
            let roleFromToken = payload.role || this.currentUserRole;
            this.updateRolePermissions(roleFromToken, this.currentUser);
        } catch(e) {}
    }
    if (!localStorage.getItem('access_token')) {
      this.router.navigate(['/login']);
      return;
    }
    
    setTimeout(() => {
      this.isLoaded = true;
    }, 100);

    this.loadContracts();
    this.loadProfile();
    this.loadChatHistory();
    this.loadTelemetryOverview();
    this.checkServerMaintenanceStatus();
    this.maintenancePollTimer = setInterval(() => {
      this.checkServerMaintenanceStatus();
    }, 6000);
  }

  ngOnDestroy() {
    if (this.maintenancePollTimer) {
      clearInterval(this.maintenancePollTimer);
    }
    this.stopElapsedTimer();
  }

  loadChatHistory() {
    this.chatService.getHistory().subscribe({
      next: (history) => {
        this.chatMessages = history.map(msg => ({
          text: msg.content,
          isUser: !msg.is_bot && msg.username !== 'AI_DBA'
        }));
        this.scrollToBottom();
      },
      error: (err) => console.error("Error cargando historial", err)
    });
  }

  sendOption(opt: string) {
    this.chatInput = opt;
    setTimeout(() => {
      const input = document.querySelector('.chat-input-wrapper input') as HTMLInputElement;
      if (input) input.focus();
    }, 100);
  }

  sendMessage() {
    if (!this.chatInput.trim()) return;
    
    const userMsg = this.chatInput;
    this.chatMessages.push({ text: userMsg, isUser: true });
    this.chatInput = '';
    this.isChatLoading = true;

    this.chatService.sendMessage(userMsg).subscribe({
      next: (res) => {
        this.isChatLoading = false;
        this.chatMessages.push({ text: res.reply || (res as any).message, isUser: false, options: res.options });
        this.scrollToBottom();
      },
      error: (err) => {
        this.isChatLoading = false;
        this.chatMessages.push({
          text: "⚠️ " + (err.error?.detail || "No se pudo comunicar con el servicio de chat."),
          isUser: false
        });
        this.scrollToBottom();
      }
    });
  }

  clearChat() {
    this.chatService.clearHistory().subscribe({
      next: () => {
        this.chatMessages = [];
      },
      error: (err) => {
        console.error("Error al borrar historial en servidor", err);
        this.chatMessages = [];
      }
    });
  }

  scrollToBottom() {
    setTimeout(() => {
      const container = document.querySelector('.chat-body');
      if (container) container.scrollTop = container.scrollHeight;
    }, 100);
  }

  // UI Helpers
  getKeys(obj: any): string[] {
    if (!obj) return [];
    return Object.keys(obj);
  }

  isArray(obj: any): boolean {
    return Array.isArray(obj);
  }

  formatMessage(msg: string): string {
    if (!msg) return '';
    return msg.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }

  getActionType(): string {
    if (!this.actionResult) return '';
    return this.actionResult.type || (this.actionResult.data && this.actionResult.data.type) || '';
  }

  getActionData(): any {
    if (!this.actionResult) return null;
    if (this.actionResult.data !== undefined) {
      if (this.actionResult.data && typeof this.actionResult.data === 'object' && this.actionResult.data.data !== undefined) {
        return this.actionResult.data.data;
      }
      return this.actionResult.data;
    }
    return this.actionResult;
  }

  getActionMessage(): string {
    if (!this.actionResult) return '';
    return this.actionResult.message || this.actionResult.detail || (this.actionResult.data && (this.actionResult.data.message || this.actionResult.data.detail)) || '';
  }

  getActionTitle(): string {
    if (!this.actionResult) return '';
    return this.actionResult.title || 'Diagnóstico del Motor';
  }

  isTableData(): boolean {
    const d = this.getActionData();
    return Array.isArray(d);
  }

  loadContracts() {
    this.apiService.getContracts().subscribe({
      next: (data) => {
        this.contracts = data;
        if (this.contracts.length > 0) {
          if (!this.selectedContractId || !this.contracts.some(c => c.id === this.selectedContractId)) {
            this.selectedContractId = this.contracts[0].id;
          }
          this.loadInstances();
        }
      },
      error: (err) => console.error(err)
    });
  }

  loadInstances() {
    if (!this.selectedContractId) return;
    this.apiService.getInstances(this.selectedContractId).subscribe({
      next: (data) => {
        this.instances = data;
        if (this.instances.length > 0) {
          if (!this.selectedInstanceId || !this.instances.some(i => i.id === this.selectedInstanceId)) {
            this.selectedInstanceId = this.instances[0].id;
          }
          this.onInstanceChange();
        } else {
          this.selectedInstanceId = null;
        }
      },
      error: (err) => console.error(err)
    });
  }

  onInstanceChange() {
    if (!this.selectedInstanceId) return;
    this.apiService.selectInstance(this.selectedInstanceId).subscribe({
      next: (res) => {
        console.log('Instance selected', res);
        this.loadTelemetryOverview();
        if (this.activeTab !== 'overview') {
          this.selectTab(this.activeTab);
        }
      },
      error: (err) => console.error(err)
    });
  }

  selectTab(tab: string) {
    if (!this.isAdmin && this.isModuleDisabled(tab)) {
      this.toast.warning(`⚠️ La función '${tab.toUpperCase()}' se encuentra temporalmente deshabilitada por mantenimiento técnico. El resto del sistema y la base de datos continúan operativos.`);
      return;
    }
    this.activeTab = tab;
    if (tab === 'overview') {
      this.loadTelemetryOverview();
    } else {
      const actionMap: { [key: string]: string } = {
        'esperas': 'waitstats',
        'cpu': 'cpu',
        'bloqueos': 'bloqueos',
        'bloat': 'bloat',
        'mantenimiento': 'maintenance',
        'discos': 'discos',
        'tempdb': 'tempdb',
        'whoisactive': 'whoisactive',
        'jobs': 'jobs',
        'alwayson': 'alwayson',
        'performance': 'performance',
        'datalog': 'datalog'
      };
      const action = actionMap[tab] || tab;
      this.runAction(action);
    }
  }

  openSupportCenter() {
    this.isChatMinimized = false;
    this.chatInput = "soporte ";
    setTimeout(() => {
      const input = document.querySelector('.chat-input-area input') as HTMLInputElement;
      if (input) input.focus();
    }, 100);
  }

  formatMarkdown(text: string): string {
    if (!text) return '';
    let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    return formatted;
  }

  logout() {
    localStorage.removeItem('access_token');
    this.router.navigate(['/login']);
  }

  // ---------------------------------------------------------------------------
  // Privacidad: autorización, descarga y eliminación de datos (Ley 1581 de 2012)
  // ---------------------------------------------------------------------------
  acceptLegalDocuments() {
    this.apiService.acceptLegalDocuments().subscribe({
      next: () => { this.isConsentModalOpen = false; },
      error: (err) => this.toast.error(err.error?.detail || 'No se pudo registrar tu autorización. Inténtalo de nuevo.')
    });
  }

  declineLegalDocuments() {
    this.logout();
  }

  downloadMyData() {
    this.apiService.exportMyData().subscribe({
      next: (data) => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `datacheck-mis-datos-${this.currentUser}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      },
      error: (err) => this.toast.error(err.error?.detail || 'No se pudieron descargar tus datos.')
    });
  }

  toggleEmailOptOut() {
    const next = !this.emailOptOut;
    this.apiService.setEmailOptOut(next).subscribe({
      next: () => { this.emailOptOut = next; },
      error: (err) => this.toast.error(err.error?.detail || 'No se pudo actualizar tu preferencia.')
    });
  }

  openDeleteAccount() {
    this.deleteAccountPassword = '';
    this.isDeleteAccountOpen = true;
  }

  cancelDeleteAccount() {
    this.isDeleteAccountOpen = false;
    this.deleteAccountPassword = '';
  }

  confirmDeleteAccount() {
    if (!this.deleteAccountPassword) {
      this.toast.warning('Ingresa tu contraseña para confirmar.');
      return;
    }
    this.isDeletingAccount = true;
    this.apiService.deleteMyAccount(this.deleteAccountPassword).subscribe({
      next: (res) => {
        this.isDeletingAccount = false;
        this.toast.success(res.message || 'Tu cuenta fue eliminada.');
        this.logout();
      },
      error: (err) => {
        this.isDeletingAccount = false;
        this.toast.error(err.error?.detail || 'No se pudo eliminar la cuenta.');
      }
    });
  }

  /** Teclado: Escape cierra el modal abierto que esté encima (WCAG 2.1.2 / patrón ARIA dialog). */
  @HostListener('document:keydown.escape')
  onEscapeKey() {
    if (this.isConsentModalOpen) { return; } // requiere una decisión explícita
    const stack: Array<[boolean, () => void]> = [
      [this.zoomedChartType !== null, () => this.closeChartZoom()],
      [this.isDeleteAccountOpen, () => this.cancelDeleteAccount()],
      [this.isChangePasswordModalOpen, () => { this.isChangePasswordModalOpen = false; }],
      [this.isEditUserModalOpen, () => { this.isEditUserModalOpen = false; }],
      [this.isEditContractModalOpen, () => { this.isEditContractModalOpen = false; }],
      [this.isContractModalOpen, () => { this.isContractModalOpen = false; }],
      [this.isInstanceModalOpen, () => { this.isInstanceModalOpen = false; }],
      [this.isProfileModalOpen, () => this.closeProfileModal()],
      [this.isUserModalOpen, () => this.closeUserModal()],
      [this.isFeedbackModalOpen, () => { this.isFeedbackModalOpen = false; }],
      [this.isAuditModalOpen, () => { this.isAuditModalOpen = false; }],
      [this.isMaintenanceConfigModalOpen, () => { this.isMaintenanceConfigModalOpen = false; }],
      [this.isAboutModalOpen, () => { this.isAboutModalOpen = false; }],
    ];
    const top = stack.find(([open]) => open);
    if (top) { top[1](); }
  }

  runAction(actionName: string) {
    if (!this.isAdmin && this.isModuleDisabled(actionName)) {
      this.toast.warning(`⚠️ La acción '${actionName.toUpperCase()}' está en mantenimiento técnico.`);
      return;
    }
    if (!this.selectedInstanceId) {
      this.toast.warning("Por favor, selecciona una instancia primero.");
      return;
    }

    this.isLoadingAction = true;
    this.actionResult = null;

    let actionObs;
    switch(actionName) {
      case 'status': actionObs = this.dbaService.getStatus(); break;
      case 'cpu': actionObs = this.dbaService.getCpu(); break;
      case 'discos': actionObs = this.dbaService.getDisks(); break;
      case 'tempdb': actionObs = this.dbaService.getTempDb(); break;
      case 'whoisactive': actionObs = this.dbaService.getWhoIsActive(); break;
      case 'bloqueos': actionObs = this.dbaService.getBloqueos(); break;
      case 'datalog': actionObs = this.dbaService.getDataLog(); break;
      case 'jobs': actionObs = this.dbaService.getJobs(); break;
      case 'alwayson': actionObs = this.dbaService.getAlwaysOn(); break;
      case 'performance': actionObs = this.dbaService.getPerformance(); break;
      case 'waitstats': actionObs = this.dbaService.getWaitStats(); break;
      case 'bloat':
      case 'pg_bloat': actionObs = this.dbaService.getBloat(); break;
      case 'maintenance':
      case 'pg_autovacuum': actionObs = this.dbaService.getMaintenance(); break;
      case 'backups': actionObs = this.dbaService.getBackups(); break;
      case 'topqueries': actionObs = this.dbaService.getTopQueries(); break;
      case 'cancelar': 
        this.isLoadingAction = false;
        if (!this.canCancelQueries) {
          this.toast.error('⛔ Permisos insuficientes: Solo el Administrador y el DBA Principal tienen autorización para forzar la cancelación de consultas y procesos.');
          return;
        }
        this.isChatMinimized = false;
        this.chatInput = "matar ";
        setTimeout(() => {
          const input = document.querySelector('.chat-input-area input') as HTMLInputElement;
          if (input) input.focus();
        }, 100);
        return;
      default: 
        setTimeout(() => {
          this.actionResult = { error: "Acción no implementada temporalmente" };
          this.isLoadingAction = false;
        }, 300);
        return;
    }

    if (actionObs) {
      actionObs.subscribe({
        next: (res) => {
          this.actionResult = res;
          this.isLoadingAction = false;
          if (actionName === 'status' || actionName === 'cpu') {
            setTimeout(() => this.renderCpuChart(), 100);
          }
        },
        error: (err) => {
          this.actionResult = { error: err.error?.detail || err.message };
          this.isLoadingAction = false;
        }
      });
    }
  }

  renderCpuChart() {
    const canvas = document.getElementById('cpuChart') as HTMLCanvasElement;
    if (!canvas) return;

    if (this.instanceCpuChart) {
      try { this.instanceCpuChart.destroy(); } catch (e) {}
      this.instanceCpuChart = null;
    }

    const labels = [];
    const data = [];
    for (let i = 23; i >= 0; i--) {
      labels.push(`${i}h ago`);
      data.push(Math.floor(Math.random() * 50) + 10);
    }
    data[data.length - 1] = 45;

    const ctx = canvas.getContext('2d');
    let gradient = null;
    if (ctx) {
        gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(0, 229, 255, 0.5)');
        gradient.addColorStop(1, 'rgba(0, 229, 255, 0.0)');
    }

    this.instanceCpuChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'CPU Usage %',
          data: data,
          borderColor: '#00e5ff',
          backgroundColor: gradient || 'rgba(0, 229, 255, 0.2)',
          borderWidth: 2,
          pointBackgroundColor: '#00e5ff',
          pointBorderColor: '#000',
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.8)',
            titleColor: '#fff',
            bodyColor: '#00e5ff',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: 'rgba(255,255,255,0.5)' }
          },
          x: {
            grid: { display: false },
            ticks: { color: 'rgba(255,255,255,0.5)', maxRotation: 45, minRotation: 45 }
          }
        }
      }
    });
  }

  loadTelemetryOverview() {
    this.isTelemetryLoading = true;
    this.dbaService.getTelemetryOverview(this.selectedTimeRange, this.customStartDate, this.customEndDate).subscribe({
      next: (data) => {
        this.telemetryData = data;
        this.isTelemetryLoading = false;
        setTimeout(() => {
          this.renderTelemetryCharts(data);
          if (this.zoomedChartType) {
            this.renderZoomedChart();
          }
        }, 150);
      },
      error: (err) => {
        console.error('Error fetching telemetry overview', err);
        this.isTelemetryLoading = false;
      }
    });
  }

  setAutoRefresh(seconds: number) {
    this.autoRefreshInterval = seconds;
    this.autoRefreshCountdown = seconds;
    if (this.autoRefreshTimer) {
      clearInterval(this.autoRefreshTimer);
      this.autoRefreshTimer = null;
    }
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }

    if (seconds > 0) {
      this.toast.info(`Auto-refresco activado cada ${seconds}s.`, 'Monitor en Vivo');
      this.countdownTimer = setInterval(() => {
        if (this.autoRefreshCountdown > 1) {
          this.autoRefreshCountdown--;
        } else {
          this.autoRefreshCountdown = seconds;
        }
      }, 1000);

      this.autoRefreshTimer = setInterval(() => {
        this.loadTelemetryOverview();
      }, seconds * 1000);
    } else {
      this.toast.info('Auto-refresco en pausa.', 'Pausado');
    }
  }

  exportCurrentTableToCsv(title?: string) {
    const data = this.getActionData();
    if (!data || !Array.isArray(data) || !data.length) {
      this.toast.warning('No hay datos tabulares para exportar.');
      return;
    }
    const keys = Object.keys(data[0]);
    const headers = keys.join(',');
    const rows = data.map(row => 
      keys.map(k => `"${(row[k] !== null && row[k] !== undefined ? String(row[k]) : '').replace(/"/g, '""')}"`).join(',')
    );
    const csvContent = '\uFEFF' + [headers, ...rows].join('\r\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const tabName = title || this.activeTab || 'datacheck';
    const filename = `datacheck_${tabName.toLowerCase().replace(/\s+/g, '_')}_${new Date().toISOString().slice(0, 10)}.csv`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    this.toast.success(`Datos descargados: ${filename}`, 'CSV Exportado');
  }

  copyQuerySql(sql: string) {
    if (!sql) return;
    navigator.clipboard.writeText(sql).then(() => {
      this.toast.success('Consulta SQL copiada al portapapeles.', 'Copiado');
    }).catch(() => {
      this.toast.info(sql, 'Consulta SQL');
    });
  }

  setTimeRange(range: string) {
    this.selectedTimeRange = range;
    if (range === 'custom') {
      this.showCustomRange = true;
      if (!this.customStartDate || !this.customEndDate) {
        const today = new Date();
        const past = new Date();
        past.setDate(today.getDate() - 7);
        this.customEndDate = today.toISOString().split('T')[0];
        this.customStartDate = past.toISOString().split('T')[0];
      }
    } else {
      this.showCustomRange = false;
      this.loadTelemetryOverview();
    }
  }

  applyCustomRange() {
    if (this.customStartDate && this.customEndDate) {
      this.loadTelemetryOverview();
    }
  }

  openChartZoom(type: 'cpu' | 'waits' | 'blocking' | 'throughput') {
    this.zoomedChartType = type;
    const data = this.telemetryData;
    if (type === 'cpu') {
      this.zoomedChartTitle = 'Consumo de CPU en el Tiempo';
      this.zoomedChartBadge = 'Línea de Base';
      this.zoomedChartColor = '#00e5ff';
      const series = data?.cpu_series || [];
      const maxVal = series.length ? Math.max(...series) : 0;
      const minVal = series.length ? Math.min(...series) : 0;
      const avgVal = series.length ? (series.reduce((a: number, b: number) => a + b, 0) / series.length).toFixed(1) : '0';
      this.zoomedChartStats = [
        { label: 'Pico Máximo', value: `${maxVal}%` },
        { label: 'Mínimo', value: `${minVal}%` },
        { label: 'Promedio', value: `${avgVal}%` },
        { label: 'Último Valor', value: `${series[series.length - 1] || 0}%` },
      ];
    } else if (type === 'waits') {
      this.zoomedChartTitle = 'Distribución de Tipos de Espera (Top Wait Stats)';
      this.zoomedChartBadge = 'Filtro Benigno';
      this.zoomedChartColor = '#f59e0b';
      const series = data?.wait_series || [];
      const totalWait = series.reduce((a: number, b: number) => a + b, 0);
      this.zoomedChartStats = [
        { label: 'Tiempo Total Espera', value: `${totalWait.toLocaleString()} ms` },
        { label: 'Tipo Principal', value: data?.wait_types?.[0] || 'N/A' },
        { label: 'Categorías Rastreadas', value: `${series.length}` },
      ];
    } else if (type === 'blocking') {
      this.zoomedChartTitle = 'Histórico de Bloqueos y Deadlocks';
      this.zoomedChartBadge = 'Contención de Recursos';
      this.zoomedChartColor = '#ef4444';
      const series = data?.blocking_series || [];
      const totalBlocks = series.reduce((a: number, b: number) => a + b, 0);
      this.zoomedChartStats = [
        { label: 'Total Eventos Registrados', value: `${totalBlocks}` },
        { label: 'Bloqueos Activos Ahora', value: `${data?.kpis?.active_blocks || 0}` },
        { label: 'Deadlocks (24h)', value: `${data?.kpis?.deadlocks_24h || 0}` },
      ];
    } else if (type === 'throughput') {
      this.zoomedChartTitle = 'Throughput: Batch Requests & Transacciones / seg';
      this.zoomedChartBadge = 'Throughput Activo';
      this.zoomedChartColor = '#10b981';
      const series = data?.throughput_series || [];
      const maxVal = series.length ? Math.max(...series) : 0;
      const minVal = series.length ? Math.min(...series) : 0;
      const avgVal = series.length ? (series.reduce((a: number, b: number) => a + b, 0) / series.length).toFixed(0) : '0';
      this.zoomedChartStats = [
        { label: 'Pico Máximo', value: `${maxVal} req/s` },
        { label: 'Mínimo', value: `${minVal} req/s` },
        { label: 'Promedio Estimado', value: `${avgVal} req/s` },
      ];
    }

    setTimeout(() => this.renderZoomedChart(), 120);
  }

  closeChartZoom() {
    if (this.zoomedChartInstance) {
      try { this.zoomedChartInstance.destroy(); } catch (e) {}
      this.zoomedChartInstance = null;
    }
    this.zoomedChartType = null;
  }

  renderZoomedChart() {
    if (!this.zoomedChartType || !this.telemetryData) return;
    const canvas = document.getElementById('zoomedCanvas') as HTMLCanvasElement;
    if (!canvas) return;

    if (this.zoomedChartInstance) {
      try { this.zoomedChartInstance.destroy(); } catch (e) {}
      this.zoomedChartInstance = null;
    }

    const data = this.telemetryData;
    const ctx = canvas.getContext('2d');

    if (this.zoomedChartType === 'cpu') {
      let grad = null;
      if (ctx) {
        grad = ctx.createLinearGradient(0, 0, 0, 450);
        grad.addColorStop(0, 'rgba(0, 229, 255, 0.45)');
        grad.addColorStop(1, 'rgba(0, 229, 255, 0.0)');
      }
      this.zoomedChartInstance = new Chart(canvas, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label: 'Consumo CPU %',
            data: data.cpu_series,
            borderColor: '#00e5ff',
            backgroundColor: grad || 'rgba(0, 229, 255, 0.2)',
            borderWidth: 2.5,
            pointBackgroundColor: '#00e5ff',
            pointBorderColor: '#0f172a',
            pointRadius: 4,
            pointHoverRadius: 8,
            fill: true,
            tension: 0.35
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              titleColor: '#fff',
              bodyColor: '#00e5ff',
              padding: 12,
              displayColors: false,
              callbacks: { label: (ctx: any) => `CPU: ${ctx.parsed.y}%` }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              grid: { color: 'rgba(255, 255, 255, 0.08)' },
              ticks: { color: 'rgba(255, 255, 255, 0.7)', callback: (v: any) => v + '%' }
            },
            x: {
              grid: { color: 'rgba(255, 255, 255, 0.04)' },
              ticks: { color: 'rgba(255, 255, 255, 0.7)', maxRotation: 45 }
            }
          }
        }
      });
    } else if (this.zoomedChartType === 'waits') {
      this.zoomedChartInstance = new Chart(canvas, {
        type: 'bar',
        data: {
          labels: data.wait_types,
          datasets: [{
            label: 'Tiempo de Espera (ms)',
            data: data.wait_series,
            backgroundColor: [
              'rgba(245, 158, 11, 0.85)',
              'rgba(59, 130, 246, 0.85)',
              'rgba(239, 68, 68, 0.85)',
              'rgba(16, 185, 129, 0.85)',
              'rgba(139, 92, 246, 0.85)',
              'rgba(14, 165, 233, 0.85)'
            ],
            borderRadius: 8
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              titleColor: '#fff',
              bodyColor: '#fbbf24',
              padding: 12,
              callbacks: { label: (ctx: any) => `Espera: ${ctx.parsed.y.toLocaleString()} ms` }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(255, 255, 255, 0.08)' },
              ticks: { color: 'rgba(255, 255, 255, 0.7)', callback: (v: any) => v.toLocaleString() + ' ms' }
            },
            x: {
              grid: { display: false },
              ticks: { color: 'rgba(255, 255, 255, 0.8)', maxRotation: 25 }
            }
          }
        }
      });
    } else if (this.zoomedChartType === 'blocking') {
      let grad = null;
      if (ctx) {
        grad = ctx.createLinearGradient(0, 0, 0, 450);
        grad.addColorStop(0, 'rgba(239, 68, 68, 0.45)');
        grad.addColorStop(1, 'rgba(239, 68, 68, 0.0)');
      }
      this.zoomedChartInstance = new Chart(canvas, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label: 'Eventos de Contención',
            data: data.blocking_series,
            borderColor: '#ef4444',
            backgroundColor: grad || 'rgba(239, 68, 68, 0.2)',
            borderWidth: 2.5,
            stepped: true,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              titleColor: '#fff',
              bodyColor: '#f87171',
              padding: 12
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(255, 255, 255, 0.08)' },
              ticks: { color: 'rgba(255, 255, 255, 0.7)', stepSize: 1 }
            },
            x: {
              grid: { display: false },
              ticks: { color: 'rgba(255, 255, 255, 0.7)', maxRotation: 45 }
            }
          }
        }
      });
    } else if (this.zoomedChartType === 'throughput') {
      let grad = null;
      if (ctx) {
        grad = ctx.createLinearGradient(0, 0, 0, 450);
        grad.addColorStop(0, 'rgba(16, 185, 129, 0.45)');
        grad.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
      }
      this.zoomedChartInstance = new Chart(canvas, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label: 'Batch Requests / seg',
            data: data.throughput_series,
            borderColor: '#10b981',
            backgroundColor: grad || 'rgba(16, 185, 129, 0.2)',
            borderWidth: 2.5,
            pointBackgroundColor: '#10b981',
            pointRadius: 4,
            fill: true,
            tension: 0.35
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              titleColor: '#fff',
              bodyColor: '#34d399',
              padding: 12
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(255, 255, 255, 0.08)' },
              ticks: { color: 'rgba(255, 255, 255, 0.7)' }
            },
            x: {
              grid: { display: false },
              ticks: { color: 'rgba(255, 255, 255, 0.7)', maxRotation: 45 }
            }
          }
        }
      });
    }
  }

  downloadZoomedChartPng() {
    const canvas = document.getElementById('zoomedCanvas') as HTMLCanvasElement;
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `datacheck-${this.zoomedChartType || 'chart'}-${this.selectedTimeRange}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }

  destroyTelemetryCharts() {
    if (this.telemetryCpuChart) {
      try { this.telemetryCpuChart.destroy(); } catch (e) {}
      this.telemetryCpuChart = null;
    }
    if (this.telemetryWaitsChart) {
      try { this.telemetryWaitsChart.destroy(); } catch (e) {}
      this.telemetryWaitsChart = null;
    }
    if (this.telemetryBlockingChart) {
      try { this.telemetryBlockingChart.destroy(); } catch (e) {}
      this.telemetryBlockingChart = null;
    }
    if (this.telemetryThroughputChart) {
      try { this.telemetryThroughputChart.destroy(); } catch (e) {}
      this.telemetryThroughputChart = null;
    }
  }

  renderTelemetryCharts(data: any) {
    if (!data) return;
    this.destroyTelemetryCharts();

    // 1. CPU Telemetry Chart (24h)
    const cpuCanvas = document.getElementById('telemetryCpuCanvas') as HTMLCanvasElement;
    if (cpuCanvas) {
      const ctx = cpuCanvas.getContext('2d');
      let gradient = null;
      if (ctx) {
        gradient = ctx.createLinearGradient(0, 0, 0, 260);
        gradient.addColorStop(0, 'rgba(0, 229, 255, 0.45)');
        gradient.addColorStop(1, 'rgba(0, 229, 255, 0.0)');
      }
      this.telemetryCpuChart = new Chart(cpuCanvas, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label: 'Consumo CPU %',
            data: data.cpu_series,
            borderColor: '#00e5ff',
            backgroundColor: gradient || 'rgba(0, 229, 255, 0.2)',
            borderWidth: 2.2,
            pointBackgroundColor: '#00e5ff',
            pointBorderColor: '#12131a',
            pointRadius: 2.5,
            pointHoverRadius: 6,
            fill: true,
            tension: 0.35
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              titleColor: '#fff',
              bodyColor: '#00e5ff',
              borderColor: 'rgba(255, 255, 255, 0.1)',
              borderWidth: 1,
              padding: 10
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: 'rgba(255, 255, 255, 0.5)', callback: (v: any) => v + '%' }
            },
            x: {
              grid: { display: false },
              ticks: { color: 'rgba(255, 255, 255, 0.5)', maxTicksLimit: 12 }
            }
          }
        }
      });
    }

    // 2. Wait Stats Distribution (Top Wait Types)
    const waitsCanvas = document.getElementById('telemetryWaitsCanvas') as HTMLCanvasElement;
    if (waitsCanvas) {
      this.telemetryWaitsChart = new Chart(waitsCanvas, {
        type: 'bar',
        data: {
          labels: data.wait_types,
          datasets: [{
            label: 'Tiempo de Espera (ms)',
            data: data.wait_series,
            backgroundColor: [
              'rgba(245, 158, 11, 0.85)',
              'rgba(59, 130, 246, 0.85)',
              'rgba(239, 68, 68, 0.85)',
              'rgba(16, 185, 129, 0.85)',
              'rgba(139, 92, 246, 0.85)',
              'rgba(14, 165, 233, 0.85)'
            ],
            borderRadius: 6,
            borderSkipped: false
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              titleColor: '#fff',
              bodyColor: '#f59e0b',
              borderColor: 'rgba(255, 255, 255, 0.1)',
              borderWidth: 1,
              padding: 10
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: 'rgba(255, 255, 255, 0.5)' }
            },
            x: {
              grid: { display: false },
              ticks: { color: 'rgba(255, 255, 255, 0.6)', maxRotation: 25, minRotation: 25 }
            }
          }
        }
      });
    }

    // 3. Blocking & Deadlocks Activity (24h)
    const blockingCanvas = document.getElementById('telemetryBlockingCanvas') as HTMLCanvasElement;
    if (blockingCanvas) {
      const ctx = blockingCanvas.getContext('2d');
      let gradient = null;
      if (ctx) {
        gradient = ctx.createLinearGradient(0, 0, 0, 260);
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.45)');
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0.0)');
      }
      this.telemetryBlockingChart = new Chart(blockingCanvas, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label: 'Procesos Bloqueados',
            data: data.blocking_series,
            borderColor: '#ef4444',
            backgroundColor: gradient || 'rgba(239, 68, 68, 0.2)',
            borderWidth: 2,
            stepped: true,
            pointBackgroundColor: '#ef4444',
            pointBorderColor: '#12131a',
            pointRadius: 2.5,
            pointHoverRadius: 6,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              titleColor: '#fff',
              bodyColor: '#ef4444',
              borderColor: 'rgba(255, 255, 255, 0.1)',
              borderWidth: 1,
              padding: 10
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { stepSize: 1, color: 'rgba(255, 255, 255, 0.5)' },
              grid: { color: 'rgba(255, 255, 255, 0.05)' }
            },
            x: {
              grid: { display: false },
              ticks: { color: 'rgba(255, 255, 255, 0.5)', maxTicksLimit: 12 }
            }
          }
        }
      });
    }

    // 4. Transactions & Batch Requests / Throughput (24h)
    const throughputCanvas = document.getElementById('telemetryThroughputCanvas') as HTMLCanvasElement;
    if (throughputCanvas) {
      const ctx = throughputCanvas.getContext('2d');
      let gradient = null;
      if (ctx) {
        gradient = ctx.createLinearGradient(0, 0, 0, 260);
        gradient.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
      }
      this.telemetryThroughputChart = new Chart(throughputCanvas, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [{
            label: 'Batch Requests / Transacciones x seg',
            data: data.throughput_series,
            borderColor: '#10b981',
            backgroundColor: gradient || 'rgba(16, 185, 129, 0.2)',
            borderWidth: 2,
            pointBackgroundColor: '#10b981',
            pointBorderColor: '#12131a',
            pointRadius: 2.5,
            pointHoverRadius: 5,
            fill: true,
            tension: 0.35
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              titleColor: '#fff',
              bodyColor: '#10b981',
              borderColor: 'rgba(255, 255, 255, 0.1)',
              borderWidth: 1,
              padding: 10
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: 'rgba(255, 255, 255, 0.5)' }
            },
            x: {
              grid: { display: false },
              ticks: { color: 'rgba(255, 255, 255, 0.5)', maxTicksLimit: 12 }
            }
          }
        }
      });
    }
  }

  openIncidentsPortal(): void {
    this.router.navigate(['/admin/incidents']);
  }
}
