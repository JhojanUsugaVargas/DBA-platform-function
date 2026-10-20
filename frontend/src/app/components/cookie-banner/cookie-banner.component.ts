import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ConsentService } from '../../core/services/consent.service';

@Component({
  selector: 'app-cookie-banner',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    @if (consent.bannerOpen()) {
      <div class="cookie-banner" role="dialog" aria-modal="false" aria-labelledby="cookie-title" aria-describedby="cookie-desc"
           (keydown.escape)="consent.rejectOptional()">
        <div class="cookie-body">
          <h2 id="cookie-title">Tu privacidad en DataCheck Pro</h2>
          <p id="cookie-desc">
            Usamos almacenamiento local <strong>estrictamente necesario</strong> para mantener tu sesión y recordar esta decisión.
            Hoy <strong>no usamos cookies de analítica ni de publicidad</strong>. Si alguna vez las activamos, te pediremos permiso antes.
            Más información en la <a routerLink="/legal/cookies">Política de Cookies</a> y la
            <a routerLink="/legal/privacidad">Política de Privacidad</a>.
          </p>

          @if (showDetails) {
            <fieldset class="cookie-options">
              <legend class="sr-only">Categorías de cookies</legend>
              <label class="cookie-option">
                <input type="checkbox" checked disabled>
                <span><strong>Necesarias</strong> — sesión y preferencia de cookies. Siempre activas, no se pueden desactivar.</span>
              </label>
              <label class="cookie-option">
                <input type="checkbox" name="analytics" [(ngModel)]="analytics">
                <span><strong>Analítica</strong> — actualmente no se usa ninguna. Desactivada por defecto.</span>
              </label>
            </fieldset>
          }

          <div class="cookie-actions">
            <button type="button" class="cookie-btn" (click)="consent.rejectOptional()">Solo necesarias</button>
            <button type="button" class="cookie-btn" (click)="consent.acceptAll()">Aceptar todas</button>
            @if (!showDetails) {
              <button type="button" class="cookie-btn" (click)="showDetails = true">Personalizar</button>
            } @else {
              <button type="button" class="cookie-btn" (click)="consent.saveCustom(analytics)">Guardar mi selección</button>
            }
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .cookie-banner {
      position: fixed; left: 16px; right: 16px; bottom: 16px; z-index: 100001;
      max-width: 760px; margin: 0 auto;
      background: #141414; border: 1px solid #52525b; border-radius: 14px;
      padding: 20px 22px; box-shadow: 0 20px 50px rgba(0,0,0,.7); color: #ededed;
    }
    h2 { font-size: 16px; font-weight: 600; margin: 0 0 8px; }
    p { font-size: 13.5px; line-height: 1.6; color: #c4c4cc; margin: 0 0 14px; }
    a { color: #67e8f9; text-decoration: underline; }
    .cookie-options { border: 0; margin: 0 0 14px; display: grid; gap: 10px; }
    .cookie-option { display: flex; gap: 10px; align-items: flex-start; font-size: 13px; color: #c4c4cc; }
    .cookie-option input { margin-top: 3px; width: 16px; height: 16px; accent-color: #00e5ff; }
    .cookie-actions { display: flex; flex-wrap: wrap; gap: 10px; }
    /* Los tres botones tienen el MISMO peso visual: sin patrones oscuros */
    .cookie-btn {
      flex: 1 1 140px; padding: 11px 16px; border-radius: 10px; cursor: pointer;
      background: #1f1f23; color: #ffffff; border: 1px solid #8f8f9a;
      font: 600 13px var(--font-body, sans-serif);
    }
    .cookie-btn:hover { background: #2a2a30; border-color: #ffffff; }
  `]
})
export class CookieBannerComponent {
  consent = inject(ConsentService);
  showDetails = false;
  analytics = false;
}
