import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-incident-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './incident-management.component.html',
  styleUrls: ['./incident-management.component.scss']
})
export class IncidentManagementComponent implements OnInit {
  incidents: any[] = [];
  filteredIncidents: any[] = [];
  stats: any = {
    total: 0,
    open: 0,
    in_progress: 0,
    resolved: 0,
    closed: 0,
    incidents_count: 0,
    requirements_count: 0
  };

  isLoading: boolean = false;
  searchQuery: string = '';
  filterType: string = 'todos';
  filterStatus: string = 'todos';
  filterPriority: string = 'todos';

  currentUser: string = 'Administrador';
  availableUsers: any[] = [];

  // Create Modal
  isCreateModalOpen: boolean = false;
  isSubmittingCreate: boolean = false;
  newTicket = {
    ticket_type: 'Incidente',
    module: 'Base de Datos',
    priority: 'Media',
    description: '',
    status: 'Abierto',
    notes: '',
    username: ''
  };

  // Edit / Resolve Modal
  isEditModalOpen: boolean = false;
  isSubmittingEdit: boolean = false;
  selectedTicket: any = null;
  editForm = {
    id: 0,
    status: 'Abierto',
    notes: '',
    priority: 'Media',
    module: 'General',
    ticket_type: 'Incidente',
    description: ''
  };

  // View Details Modal
  isViewModalOpen: boolean = false;
  viewingTicket: any = null;

  // Toast feedback
  toastMessage: string = '';
  toastType: 'success' | 'error' | 'info' = 'success';
  private toastTimeout: any;

  constructor(
    private apiService: ApiService,
    private router: Router
  ) {}

  ngOnInit(): void {
    const token = localStorage.getItem('access_token');
    if (!token) {
      this.router.navigate(['/login']);
      return;
    }
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      this.currentUser = payload.sub || 'Administrador';
    } catch {}

    this.loadIncidents();
    this.loadUsers();
  }

  loadIncidents(): void {
    this.isLoading = true;
    this.apiService.getIncidents(this.filterStatus, this.filterType, this.searchQuery).subscribe({
      next: (res) => {
        this.incidents = res.incidents || [];
        this.stats = res.stats || this.stats;
        this.applyLocalFilter();
        this.isLoading = false;
      },
      error: (err) => {
        this.isLoading = false;
        this.showToast(err.error?.detail || 'Error al cargar los incidentes', 'error');
      }
    });
  }

  loadUsers(): void {
    this.apiService.getUsers().subscribe({
      next: (users) => {
        this.availableUsers = users || [];
      },
      error: () => {}
    });
  }

  applyLocalFilter(): void {
    this.filteredIncidents = this.incidents.filter(ticket => {
      // Type filter
      if (this.filterType !== 'todos') {
        if (ticket.ticket_type.toLowerCase() !== this.filterType.toLowerCase()) {
          return false;
        }
      }
      // Status filter
      if (this.filterStatus !== 'todos') {
        if (ticket.status.toLowerCase() !== this.filterStatus.toLowerCase()) {
          return false;
        }
      }
      // Priority filter
      if (this.filterPriority !== 'todos') {
        if (ticket.priority.toLowerCase() !== this.filterPriority.toLowerCase()) {
          return false;
        }
      }
      // Search
      if (this.searchQuery && this.searchQuery.trim()) {
        const q = this.searchQuery.trim().toLowerCase();
        const match =
          ticket.id.toString().includes(q) ||
          (ticket.username && ticket.username.toLowerCase().includes(q)) ||
          (ticket.user_full_name && ticket.user_full_name.toLowerCase().includes(q)) ||
          (ticket.description && ticket.description.toLowerCase().includes(q)) ||
          (ticket.module && ticket.module.toLowerCase().includes(q)) ||
          (ticket.notes && ticket.notes.toLowerCase().includes(q));
        if (!match) return false;
      }
      return true;
    });
  }

  onFilterChange(): void {
    this.applyLocalFilter();
  }

  openCreateModal(): void {
    this.newTicket = {
      ticket_type: 'Incidente',
      module: 'Base de Datos',
      priority: 'Media',
      description: '',
      status: 'Abierto',
      notes: '',
      username: this.currentUser
    };
    this.isCreateModalOpen = true;
  }

  closeCreateModal(): void {
    this.isCreateModalOpen = false;
    this.isSubmittingCreate = false;
  }

  submitCreateTicket(): void {
    if (!this.newTicket.description.trim()) {
      this.showToast('Por favor describe el incidente o requerimiento.', 'error');
      return;
    }

    this.isSubmittingCreate = true;
    this.apiService.createIncident({
      ticket_type: this.newTicket.ticket_type,
      module: this.newTicket.module,
      priority: this.newTicket.priority,
      description: this.newTicket.description.trim(),
      status: this.newTicket.status,
      notes: this.newTicket.notes.trim(),
      username: this.newTicket.username || this.currentUser
    }).subscribe({
      next: (ticket) => {
        this.isSubmittingCreate = false;
        this.closeCreateModal();
        this.showToast(`Ticket #${ticket.id} registrado exitosamente sin tocar la base de datos.`, 'success');
        this.loadIncidents();
      },
      error: (err) => {
        this.isSubmittingCreate = false;
        this.showToast(err.error?.detail || 'Error al registrar el ticket.', 'error');
      }
    });
  }

  openEditModal(ticket: any): void {
    this.selectedTicket = ticket;
    this.editForm = {
      id: ticket.id,
      status: ticket.status || 'Abierto',
      notes: ticket.notes || '',
      priority: ticket.priority || 'Media',
      module: ticket.module || 'General',
      ticket_type: ticket.ticket_type || 'Incidente',
      description: ticket.description || ''
    };
    this.isEditModalOpen = true;
  }

  closeEditModal(): void {
    this.isEditModalOpen = false;
    this.selectedTicket = null;
    this.isSubmittingEdit = false;
  }

  submitUpdateTicket(): void {
    if (!this.editForm.id) return;

    this.isSubmittingEdit = true;
    this.apiService.updateIncident(this.editForm.id, {
      status: this.editForm.status,
      notes: this.editForm.notes.trim(),
      priority: this.editForm.priority,
      module: this.editForm.module,
      ticket_type: this.editForm.ticket_type,
      description: this.editForm.description.trim()
    }).subscribe({
      next: (res) => {
        this.isSubmittingEdit = false;
        this.closeEditModal();
        this.showToast(`Ticket #${this.editForm.id} actualizado exitosamente.`, 'success');
        this.loadIncidents();
      },
      error: (err) => {
        this.isSubmittingEdit = false;
        this.showToast(err.error?.detail || 'Error al actualizar el ticket.', 'error');
      }
    });
  }

  quickStatusChange(ticket: any, newStatus: string): void {
    if (ticket.status === newStatus) return;
    this.apiService.updateIncident(ticket.id, { status: newStatus }).subscribe({
      next: () => {
        ticket.status = newStatus;
        this.showToast(`Ticket #${ticket.id} cambiado a '${newStatus}'.`, 'success');
        this.loadIncidents();
      },
      error: (err) => {
        this.showToast(err.error?.detail || 'Error al actualizar estado.', 'error');
      }
    });
  }

  openViewModal(ticket: any): void {
    this.viewingTicket = ticket;
    this.isViewModalOpen = true;
  }

  closeViewModal(): void {
    this.isViewModalOpen = false;
    this.viewingTicket = null;
  }

  deleteTicket(ticket: any): void {
    if (!confirm(`¿Estás seguro de eliminar permanentemente el Ticket #${ticket.id} (${ticket.ticket_type})?`)) {
      return;
    }

    this.apiService.deleteIncident(ticket.id).subscribe({
      next: () => {
        this.showToast(`Ticket #${ticket.id} eliminado correctamente.`, 'info');
        this.loadIncidents();
      },
      error: (err) => {
        this.showToast(err.error?.detail || 'Error al eliminar el ticket.', 'error');
      }
    });
  }

  goToDashboard(): void {
    this.router.navigate(['/dashboard']);
  }

  getSlaBadge(ticket: any): { label: string; class: string; icon: string } {
    if (ticket.status === 'Resuelto' || ticket.status === 'Cerrado') {
      return { label: 'Resuelto', class: 'sla-done', icon: '✅' };
    }
    if (!ticket.created_at) {
      return { label: 'En Plazo', class: 'sla-ok', icon: '🟢' };
    }
    const createdTime = new Date(ticket.created_at).getTime();
    const hoursElapsed = (Date.now() - createdTime) / (1000 * 60 * 60);

    const prio = (ticket.priority || '').toLowerCase();
    if (prio === 'crítica') {
      if (hoursElapsed > 2) return { label: 'SLA Excedido (>2h)', class: 'sla-breached', icon: '🚨' };
      if (hoursElapsed > 1) return { label: 'SLA En Riesgo (>1h)', class: 'sla-warning', icon: '⚠️' };
    } else if (prio === 'alta') {
      if (hoursElapsed > 4) return { label: 'SLA Excedido (>4h)', class: 'sla-breached', icon: '🚨' };
      if (hoursElapsed > 2) return { label: 'SLA En Riesgo (>2h)', class: 'sla-warning', icon: '⚠️' };
    } else {
      if (hoursElapsed > 8) return { label: 'SLA Excedido (>8h)', class: 'sla-breached', icon: '🚨' };
    }
    return { label: 'En Plazo SLA', class: 'sla-ok', icon: '🟢' };
  }

  exportToCsv(): void {
    if (!this.filteredIncidents.length) {
      this.showToast('No hay tickets para exportar.', 'info');
      return;
    }
    const headers = ['ID', 'Tipo', 'Prioridad', 'Modulo', 'Solicitante', 'Email', 'Estado', 'Descripcion', 'Notas_Agente', 'Fecha_Creacion'];
    const rows = this.filteredIncidents.map(item => [
      item.id,
      `"${(item.ticket_type || '').replace(/"/g, '""')}"`,
      `"${(item.priority || '').replace(/"/g, '""')}"`,
      `"${(item.module || '').replace(/"/g, '""')}"`,
      `"${(item.username || '').replace(/"/g, '""')}"`,
      `"${(item.user_email || '').replace(/"/g, '""')}"`,
      `"${(item.status || '').replace(/"/g, '""')}"`,
      `"${(item.description || '').replace(/"/g, '""')}"`,
      `"${(item.notes || '').replace(/"/g, '""')}"`,
      `"${item.created_at || ''}"`
    ]);

    const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(e => e.join(','))].join('\r\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `reporte_incidentes_dba_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    this.showToast('Reporte CSV generado exitosamente.', 'success');
  }

  showToast(message: string, type: 'success' | 'error' | 'info' = 'success'): void {
    this.toastMessage = message;
    this.toastType = type;
    if (this.toastTimeout) clearTimeout(this.toastTimeout);
    this.toastTimeout = setTimeout(() => {
      this.toastMessage = '';
    }, 4000);
  }
}
