import { Component, OnInit } from '@angular/core';
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
export class DashboardComponent implements OnInit {
  contracts: any[] = [];
  instances: any[] = [];
  
  selectedContractId: number | null = null;
  selectedInstanceId: number | null = null;
  
  actionResult: any = null;
  isLoadingAction: boolean = false;
  isLoaded: boolean = false;
  currentUser: string = 'User';
  currentUserInitials: string = 'U'; 

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
  newUser = { username: '', role: 'Monitor (Solo Lectura)' };

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

  constructor(
    private router: Router,
    private apiService: ApiService,
    private dbaService: DbaService,
    private chatService: ChatService
  ) {}

  openUserModal() {
    this.isUserModalOpen = true;
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
      },
      error: (err) => console.error("Error loading profile", err)
    });
  }

  onPhotoSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.profilePhotoUrl = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  }

  saveProfileChanges() {
    this.isSavingProfile = true;
    
    // Save MFA
    this.apiService.toggleMfa({ mfa_enabled: this.profileForm.mfaEnabled }).subscribe({
      next: () => {},
      error: (err) => console.error("Error saving MFA", err)
    });

    // Save Photo if changed
    if (this.profilePhotoUrl && this.profilePhotoUrl.startsWith('data:image')) {
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
          alert('Contraseña actualizada con éxito');
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
        this.closeProfileModal();
      }, 500);
    }
  }

  closeUserModal() {
    this.isUserModalOpen = false;
    this.newUser = { username: '', role: 'Monitor (Solo Lectura)' };

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
    if (!this.newUser.username) {
        alert("Ingresa un nombre de usuario.");
        return;
    }
    this.isCreatingUser = true;
    this.apiService.createUser(this.newUser.username, this.newUser.role).subscribe({
        next: (res) => {
            alert(res.message + " ContraseÃ±a por defecto: ChangeMe123!");
            this.closeUserModal();
            this.isCreatingUser = false;
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
    this.loadChatHistory();
  }

  loadChatHistory() {
    this.chatService.getHistory().subscribe({
      next: (history) => {
        this.chatMessages = history.map(msg => ({ text: msg.content, isUser: true }));
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
        this.chatMessages.push({ text: res.reply || res.message, isUser: false, options: res.options });
        this.scrollToBottom();
      },
      error: (err) => {
        this.isChatLoading = false;
        this.chatMessages.push({ text: "Error de conexiÃ³n con el asistente.", isUser: false, isError: true });
        this.scrollToBottom();
      }
    });
  }

  
  clearChat() {
    this.chatMessages = [];
  }

  scrollToBottom() {
    setTimeout(() => {
      const container = document.querySelector('.chat-messages');
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

  loadContracts() {
    this.apiService.getContracts().subscribe({
      next: (data) => {
        this.contracts = data;
        if (this.contracts.length > 0) {
          this.selectedContractId = this.contracts[0].id;
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
          this.selectedInstanceId = this.instances[0].id;
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
        this.runAction('status');
      },
      error: (err) => console.error(err)
    });
  }

  
  openSupportCenter() {
    this.isChatMinimized = false;
    this.chatInput = "soporte ";
    setTimeout(() => {
      const input = document.querySelector('.chat-input-wrapper input') as HTMLInputElement;
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
        alert("¡Nueva función! Para forzar cancelación de un proceso, simplemente pídeselo a DataCheck AI en el chat de la esquina inferior derecha. Ej: 'matar 55'");
        this.isLoadingAction = false;
        return;
      default: 
        setTimeout(() => {
          this.actionResult = { error: "Acción no implementada temporalmente" };
          this.isLoadingAction = false;
        }, 1000);
        return;
    }

    actionObs.subscribe({
      next: (data) => {
        this.actionResult = { title: data?.title || actionName, data: data };
        this.isLoadingAction = false;
        
        // Trigger chart render if it's the CPU monitor
        if (data.type === 'instance_monitor') {
          this.loadHistoricalCpu();
        }
      },
      error: (err) => {
        this.actionResult = { error: err.error?.detail || "Error ejecutando la consulta" };
        this.isLoadingAction = false;
      }
    });
  }


  // Add Chart methods
  cpuChart: any = null;

  loadHistoricalCpu() {
    if (!this.selectedContractId) return;
    this.apiService.getHistoricalCpu(this.selectedContractId).subscribe({
      next: (res: any) => {
        setTimeout(() => this.renderCpuChart(res.labels, res.data), 100);
      }
    });
  }

  renderCpuChart(labels: string[], data: number[]) {
    const canvas = document.getElementById('cpuChart') as HTMLCanvasElement;
    if (!canvas) return;
    
    if (this.cpuChart) {
      this.cpuChart.destroy();
    }

    const ctx = canvas.getContext('2d');
    
    // Create gradient
    let gradient = null;
    if (ctx) {
        gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(0, 229, 255, 0.5)');
        gradient.addColorStop(1, 'rgba(0, 229, 255, 0.0)');
    }

    this.cpuChart = new Chart(canvas, {
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


}






