import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { trigger, transition, style, animate } from '@angular/animations';
import { ToastService, Toast } from '../../core/services/toast.service';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast-container" aria-live="polite" aria-atomic="true">
      <div 
        *ngFor="let toast of toastService.toasts$ | async; trackBy: trackById"
        class="toast-card"
        [ngClass]="'toast-' + toast.type"
        [@toastAnim]
        role="alert">
        <div class="toast-icon">
          <span *ngIf="toast.type === 'success'">✅</span>
          <span *ngIf="toast.type === 'error'">❌</span>
          <span *ngIf="toast.type === 'warning'">⚠️</span>
          <span *ngIf="toast.type === 'info'">ℹ️</span>
        </div>
        <div class="toast-body">
          <h5 *ngIf="toast.title" class="toast-title">{{ toast.title }}</h5>
          <p class="toast-message">{{ toast.message }}</p>
        </div>
        <button class="toast-close-btn" (click)="toastService.remove(toast.id)" aria-label="Cerrar notificación">✕</button>
      </div>
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      top: 20px;
      right: 24px;
      z-index: 999999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-width: 420px;
      width: calc(100vw - 48px);
      pointer-events: none;
    }
    .toast-card {
      pointer-events: auto;
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 14px 16px;
      border-radius: 12px;
      background: rgba(15, 23, 42, 0.94);
      backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.65), 0 0 20px rgba(0, 0, 0, 0.4);
      color: #f8fafc;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .toast-card:hover {
      transform: translateY(-2px);
    }
    .toast-icon {
      font-size: 18px;
      line-height: 1;
      padding-top: 2px;
    }
    .toast-body {
      flex: 1;
      min-width: 0;
    }
    .toast-title {
      margin: 0 0 4px 0;
      font-size: 13.5px;
      font-weight: 700;
      letter-spacing: 0.3px;
    }
    .toast-message {
      margin: 0;
      font-size: 12.5px;
      line-height: 1.4;
      color: #cbd5e1;
      word-break: break-word;
    }
    .toast-close-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 14px;
      cursor: pointer;
      padding: 2px 4px;
      border-radius: 4px;
      transition: color 0.15s;
    }
    .toast-close-btn:hover {
      color: #ffffff;
    }
    .toast-success {
      border-color: rgba(16, 185, 129, 0.45);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.65), 0 0 25px rgba(16, 185, 129, 0.15);
    }
    .toast-success .toast-title { color: #34d399; }
    .toast-error {
      border-color: rgba(239, 68, 68, 0.45);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.65), 0 0 25px rgba(239, 68, 68, 0.15);
    }
    .toast-error .toast-title { color: #f87171; }
    .toast-warning {
      border-color: rgba(245, 158, 11, 0.45);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.65), 0 0 25px rgba(245, 158, 11, 0.15);
    }
    .toast-warning .toast-title { color: #fbbf24; }
    .toast-info {
      border-color: rgba(56, 189, 248, 0.45);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.65), 0 0 25px rgba(56, 189, 248, 0.15);
    }
    .toast-info .toast-title { color: #38bdf8; }
  `],
  animations: [
    trigger('toastAnim', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateX(40px) scale(0.95)' }),
        animate('250ms cubic-bezier(0.16, 1, 0.3, 1)', style({ opacity: 1, transform: 'translateX(0) scale(1)' }))
      ]),
      transition(':leave', [
        animate('200ms ease-in', style({ opacity: 0, transform: 'translateX(30px) scale(0.95)' }))
      ])
    ])
  ]
})
export class ToastContainerComponent {
  constructor(public toastService: ToastService) {}

  trackById(index: number, toast: Toast): string {
    return toast.id;
  }
}
