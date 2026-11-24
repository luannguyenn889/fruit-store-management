/**
 * Module: cypress.config.ts
 * Nhiệm vụ: Cấu hình Cypress E2E (v16+) cho ứng dụng Angular FruitStore (:4200)
 *           giao tiếp với API Gateway (:8000) -> Auth Service (:8001) & Catalog Service (:8002).
 */

import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:4200',
    specPattern: 'cypress/e2e/**/*.cy.ts',
    supportFile: 'cypress/support/e2e.ts',
    viewportWidth: 1366,
    viewportHeight: 820,
    defaultCommandTimeout: 10000,
    requestTimeout: 15000,
    video: false,
    screenshotOnRunFailure: true,
  },
});
