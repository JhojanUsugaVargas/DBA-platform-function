import { Injectable, signal } from '@angular/core';

export interface ConsentChoices {
  necessary: true;      // siempre activo: sesión (JWT) y registro de esta preferencia
  analytics: boolean;   // hoy no se usa ninguna analítica; se deja listo para pedir permiso si algún día se agrega
}

export interface StoredConsent extends ConsentChoices {
  version: string;
  decidedAt: string;
}

/** Versión de la política de cookies. Súbela cuando cambien las categorías o los fines. */
export const COOKIE_POLICY_VERSION = '2026-10-20';

const STORAGE_KEY = 'datacheck_cookie_consent';

/**
 * Gestiona el consentimiento de cookies/almacenamiento local.
 * Regla: ningún script o SDK no esencial debe cargarse sin llamar antes a `hasConsent()`.
 */
@Injectable({ providedIn: 'root' })
export class ConsentService {
  private readonly _consent = signal<StoredConsent | null>(this.read());
  /** Señal de solo lectura con la decisión guardada (null = aún no decidió). */
  readonly consent = this._consent.asReadonly();
  /** El banner se muestra si no hay decisión o si cambió la versión de la política. */
  readonly bannerOpen = signal<boolean>(this.needsDecision());

  hasConsent(category: keyof ConsentChoices): boolean {
    if (category === 'necessary') return true;
    return this._consent()?.[category] === true;
  }

  acceptAll(): void {
    this.save({ necessary: true, analytics: true });
  }

  rejectOptional(): void {
    this.save({ necessary: true, analytics: false });
  }

  saveCustom(analytics: boolean): void {
    this.save({ necessary: true, analytics });
  }

  /** Reabre el banner (enlace "Preferencias de cookies" en el pie). */
  reopen(): void {
    this.bannerOpen.set(true);
  }

  private save(choices: ConsentChoices): void {
    const stored: StoredConsent = {
      ...choices,
      version: COOKIE_POLICY_VERSION,
      decidedAt: new Date().toISOString()
    };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
    } catch {
      /* almacenamiento bloqueado: la decisión vive solo en memoria */
    }
    this._consent.set(stored);
    this.bannerOpen.set(false);
  }

  private read(): StoredConsent | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as StoredConsent) : null;
    } catch {
      return null;
    }
  }

  private needsDecision(): boolean {
    const c = this.read();
    return !c || c.version !== COOKIE_POLICY_VERSION;
  }
}
