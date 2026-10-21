import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { CookieBannerComponent } from './components/cookie-banner/cookie-banner.component';
import { ToastContainerComponent } from './components/toast/toast-container.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CookieBannerComponent, ToastContainerComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  title = 'frontend';

  skipToMain(event: Event): void {
    event.preventDefault();
    document.getElementById('main-content')?.focus();
  }
}
