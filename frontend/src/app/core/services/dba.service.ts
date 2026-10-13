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

  getTelemetryOverview(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/telemetry/overview`);
  }

  getBackups(): Observable<DbaActionResponse> {
    return this.http.get<DbaActionResponse>(`${this.baseUrl}/backups`);
  }
}
