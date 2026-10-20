import { Component, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { LegalLinksComponent } from '../legal/legal-links.component';
import { gsap as gsapLib } from 'gsap';

// Paquete local (npm): ya no se descarga desde un CDN de terceros
const gsap: any = gsapLib;

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LegalLinksComponent],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent implements AfterViewInit, OnDestroy {
  username = '';
  password = '';
  errorMessage = '';
  isLoading = false;
  isLampOn = false;
  step: 'login' | 'otp' = 'login';

  otpCode: string[] = ['', '', '', ''];
  savedToken = '';

  timeLeft: number = 120;
  timerDisplay: string = '02:00';
  private timerInterval: any;

  constructor(
    private router: Router,
    private authService: AuthService
  ) {}

  ngAfterViewInit(): void {
    if (typeof gsap !== 'undefined') {
      gsap.fromTo(
        '.login-card',
        { y: 30, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.8, ease: 'power3.out' }
      );
    }
  }

  ngOnDestroy(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }
  }

  toggleLamp(): void {
    this.isLampOn = true;
    if (typeof gsap !== 'undefined') {
      gsap.to('.lamp-light', { opacity: 0.8, duration: 0.3 });
      gsap.to('.lamp-glow', { opacity: 0.5, duration: 0.3 });
    }
  }

  startTimer(): void {
    this.timeLeft = 120;
    this.updateTimerDisplay();
    if (this.timerInterval) clearInterval(this.timerInterval);

    this.timerInterval = setInterval(() => {
      this.timeLeft--;
      this.updateTimerDisplay();
      if (this.timeLeft <= 0) {
        clearInterval(this.timerInterval);
        this.errorMessage = 'El código ha expirado.';
        this.otpCode = ['', '', '', ''];
      }
    }, 1000);
  }

  updateTimerDisplay(): void {
    const m = Math.floor(this.timeLeft / 60);
    const s = this.timeLeft % 60;
    this.timerDisplay = (m < 10 ? '0' + m : m) + ':' + (s < 10 ? '0' + s : s);
  }

  resendOtp(): void {
    if (this.isLoading) return;
    this.isLoading = true;
    this.errorMessage = '';

    this.authService.sendOtp(this.username).subscribe({
      next: () => {
        this.isLoading = false;
        this.startTimer();
        this.otpCode = ['', '', '', ''];
        this.focusInput(0);
        if (typeof gsap !== 'undefined') {
          gsap.fromTo('.timer-display', { scale: 1.5, color: 'var(--green)' }, { scale: 1, color: 'var(--text-muted)', duration: 0.5 });
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = 'Error al reenviar OTP: ' + (err.error?.detail || err.message);
      }
    });
  }

  onOtpInput(event: any, index: number): void {
    if (this.timeLeft <= 0) return;

    const val = event.target.value;
    if (val) {
      this.otpCode[index] = val.slice(-1);
      event.target.value = this.otpCode[index];

      setTimeout(() => {
        if (index < 3) {
          const next = document.getElementById('otp-' + (index + 1));
          if (next) next.focus();
        }
        if (this.otpCode.join('').length === 4) {
          this.verifyOtp();
        }
      }, 10);
    }
  }

  onOtpKeyup(event: KeyboardEvent, index: number): void {}

  onOtpKeydown(event: KeyboardEvent, index: number): void {
    if (this.timeLeft <= 0) return;

    if (event.key === 'Backspace') {
      if (!this.otpCode[index] && index > 0) {
        const prev = document.getElementById('otp-' + (index - 1));
        if (prev) {
          this.otpCode[index - 1] = '';
          prev.focus();
        }
      } else {
        this.otpCode[index] = '';
      }
    }
  }

  focusInput(index: number): void {
    setTimeout(() => {
      const el = document.getElementById('otp-' + index);
      if (el) el.focus();
    }, 50);
  }

  onSubmit(): void {
    this.isLoading = true;
    this.errorMessage = '';

    if (typeof gsap !== 'undefined') {
      gsap.to('.gold-btn span', { opacity: 0.5, yoyo: true, repeat: -1, duration: 0.4 });
    }

    this.authService.login(this.username, this.password).subscribe({
      next: (response) => {
        if (!response.requires_mfa) {
          this.authService.setToken(response.access_token);
          if (typeof gsap !== 'undefined') {
            gsap.to('.login-card', {
              y: -50,
              opacity: 0,
              duration: 0.5,
              onComplete: () => {
                this.router.navigate(['/dashboard']);
              }
            });
          } else {
            this.router.navigate(['/dashboard']);
          }
          return;
        }

        this.savedToken = response.access_token;

        this.authService.sendOtp(this.username).subscribe({
          next: () => {
            this.isLoading = false;
            if (typeof gsap !== 'undefined') {
              gsap.killTweensOf('.gold-btn span');
              gsap.set('.gold-btn span', { opacity: 1 });
            }

            this.step = 'otp';
            this.startTimer();

            try {
              if (typeof gsap !== 'undefined') {
                gsap.to(document.body, { backgroundColor: '#0a0a0a', duration: 0.6 });
                setTimeout(() => {
                  gsap.fromTo(
                    '.otp-inputs input',
                    { y: 50, opacity: 0 },
                    { y: 0, opacity: 1, duration: 0.5, stagger: 0.1, ease: 'power2.out' }
                  );
                  this.focusInput(0);
                }, 50);
              }
            } catch {}
          },
          error: (err) => {
            this.isLoading = false;
            if (typeof gsap !== 'undefined') {
              gsap.killTweensOf('.gold-btn span');
              gsap.set('.gold-btn span', { opacity: 1 });
            }
            this.errorMessage = 'Error al solicitar OTP: ' + (err.error?.detail || err.message);
          }
        });
      },
      error: (error) => {
        this.isLoading = false;
        if (typeof gsap !== 'undefined') {
          gsap.killTweensOf('.gold-btn span');
          gsap.set('.gold-btn span', { opacity: 1 });
        }
        this.errorMessage = error.error?.detail || 'Credenciales incorrectas';
      }
    });
  }

  verifyOtp(): void {
    this.isLoading = true;
    const code = this.otpCode.join('');

    if (typeof gsap !== 'undefined') {
      gsap.to('.otp-inputs input', { opacity: 0.5, duration: 0.2 });
    }

    if (code.length === 4) {
      this.authService.verifyOtp(this.username, code).subscribe({
        next: (res) => {
          if (typeof gsap !== 'undefined') {
            gsap.to('.otp-inputs input', {
              backgroundColor: 'rgba(0, 255, 0, 0.15)',
              borderColor: '#00ff00',
              opacity: 1,
              duration: 0.3
            });
          }

          setTimeout(() => {
            this.authService.setToken(res.access_token);
            this.router.navigate(['/dashboard']);
            document.body.style.backgroundColor = '';
          }, 600);
        },
        error: (err) => {
          this.isLoading = false;
          this.errorMessage = err.error?.detail || 'Código OTP incorrecto';
          this.otpCode = ['', '', '', ''];

          if (typeof gsap !== 'undefined') {
            gsap.set('.otp-inputs input', { opacity: 1 });
            gsap.fromTo(
              '.otp-inputs',
              { x: -15 },
              {
                x: 15,
                duration: 0.08,
                yoyo: true,
                repeat: 5,
                onComplete: () => {
                  gsap.to('.otp-inputs', { x: 0 });
                  gsap.fromTo(
                    '.otp-inputs input',
                    { borderColor: '#ff4d4d', backgroundColor: 'rgba(255,0,0,0.1)' },
                    { borderColor: 'rgba(255,255,255,0.2)', backgroundColor: 'transparent', duration: 0.5, delay: 0.5 }
                  );
                  this.focusInput(0);
                }
              }
            );
          }
        }
      });
    }
  }
}
