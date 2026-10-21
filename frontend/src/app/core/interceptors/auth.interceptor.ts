import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ToastService } from '../services/toast.service';

/**
 * Functional HTTP Interceptor for Angular 18+.
 * Injects JWT Bearer token into outgoing HTTP requests and handles 401 Session Expiration.
 */
export const authInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const toast = inject(ToastService);
  const token = authService.getToken();

  let outgoing = req;
  if (token && !req.headers.has('Authorization')) {
    outgoing = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(outgoing).pipe(
    catchError((error: HttpErrorResponse) => {
      // If 401 Unauthorized and not the login endpoint, session expired
      if (error.status === 401 && !req.url.includes('/auth/login')) {
        authService.logout();
        toast.warning('Tu sesión ha expirado por inactividad o seguridad. Por favor ingresa de nuevo.', 'Sesión Expirada');
      }
      return throwError(() => error);
    })
  );
};
