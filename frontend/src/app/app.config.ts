/**
 * Module: app.config.ts
 * Nhiệm vụ: Cấu hình các provider toàn cục của ứng dụng Angular 21 FruitStore,
 *           bao gồm Router và HttpClient gắn `authInterceptor` (tự động gia hạn Refresh Token).
 */

import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(withInterceptors([authInterceptor])),
  ]
};
