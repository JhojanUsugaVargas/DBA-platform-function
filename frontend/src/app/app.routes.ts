import { Routes } from '@angular/router';
import { LoginComponent } from './components/login/login.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { IncidentManagementComponent } from './components/incident-management/incident-management.component';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'admin/incidents', component: IncidentManagementComponent, canActivate: [authGuard] },
  { path: 'incidentes', redirectTo: '/admin/incidents' },
  { path: '**', redirectTo: '/login' }
];
