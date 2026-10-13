import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { trigger, transition, style, animate, query, stagger } from '@angular/animations';
import { ApiService } from '../../core/services/api.service';
import { DbaService } from '../../core/services/dba.service';
import { ChatService } from '../../core/services/chat.service';

declare var Chart: any;

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
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
  canCancelQueries: boolean = false;

  // Darling Web / PerformanceMonitor Telemetry State & Tabs
  activeTab: string = 'overview';
  telemetryData: any = null;
  isTelemetryLoading: boolean = false;
  telemetryCpuChart: any = null;
  telemetryWaitsChart: any = null;
  telemetryBlockingChart: any = null;
  telemetryThroughputChart: any = null;

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

  // Audit Logs Modal
  isAuditModalOpen: boolean = false;
  auditLogs: any[] = [];
  isAuditLoading: boolean = false;

  // Maintenance & System Adjustments Animation & Granular Lockout
  isMaintenanceActive: boolean = false;
  maintenanceTitle: string = 'Ajustes del Sistema en Progreso';
  maintenanceSubtitle: string = 'Optimizando motores de bases de datos, reindexando y aplicando configuraciones DBA...';
  maintenanceProgress: number = 68;
  isAdmin: boolean = false;
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
    { key: 'datalog', label: 'Validar Data y Log', icon: '🔍' },
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
    private chatService: ChatService
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
      alert('Ingresa el nombre del contrato.');
      return;
    }
    this.isCreatingContract = true;
    this.apiService.createContract(this.newContractName.trim()).subscribe({
      next: (res) => {
        alert(`Contrato '${this.newContractName}' creado exitosamente.`);
        this.isCreatingContract = false;
        this.closeContractModal();
        this.loadContracts();
      },
      error: (err) => {
        alert(err.error?.detail || 'Error al crear contrato');
        this.isCreatingContract = false;
      }
    });
  }

  openEditContractModal(contract?: any) {
    const c = contract || this.contracts.find(item => item.id === this.selectedContractId);
    if (!c) {
      alert('Por favor selecciona un contrato para editar.');
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
      alert('Ingresa un nombre válido para el contrato.');
      return;
    }
    this.isUpdatingContract = true;
    this.apiService.updateContract(this.editingContractId, this.editingContractName.trim()).subscribe({
      next: (res) => {
        alert(`Contrato actualizado exitosamente a '${this.editingContractName}'.`);
        this.isUpdatingContract = false;
        this.closeEditContractModal();
        this.loadContracts();
      },
      error: (err) => {
        alert(err.error?.detail || 'Error al actualizar el contrato');
        this.isUpdatingContract = false;
      }
    });
  }

  confirmDeleteContract(contractId?: number, contractName?: string) {
    const cid = contractId || this.selectedContractId;
    if (!cid) {
      alert('Por favor selecciona un contrato para eliminar.');
      return;
    }
    const c = this.contracts.find(item => item.id === cid);
    const name = contractName || (c ? c.name : `ID ${cid}`);

    if (confirm(`¿Estás seguro de eliminar el contrato "${name}" y desactivar sus instancias asociadas?`)) {
      this.apiService.deleteContract(cid).subscribe({
        next: () => {
          alert(`Contrato "${name}" eliminado correctamente.`);
          if (this.selectedContractId === cid) {
            this.selectedContractId = null;
          }
          this.loadContracts();
        },
        error: (err) => {
          alert(err.error?.detail || 'Error al eliminar el contrato.');
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
      alert('Por favor completa Nombre, Servidor/Host y Base de Datos.');
      return;
    }
    const contractId = this.newInstance.contractId || this.selectedContractId;
    if (!contractId) {
      alert('Debes seleccionar un contrato para la instancia.');
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
        alert(`Instancia '${this.newInstance.name}' registrada correctamente.`);
        this.isCreatingInstance = false;
        this.closeInstanceModal();
        this.loadInstances();
      },
      error: (err) => {
        alert(err.error?.detail || 'Error al registrar instancia');
        this.isCreatingInstance = false;
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
        if (res.role) {
          this.currentUserRole = res.role;
          this.isAdmin = (res.role === 'Administrador') || (this.currentUser === 'admin');
          this.canCancelQueries = this.isAdmin || (res.role === 'DBA Principal');
        }
      },
      error: (err) => console.error("Error loading profile", err)
    });
  }

  onPhotoSelected(event: any) {
    const file = event.target.files?.[0];
    if (file) {
      if (file.size > 3 * 1024 * 1024) {
        alert('⚠️ La imagen seleccionada es muy pesada (máximo 3 MB). Por favor selecciona una imagen más liviana.');
        return;
      }
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.profilePhotoUrl = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  }

  removePhoto() {
    this.profilePhotoUrl = '';
  }

  saveProfileChanges() {
    this.isSavingProfile = true;
    
    // Save MFA
    this.apiService.toggleMfa({ mfa_enabled: this.profileForm.mfaEnabled }).subscribe({
      next: () => {},
      error: (err) => console.error("Error saving MFA", err)
    });

    // Save Photo if changed or removed
    if (this.profilePhotoUrl !== null && this.profilePhotoUrl !== undefined) {
      this.apiService.updatePhoto({ photo_base64: this.profilePhotoUrl }).subscribe({
        next: () => {},
        error: (err) => console.error("Error saving photo", err)
      });
    }

    // Save Password if filled
    if (this.profileForm.oldPassword && this.profileForm.newPassword) {
      this.apiService.updatePassword({
        old_password: this.profileForm.oldPassword,
        new_password: this.profileForm.newPassword
      }).subscribe({
        next: (res) => {
          alert('✅ Perfil actualizado exitosamente (contraseña y foto guardadas).');
          this.profileForm.oldPassword = '';
          this.profileForm.newPassword = '';
          this.isSavingProfile = false;
          this.closeProfileModal();
        },
        error: (err) => {
          alert(err.error?.detail || 'Error al cambiar contraseña');
          this.isSavingProfile = false;
        }
      });
    } else {
      setTimeout(() => {
        this.isSavingProfile = false;
        alert('✅ Foto de perfil y ajustes guardados con éxito.');
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
      alert('Por seguridad (OWASP), la contraseña debe tener al menos 8 caracteres.');
      return;
    }
    this.isChangingPassword = true;
    this.apiService.changeUserPassword(this.targetUserForPassword.id, this.newPasswordForUser).subscribe({
      next: (res) => {
        alert(`Contraseña actualizada con éxito para el usuario '${this.targetUserForPassword.username}'.`);
        this.isChangingPassword = false;
        this.closeChangePasswordModal();
      },
      error: (err) => {
        alert(err.error?.detail || 'Error al cambiar contraseña');
        this.isChangingPassword = false;
      }
    });
  }

  confirmDeleteUser(user: any) {
    if (user.username === this.currentUser) {
      alert('No puedes eliminar tu propia cuenta en sesión activa.');
      return;
    }
    if (confirm(`¿Estás seguro de eliminar al usuario "${user.username}"?`)) {
      this.apiService.deleteUser(user.id).subscribe({
        next: () => {
          alert(`Usuario "${user.username}" eliminado correctamente.`);
          this.loadUsers();
        },
        error: (err) => {
          alert(err.error?.detail || 'Error al eliminar usuario.');
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
        alert(`Usuario '${this.editingUserForm.username}' actualizado exitosamente.`);
        this.isUpdatingUser = false;
        this.closeEditUserModal();
        this.loadUsers();
      },
      error: (err) => {
        alert(err.error?.detail || 'Error al actualizar usuario.');
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
          alert('Por favor selecciona al menos un botón/módulo a deshabilitar o activa el "Bloqueo Global".');
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
            alert('🛠️ Bloqueo Global Activado:\nTodos los usuarios que no son Administradores tienen la pantalla bloqueada con temporizador en tiempo real.');
          } else {
            alert(`🛠️ Mantenimiento Modular Activado:\nSe han deshabilitado ${modulesToDisable.length} botones específicos. El resto de la base de datos y la plataforma siguen operativos para los usuarios.`);
          }
        } else {
          alert('✅ Modo Mantenimiento DESACTIVADO.\nTodos los módulos y la plataforma han sido restablecidos con normalidad.');
        }
      },
      error: (err) => {
        this.isSavingMaintenanceConfig = false;
        alert(err.error?.detail || 'Error al actualizar configuración de mantenimiento');
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
      alert('Información del sistema copiada al portapapeles.');
    }).catch(() => {
      alert(info);
    });
  }

  // --- Feedback & Export ---
  exportToPDF() {
    window.print();
  }

  openDocs() {
    window.open('https://github.com/arus-com-co/datacheck-docs', '_blank');
  }

  openFeedbackModal() {
    this.feedbackRating = 5;
    this.feedbackComment = '';
    this.isFeedbackModalOpen = true;
  }

  submitFeedback() {
    this.apiService.submitFeedback(this.feedbackRating, this.feedbackComment).subscribe({
      next: (res) => {
        alert("¡Nueva función! Para forzar cancelación de un proceso, simplemente pídeselo a DataCheck AI en el chat de la esquina inferior derecha. Ej: 'matar 55'");
        this.isFeedbackModalOpen = false;
      },
      error: (err) => {
        alert("Error enviando feedback: " + (err.error?.detail || err.message));
      }
    });
  }

  submitUser() {
    if (!this.newUser.username.trim()) {
      alert("Por favor ingresa un nombre de usuario.");
      return;
    }
    this.isCreatingUser = true;
    const payload = {
      username: this.newUser.username.trim(),
      full_name: this.newUser.full_name.trim() || this.newUser.username.trim(),
      email: this.newUser.email.trim() || undefined,
      password: this.newUser.password.trim() || undefined,
      role: this.newUser.role
    };

    this.apiService.createUser(payload).subscribe({
      next: (res) => {
        let msg = `Usuario '${payload.username}' creado con éxito.`;
        if (res.invitation && res.invitation.sent) {
          msg += `\n📧 Se despachó el correo de invitación a ${payload.email} con las credenciales de acceso.`;
        } else if (payload.password) {
          msg += `\nContraseña configurada: ${payload.password}`;
        }
        alert(msg);
        this.isCreatingUser = false;
        this.userManagementTab = 'list';
        this.loadUsers();
      },
      error: (err) => {
        alert(err.error?.detail || "Error al crear usuario");
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
            if (payload.role) {
                this.currentUserRole = payload.role;
            }
            this.isAdmin = (this.currentUserRole === 'Administrador') || (payload.role === 'Administrador') || (this.currentUser === 'admin');
            this.canCancelQueries = this.isAdmin || (this.currentUserRole === 'DBA Principal') || (payload.role === 'DBA Principal');
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
      alert(`⚠️ La función '${tab.toUpperCase()}' se encuentra temporalmente deshabilitada por mantenimiento técnico. El resto del sistema y la base de datos continúan operativos.`);
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

  runAction(actionName: string) {
    if (!this.isAdmin && this.isModuleDisabled(actionName)) {
      alert(`⚠️ La acción '${actionName.toUpperCase()}' está en mantenimiento técnico.`);
      return;
    }
    if (!this.selectedInstanceId) {
      alert("Por favor, selecciona una instancia primero.");
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
      case 'cancelar': 
        this.isLoadingAction = false;
        if (!this.canCancelQueries) {
          alert('⛔ Permisos insuficientes: Solo el Administrador y el DBA Principal tienen autorización para forzar la cancelación de consultas y procesos.');
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
    this.dbaService.getTelemetryOverview().subscribe({
      next: (data) => {
        this.telemetryData = data;
        this.isTelemetryLoading = false;
        setTimeout(() => this.renderTelemetryCharts(data), 150);
      },
      error: (err) => {
        console.error('Error fetching telemetry overview', err);
        this.isTelemetryLoading = false;
      }
    });
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
