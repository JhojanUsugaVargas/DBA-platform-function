import { Injectable, PLATFORM_ID, Inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';
import { UserProfile } from '../models';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  requires_mfa: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly baseUrl = environment.apiUrl;
  private readonly TOKEN_KEY = 'access_token';

  constructor(
    private http: HttpClient,
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  login(username: string, password: string): Observable<LoginResponse> {
    const body = new URLSearchParams();
    body.set('username', username);
    body.set('password', password);

    return this.http.post<LoginResponse>(
      `${this.baseUrl}/auth/login`,
      body.toString(),
      {
        headers: new HttpHeaders().set('Content-Type', 'application/x-www-form-urlencoded')
      }
    );
  }

  sendOtp(username: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.baseUrl}/auth/send-otp?username=${encodeURIComponent(username)}`,
      {}
    );
  }

  verifyOtp(username: string, code: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(
      `${this.baseUrl}/auth/verify-otp`,
      { username, code }
    );
  }

  setToken(token: string): void {
    if (isPlatformBrowser(this.platformId)) {
      localStorage.setItem(this.TOKEN_KEY, token);
    }
  }

  getToken(): string | null {
    if (isPlatformBrowser(this.platformId)) {
      return localStorage.getItem(this.TOKEN_KEY);
    }
    return null;
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  getStoredUsername(): string {
    const token = this.getToken();
    if (!token) return 'User';
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.sub || 'User';
    } catch {
      return 'User';
    }
  }

  logout(): void {
    if (isPlatformBrowser(this.platformId)) {
      localStorage.removeItem(this.TOKEN_KEY);
    }
    this.router.navigate(['/login']);
  }

  getUserRole(): string {
    const token = this.getToken();
    if (!token) return 'Monitor';
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.role || 'Monitor';
    } catch {
      return 'Monitor';
    }
  }

  isAdmin(): boolean {
    const role = (this.getUserRole() || '').toLowerCase();
    const user = (this.getStoredUsername() || '').toLowerCase();
    return role === 'administrador' || role === 'admin' || user === 'admin';
  }

  isDbaPrincipal(): boolean {
    const role = (this.getUserRole() || '').toLowerCase();
    return role === 'dba principal' || role === 'dba';
  }

  canCancelQueries(): boolean {
    return this.isAdmin() || this.isDbaPrincipal();
  }

  canTestInstance(): boolean {
    return this.isAdmin() || this.isDbaPrincipal();
  }

  getProfile(): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${this.baseUrl}/auth/profile/me`);
  }

  updatePassword(data: { old_password: string; new_password: string }): Observable<any> {
    return this.http.put(`${this.baseUrl}/auth/profile/password`, data);
  }

  updatePhoto(data: { photo_base64: string }): Observable<any> {
    return this.http.put(`${this.baseUrl}/auth/profile/photo`, data);
  }

  toggleMfa(data: { mfa_enabled: boolean }): Observable<any> {
    return this.http.put(`${this.baseUrl}/auth/profile/mfa`, data);
  }
}
