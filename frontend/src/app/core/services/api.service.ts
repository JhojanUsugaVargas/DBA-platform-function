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

  getInstances(contractId: number): Observable<Instance[]> {
    return this.http.get<Instance[]>(`${this.baseUrl}/dba/instances?contract_id=${contractId}`);
  }

  selectInstance(instanceId: number): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/dba/instances/select?instance_id=${instanceId}`, {});
  }

  // Gestión de Usuarios
  createUser(username: string, role: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/admin/users`, {
      username,
      password: 'ChangeMe123!',
      role
    });
  }

  // Métricas Históricas
  getHistoricalCpu(contractId: number): Observable<HistoricalCpuData> {
    return this.http.get<HistoricalCpuData>(`${this.baseUrl}/dba/history/cpu?contract_id=${contractId}`);
  }

  // Feedback y Calificaciones
  submitFeedback(rating: number, comment: string): Observable<any> {
    return this.http.post<any>(
      `${this.baseUrl}/feedback/submit?rating=${rating}&comment=${encodeURIComponent(comment)}`,
      {}
    );
  }

  // Perfil de Usuario
  getProfile(): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${this.baseUrl}/auth/profile/me`);
  }

  updatePassword(data: { old_password: string; new_password: string }): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/auth/profile/password`, data);
  }

  updatePhoto(data: { photo_base64: string }): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/auth/profile/photo`, data);
  }

  toggleMfa(data: { mfa_enabled: boolean }): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/auth/profile/mfa`, data);
  }
}
