import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';
import { LEGAL_DOCS, LEGAL_VERSION } from './legal-content';
import { ConsentService } from '../../core/services/consent.service';

@Component({
  selector: 'app-legal-page',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="legal-scroll">
      <article class="legal-page" [attr.aria-labelledby]="'legal-title'">
        <nav class="legal-nav" aria-label="Documentos legales">
          <a routerLink="/login" class="back-link">← Volver</a>
          <ul>
            @for (d of docs; track d.slug) {
              <li><a [routerLink]="['/legal', d.slug]" [attr.aria-current]="doc()?.slug === d.slug ? 'page' : null">{{ d.short }}</a></li>
            }
          </ul>
        </nav>

        @if (doc(); as d) {
          <h1 id="legal-title">{{ d.title }}</h1>
          <p class="legal-meta">Versión {{ version }} · {{ d.summary }}</p>

          @for (b of d.blocks; track $index) {
            @switch (b.type) {
              @case ('h3') { <h2>{{ b.text }}</h2> }
              @case ('p') { <p>{{ b.text }}</p> }
              @case ('ul') {
                <ul class="legal-list">
                  @for (i of b.items; track $index) { <li>{{ i }}</li> }
                </ul>
              }
              @case ('table') {
                <div class="table-wrap" tabindex="0" role="region" [attr.aria-label]="'Tabla: ' + d.title">
                  <table>
                    <thead><tr>@for (h of b.head; track $index) { <th scope="col">{{ h }}</th> }</tr></thead>
                    <tbody>
                      @for (r of b.rows; track $index) {
                        <tr>@for (c of r; track $index) { <td>{{ c }}</td> }</tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
            }
          }
        } @else {
          <h1 id="legal-title">Documento no encontrado</h1>
          <p>Elige uno de los documentos del menú superior.</p>
        }

        <footer class="legal-foot">
          <button type="button" (click)="consent.reopen()">Preferencias de cookies</button>
        </footer>
      </article>
    </div>
  `,
  styles: [`
    .legal-scroll { height: 100vh; overflow-y: auto; background: #0a0a0a; }
    .legal-page { max-width: 860px; margin: 0 auto; padding: 32px 24px 80px; color: #ededed; line-height: 1.7; }
    .legal-nav { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 24px; margin-bottom: 28px;
                 padding-bottom: 14px; border-bottom: 1px solid #3f3f46; }
    .legal-nav ul { display: flex; flex-wrap: wrap; gap: 8px 18px; list-style: none; margin: 0; padding: 0; }
    .legal-nav a { color: #67e8f9; text-decoration: underline; font-size: 14px; }
    .legal-nav a[aria-current='page'] { color: #ffffff; font-weight: 600; text-decoration: none; }
    .back-link { font-weight: 600; }
    h1 { font-size: 26px; font-weight: 600; margin: 0 0 6px; }
    h2 { font-size: 17px; font-weight: 600; margin: 28px 0 8px; color: #ffffff; }
    p, li { font-size: 14.5px; color: #d4d4d8; }
    .legal-meta { font-size: 13px; color: #a1a1aa; margin-bottom: 8px; }
    .legal-list { padding-left: 22px; margin: 8px 0; }
    .table-wrap { overflow-x: auto; margin: 12px 0; border: 1px solid #3f3f46; border-radius: 10px; }
    table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
    th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid #27272a; vertical-align: top; }
    th { background: #18181b; color: #ffffff; font-weight: 600; }
    td { color: #d4d4d8; }
    .legal-foot { margin-top: 40px; padding-top: 16px; border-top: 1px solid #3f3f46; }
    .legal-foot button { background: transparent; color: #67e8f9; border: 1px solid #8f8f9a; border-radius: 8px;
                         padding: 8px 14px; cursor: pointer; font: 500 13px var(--font-body, sans-serif); }
    .legal-foot button:hover { border-color: #ffffff; color: #ffffff; }
  `]
})
export class LegalPageComponent {
  private route = inject(ActivatedRoute);
  private title = inject(Title);
  consent = inject(ConsentService);
  version = LEGAL_VERSION;

  docs = [
    { slug: 'privacidad', short: 'Privacidad' },
    { slug: 'terminos', short: 'Términos y Condiciones' },
    { slug: 'cookies', short: 'Cookies' },
    { slug: 'licencias', short: 'Licencias y Créditos' }
  ];

  doc = toSignal(
    this.route.paramMap.pipe(
      map(p => {
        const d = LEGAL_DOCS[p.get('slug') ?? ''];
        this.title.setTitle(d ? `${d.title} | DataCheck Pro` : 'Documento no encontrado | DataCheck Pro');
        return d ?? null;
      })
    ),
    { initialValue: null }
  );
}
