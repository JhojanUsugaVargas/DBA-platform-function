import { Injectable, NgZone, PLATFORM_ID, Inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { BehaviorSubject, Observable, Subscription, interval } from 'rxjs';
import { AuthService } from './auth.service';
import { ToastService } from './toast.service';

@Injectable({
  providedIn: 'root'
})
export class InactivityService {
  // 18 minutes of idle time before showing the warning dialog (in seconds)
  private readonly IDLE_THRESHOLD_SECONDS = 18 * 60; // 1080s
  // Warning countdown duration (in seconds): 2 minutes
  private readonly WARNING_DURATION_SECONDS = 2 * 60; // 120s

  private lastActivityTimestamp = Date.now();
  private checkIntervalSub?: Subscription;
  private countdownSub?: Subscription;

  private isWarningActiveSubject = new BehaviorSubject<boolean>(false);
  public isWarningActive$: Observable<boolean> = this.isWarningActiveSubject.asObservable();

  private remainingSecondsSubject = new BehaviorSubject<number>(this.WARNING_DURATION_SECONDS);
  public remainingSeconds$: Observable<number> = this.remainingSecondsSubject.asObservable();

  private isListening = false;

  constructor(
    private authService: AuthService,
    private toast: ToastService,
    private ngZone: NgZone,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {
    if (isPlatformBrowser(this.platformId)) {
      this.init();
    }
  }

  private init(): void {
    this.setupEventListeners();
    this.startIdleMonitor();
  }

  private setupEventListeners(): void {
    if (this.isListening || !isPlatformBrowser(this.platformId)) return;
    this.isListening = true;

    const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'];
    let lastRecorded = 0;

    // Run outside Angular zone so mouse movements don't trigger unnecessary change detection cycles
    this.ngZone.runOutsideAngular(() => {
      events.forEach(eventName => {
        window.addEventListener(eventName, () => {
          const now = Date.now();
          // Throttle timestamp updates to at most once every 5 seconds
          if (now - lastRecorded > 5000) {
            lastRecorded = now;
            // Only update activity timestamp if warning modal is not currently counting down
            if (!this.isWarningActiveSubject.value) {
              this.lastActivityTimestamp = now;
            }
          }
        }, { passive: true });
      });
    });
  }

  private startIdleMonitor(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    // Periodic check every 10 seconds
    this.checkIntervalSub = interval(10000).subscribe(() => {
      if (!this.authService.isAuthenticated()) {
        this.resetTimers();
        return;
      }

      if (this.isWarningActiveSubject.value) {
        return;
      }

      const idleSeconds = Math.floor((Date.now() - this.lastActivityTimestamp) / 1000);
      if (idleSeconds >= this.IDLE_THRESHOLD_SECONDS) {
        this.triggerWarning();
      }
    });
  }

  private triggerWarning(): void {
    this.ngZone.run(() => {
      this.isWarningActiveSubject.next(true);
      let remaining = this.WARNING_DURATION_SECONDS;
      this.remainingSecondsSubject.next(remaining);

      if (this.countdownSub) {
        this.countdownSub.unsubscribe();
      }

      this.countdownSub = interval(1000).subscribe(() => {
        remaining -= 1;
        this.remainingSecondsSubject.next(remaining);

        if (remaining <= 0) {
          this.handleSessionTimeout();
        }
      });
    });
  }

  public stayActive(): void {
    this.ngZone.run(() => {
      this.lastActivityTimestamp = Date.now();
      this.resetTimers();
      this.toast.info('Sesión prolongada exitosamente.', 'Seguridad');
    });
  }

  public logoutNow(): void {
    this.resetTimers();
    this.authService.logout();
  }

  private handleSessionTimeout(): void {
    this.resetTimers();
    this.authService.logout();
    this.toast.warning('Tu sesión se ha cerrado por inactividad prolongada para proteger los datos.', 'Cierre de Sesión Seguro');
  }

  private resetTimers(): void {
    this.isWarningActiveSubject.next(false);
    this.remainingSecondsSubject.next(this.WARNING_DURATION_SECONDS);
    if (this.countdownSub) {
      this.countdownSub.unsubscribe();
      this.countdownSub = undefined;
    }
    this.lastActivityTimestamp = Date.now();
  }
}
