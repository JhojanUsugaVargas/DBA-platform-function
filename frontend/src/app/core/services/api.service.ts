import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Contract, Instance, HistoricalCpuData, UserProfile } from '../models';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Contratos e Instancias
  getContracts(): Observable<Contract[]> {
    return this.http.get<Contract[]>(`${this.baseUrl}/admin/contracts`);
  }

  createContract(name: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/contracts`, { name });
  }

  updateContract(id: number, name: string): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/admin/contracts/${id}`, { name });
  }

  deleteContract(id: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/admin/contracts/${id}`);
  }

  getInstances(contractId: number): Observable<Instance[]> {
    return this.http.get<Instance[]>(`${this.baseUrl}/dba/instances?contract_id=${contractId}`);
  }

  createInstance(contractId: number, name: string, connStr: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/instances`, {
      contract_id: contractId,
      name,
      conn_str: connStr
    });
  }

  selectInstance(instanceId: number): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/dba/instances/select?instance_id=${instanceId}`, {});
  }

  testInstanceConnection(instanceId: number): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/instances/${instanceId}/test`, {});
  }

  testConnectionString(connStr: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/instances/test-connection`, { conn_str: connStr });
  }


  // Gestión de Usuarios
  getUsers(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/admin/users/all`);
  }

  createUser(userData: { username: string; role: string; email?: string; password?: string; full_name?: string; consent_confirmed?: boolean }): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/users`, userData);
  }

  changeUserPassword(userId: number, newPassword: string): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/admin/users/${userId}/password`, {
      new_password: newPassword
    });
  }

  updateUser(userId: number, userData: { full_name?: string; email?: string; role?: string }): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/admin/users/${userId}`, userData);
  }

  deleteUser(userId: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/admin/users/${userId}`);
  }

  resendUserInvitation(userId: number, newPassword?: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/users/${userId}/resend-invitation`, {
      new_password: newPassword
    });
  }

  getSmtpStatus(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/admin/system/smtp-status`);
  }

  // Mantenimiento Global
  getMaintenanceStatus(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/admin/system/maintenance`);
  }

  setMaintenanceStatus(data: { is_active: boolean; title?: string; subtitle?: string; disabled_modules?: string[] }): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/system/maintenance`, data);
  }

  // Auditoría
  getAuditLogs(action?: string): Observable<any[]> {
    let url = `${this.baseUrl}/admin/audit-logs`;
    if (action) {
      url += `?action=${action}`;
    }
    return this.http.get<any[]>(url);
  }

  // Métricas Históricas
  getHistoricalCpu(contractId: number): Observable<HistoricalCpuData> {
    return this.http.get<HistoricalCpuData>(`${this.baseUrl}/dba/history/cpu?contract_id=${contractId}`);
  }

  // Feedback y Calificaciones
  submitFeedback(rating: number, comment: string, consentConfirmed: boolean): Observable<any> {
    // El comentario es texto libre: va en el cuerpo, nunca en la URL
    return this.http.post<any>(`${this.baseUrl}/feedback/submit`, {
      rating,
      comment,
      consent_confirmed: consentConfirmed
    });
  }

  // Perfil de Usuario
  getProfile(): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${this.baseUrl}/auth/profile/me`);
  }

  updatePassword(data: { old_password: string; new_password: string }): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/auth/profile/password`, data);
  }

  updatePhoto(data: { photo_base64: string; rights_confirmed?: boolean }): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/auth/profile/photo`, data);
  }

  // Derechos del titular (Ley 1581 de 2012)
  acceptLegalDocuments(): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/profile/consent`, {});
  }

  exportMyData(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/auth/profile/export`);
  }

  deleteMyAccount(password: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/profile/delete-account`, { password });
  }

  setEmailOptOut(optOut: boolean): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/auth/profile/email-preferences?opt_out=${optOut}`, {});
  }

  toggleMfa(data: { mfa_enabled: boolean }): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/auth/profile/mfa`, data);
  }

  // Gestión Administrativa de Incidentes y Requerimientos (Sin tocar BD directamente)
  getIncidents(status?: string, ticketType?: string, search?: string): Observable<{ incidents: any[]; stats: any }> {
    let params: string[] = [];
    if (status && status !== 'todos') params.push(`status=${encodeURIComponent(status)}`);
    if (ticketType && ticketType !== 'todos') params.push(`ticket_type=${encodeURIComponent(ticketType)}`);
    if (search && search.trim()) params.push(`search=${encodeURIComponent(search.trim())}`);
    
    const query = params.length > 0 ? `?${params.join('&')}` : '';
    return this.http.get<{ incidents: any[]; stats: any }>(`${this.baseUrl}/admin/incidents${query}`);
  }

  createIncident(data: {
    ticket_type: string;
    module: string;
    priority: string;
    description: string;
    status?: string;
    notes?: string;
    username?: string;
  }): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/incidents`, data);
  }

  updateIncident(id: number, data: {
    status?: string;
    notes?: string;
    priority?: string;
    module?: string;
    ticket_type?: string;
    description?: string;
  }): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/admin/incidents/${id}`, data);
  }

  deleteIncident(id: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/admin/incidents/${id}`);
  }

  // Alertas Proactivas y Notificaciones
  getAlerts(unreadOnly: boolean = false, limit: number = 50): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/dba/alerts?unread_only=${unreadOnly}&limit=${limit}`);
  }

  getUnreadAlertsCount(): Observable<{ unread_count: number }> {
    return this.http.get<{ unread_count: number }>(`${this.baseUrl}/dba/alerts/unread-count`);
  }

  markAlertRead(alertId: number): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/dba/alerts/${alertId}/read`, {});
  }

  markAllAlertsRead(): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/dba/alerts/mark-all-read`, {});
  }

  deleteAlert(alertId: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/dba/alerts/${alertId}`);
  }

  // Copiloto IA: Diagnóstico de Consultas Lentas
  diagnoseQuery(payload: {
    query_text: string;
    engine?: string;
    execution_count?: number;
    cpu_total_ms?: number;
    logical_reads?: number;
  }): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/dba/queries/diagnose`, payload);
  }

  // Copiloto IA: Sugerencia de Solución para Tickets
  suggestIncidentSolution(incidentId: number): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/incidents/${incidentId}/suggest-solution`, {});
  }

  suggestDraftSolution(payload: {
    title: string;
    description: string;
    module?: string;
    priority?: string;
    ticket_type?: string;
  }): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/incidents/suggest-solution`, payload);
  }

  // Purga Manual de Telemetría
  purgeTelemetry(days?: number): Observable<any> {
    const url = days ? `${this.baseUrl}/admin/system/purge-telemetry?days=${days}` : `${this.baseUrl}/admin/system/purge-telemetry`;
    return this.http.post<any>(url, {});
  }
}
