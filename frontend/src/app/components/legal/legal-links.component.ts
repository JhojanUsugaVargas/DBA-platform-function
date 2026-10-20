import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ConsentService } from '../../core/services/consent.service';

/** Enlaces legales reutilizables (login, dashboard). */
@Component({
  selector: 'app-legal-links',
  standalone: true,
  imports: [RouterLink],
  template: `
    <nav class="legal-links" aria-label="Información legal">
      <a routerLink="/legal/privacidad">Privacidad</a>
      <a routerLink="/legal/terminos">Términos</a>
      <a routerLink="/legal/cookies">Cookies</a>
      <a routerLink="/legal/licencias">Licencias</a>
      <button type="button" (click)="consent.reopen()">Preferencias de cookies</button>
    </nav>
  `,
  styles: [`
    .legal-links { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px 14px; font-size: 12px; }
    a, button { color: #b4b4bd; text-decoration: underline; background: none; border: 0; padding: 2px; cursor: pointer;
                font: inherit; }
    a:hover, button:hover { color: #ffffff; }
  `]
})
export class LegalLinksComponent {
  consent = inject(ConsentService);
}
