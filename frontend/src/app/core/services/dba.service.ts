import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DbaActionResponse } from '../models';

@Injectable({
  providedIn: 'root'
})
export class DbaService {
  private readonly baseUrl = `${environment.apiUrl}/dba`;

  constructor(private http: HttpClient) {}

  getStatus(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/status`);
  }

  getCpu(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/cpu`);
  }

  getDisks(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/discos`);
  }

  getTempDb(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/tempdb`);
  }

  getWhoIsActive(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/whoisactive`);
  }

  getBloqueos(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/bloqueos`);
  }

  getDataLog(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/datalog`);
  }

  getJobs(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/jobs`);
  }

  getAlwaysOn(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/alwayson`);
  }

  getPerformance(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/performance`);
  }

  getWaitStats(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/waitstats`);
  }

  getBloat(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/bloat`);
  }

  getMaintenance(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/maintenance`);
  }

  getPgBloat(): Observable<DbaActionResponse> {
    return this.getBloat();
  }

  getPgAutovacuum(): Observable<DbaActionResponse> {
    return this.getMaintenance();
  }

  getTelemetryOverview(range: string = '24h', startDate?: string, endDate?: string): Observable<any> {
    const params: Record<string, string> = { range };
    if (startDate) params['start_date'] = startDate;
    if (endDate) params['end_date'] = endDate;
    return this.http.get<any>(`${this.baseUrl}/telemetry/overview`, { params });
  }

  getBackups(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/backups`);
  }

  getTopQueries(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/top-queries`);
  }

  cancelSession(spid: string, reason: string): Observable<DbaActionResponse> {
    return this.http.post<DbaActionResponse>(`${this.baseUrl}/cancelar`, { spid, reason });
  }

  getHealthScore(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/health-score`);
  }

  getInstanceHealthScore(instanceId: number): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/instances/${instanceId}/health-score`);
  }

  getMissingIndexes(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/missing-indexes`);
  }

  getConfigDrift(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/config-drift`);
  }

  getMaintenanceWindows(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/maintenance-windows`);
  }

  createMaintenanceWindow(payload: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/maintenance-windows`, payload);
  }

  deleteMaintenanceWindow(id: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/maintenance-windows/${id}`);
  }

  getAlertStats(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/alerts/stats`);
  }

  getSystemAlertsFiltered(params: { unread_only?: boolean; severity?: string; metric?: string; limit?: number }): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/alerts`, { params: params as any });
  }
}
