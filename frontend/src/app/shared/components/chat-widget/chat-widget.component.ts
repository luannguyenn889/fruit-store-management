/**
 * Module: shared/components/chat-widget/chat-widget.component.ts
 * Nhiệm vụ: Widget bong bóng Trợ lý AI FruitStore nổi ở góc dưới phải màn hình.
 *           Tự ẩn trên các trang xác thực (/login, /register, /forgot-password, /reset-password).
 */

import { Component, OnDestroy, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NavigationEnd, Router } from '@angular/router';
import { Subscription, filter } from 'rxjs';
import { ChatbotService } from '../../../core/services/chatbot.service';
import { AuthService } from '../../../core/services/auth.service';

interface UiChatMessage {
  role: 'user' | 'assistant';
  content: string;
  toolsUsed?: string[];
}

const HIDDEN_ROUTES = ['/login', '/register', '/forgot-password', '/reset-password'];

@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-widget.component.html',
  styleUrls: ['./chat-widget.component.css']
})
export class ChatWidgetComponent implements OnDestroy {
  isOpen = signal(false);
  isHidden = signal(false);
  isSending = signal(false);
  sessionId = signal<string | null>(null);
  inputText = '';

  messages = signal<UiChatMessage[]>([
    {
      role: 'assistant',
      content:
        'Xin chào! Mình là Trợ lý AI FruitStore. Bạn cần tìm trái cây, xem giá, hỏi cách bảo quản hay kiểm tra tồn kho?'
    }
  ]);

  suggestions = signal<string[]>([
    'Xoài cát Hòa Lộc giá bao nhiêu và còn hàng không?',
    'Cửa hàng đang có những loại trái cây nào?',
    'Cách bảo quản dâu tây tươi lâu?'
  ]);

  isInternalStaff = computed(() =>
    this.authService.hasRole('ADMIN', 'MANAGER', 'WAREHOUSE')
  );

  private routerSub: Subscription;

  constructor(
    private chatbotService: ChatbotService,
    private authService: AuthService,
    private router: Router
  ) {
    this.updateVisibility(this.router.url);
    this.routerSub = this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe(e => this.updateVisibility(e.urlAfterRedirects));
  }

  ngOnDestroy(): void {
    this.routerSub.unsubscribe();
  }

  private updateVisibility(url: string): void {
    const path = url.split('?')[0];
    this.isHidden.set(HIDDEN_ROUTES.some(r => path.startsWith(r)));
  }

  toggleOpen(): void {
    this.isOpen.update(v => !v);
    if (this.isOpen() && this.isInternalStaff() && this.messages().length === 1) {
      this.suggestions.set([
        'Có lô trái cây nào sắp hết hạn không?',
        'Kiểm tra tồn kho Xoài cát Hòa Lộc',
        'Liệt kê các sản phẩm đang mở bán'
      ]);
    }
  }

  resetConversation(): void {
    this.sessionId.set(null);
    this.messages.set([
      {
        role: 'assistant',
        content: 'Đã tạo cuộc trò chuyện mới. Bạn muốn hỏi thông tin gì về FruitStore?'
      }
    ]);
  }

  sendQuickPrompt(text: string): void {
    this.inputText = text;
    this.send();
  }

  send(): void {
    const trimmed = this.inputText.trim();
    if (!trimmed || this.isSending()) {
      return;
    }

    this.inputText = '';
    this.messages.update(list => [...list, { role: 'user', content: trimmed }]);
    this.isSending.set(true);

    this.chatbotService.sendMessage(trimmed, this.sessionId()).subscribe({
      next: res => {
        this.sessionId.set(res.session_id);
        this.messages.update(list => [
          ...list,
          { role: 'assistant', content: res.reply, toolsUsed: res.tools_used }
        ]);
        if (res.suggestions && res.suggestions.length > 0) {
          this.suggestions.set(res.suggestions);
        }
        this.isSending.set(false);
      },
      error: () => {
        this.messages.update(list => [
          ...list,
          {
            role: 'assistant',
            content: 'Không thể kết nối tới Trợ lý AI lúc này. Vui lòng thử lại sau ít phút.'
          }
        ]);
        this.isSending.set(false);
      }
    });
  }
}
