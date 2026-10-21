import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { CookieBannerComponent } from './components/cookie-banner/cookie-banner.component';
import { ToastContainerComponent } from './components/toast/toast-container.component';
import { InactivityService } from './core/services/inactivity.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, CookieBannerComponent, ToastContainerComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  title = 'frontend';

  constructor(public inactivity: InactivityService) {}

  skipToMain(event: Event): void {
    event.preventDefault();
    document.getElementById('main-content')?.focus();
  }
}
