import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  message: string;
  duration?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private toastsSubject = new BehaviorSubject<Toast[]>([]);
  public toasts$ = this.toastsSubject.asObservable();

  show(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info', title?: string, duration: number = 4000) {
    const id = Math.random().toString(36).substring(2, 9);
    const toast: Toast = { id, type, title, message, duration };
    const current = this.toastsSubject.value;
    this.toastsSubject.next([...current, toast]);

    if (duration > 0) {
      setTimeout(() => this.remove(id), duration);
    }
  }

  success(message: string, title?: string, duration?: number) {
    this.show(message, 'success', title || 'Operación Exitosa', duration);
  }

  error(message: string, title?: string, duration?: number) {
    this.show(message, 'error', title || 'Error', duration || 5000);
  }

  warning(message: string, title?: string, duration?: number) {
    this.show(message, 'warning', title || 'Atención', duration);
  }

  info(message: string, title?: string, duration?: number) {
    this.show(message, 'info', title || 'Información', duration);
  }

  remove(id: string) {
    this.toastsSubject.next(this.toastsSubject.value.filter(t => t.id !== id));
  }

  clear() {
    this.toastsSubject.next([]);
  }
}
