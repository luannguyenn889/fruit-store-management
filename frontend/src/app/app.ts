/**
 * Module: app.ts
 * Nhiệm vụ: Root component của ứng dụng Angular FruitStore, gắn RouterOutlet
 *           và khung thông báo Toast toàn cục (`ToastContainerComponent`).
 */

import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ToastContainerComponent } from './shared/components/toast-container/toast-container.component';
import { ChatWidgetComponent } from './shared/components/chat-widget/chat-widget.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, ToastContainerComponent, ChatWidgetComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('frontend');
}
