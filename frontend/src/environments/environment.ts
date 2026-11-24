/**
 * Module: environments/environment.ts
 * Nhiệm vụ: Tập trung cấu hình môi trường phát triển cho Frontend Angular
 *           (API Gateway URL và Google OAuth2 Client ID) — tránh hard-code URL ở nhiều nơi.
 */

export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000/api/v1',
  googleClientId:
    '569426721711-6ub3hgomi74b201otif6cpe3oq53s5fj.apps.googleusercontent.com'
};
