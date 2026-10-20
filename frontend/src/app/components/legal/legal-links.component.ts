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
      <span class="sep" aria-hidden="true">•</span>
      <a routerLink="/legal/terminos">Términos</a>
      <span class="sep" aria-hidden="true">•</span>
      <a routerLink="/legal/cookies">Cookies</a>
      <span class="sep" aria-hidden="true">•</span>
      <a routerLink="/legal/licencias">Licencias</a>
      <span class="sep" aria-hidden="true">•</span>
      <button type="button" (click)="consent.reopen()">Preferencias de cookies</button>
    </nav>
  `,
  styles: [`
    .legal-links { 
      display: flex; 
      flex-wrap: wrap; 
      justify-content: center; 
      align-items: center; 
      gap: 6px 10px; 
      font-size: 11.5px; 
      letter-spacing: 0.3px;
    }
    .sep { 
      color: rgba(255, 255, 255, 0.25); 
      font-size: 10px; 
      user-select: none; 
    }
    a, button { 
      color: rgba(255, 255, 255, 0.5); 
      text-decoration: none; 
      background: none; 
      border: 0; 
      padding: 3px 4px; 
      cursor: pointer;
      font: inherit; 
      transition: all 0.2s ease; 
    }
    a:hover, button:hover { 
      color: #ffd700; 
      text-shadow: 0 0 8px rgba(255, 215, 0, 0.3); 
    }
    button:focus-visible, a:focus-visible {
      outline: 2px solid #00e5ff;
      outline-offset: 2px;
      border-radius: 4px;
    }
  `]
})
export class LegalLinksComponent {
  consent = inject(ConsentService);
}
