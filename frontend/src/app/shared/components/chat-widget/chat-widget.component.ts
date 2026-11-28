/**
 * Module: shared/components/chat-widget/chat-widget.component.ts
 * Nhiệm vụ: Widget Trợ lý AI FruitStore nổi ở góc dưới phải màn hình:
 *           - Streaming SSE theo thời gian thực
 *           - Hiển thị thẻ sản phẩm gợi ý có ảnh & tồn kho
 *           - Gửi ảnh trái cây (Multimodal Vision) và ngữ cảnh trang đang mở
 *           - Khôi phục lịch sử hội thoại cho tài khoản đã đăng nhập
 */

import {
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  computed,
  effect,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NavigationEnd, Router } from '@angular/router';
import { Subscription, filter } from 'rxjs';
import {
  ChatSessionItem,
  ChatbotService,
  RecommendedProduct
} from '../../../core/services/chatbot.service';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

export interface InlineRun {
  text: string;
  bold?: boolean;
  code?: boolean;
}

export interface MessageBlock {
  type: 'paragraph' | 'bullet' | 'ordered';
  marker?: string;
  runs: InlineRun[];
}

interface UiChatMessage {
  role: 'user' | 'assistant';
  content: string;
  blocks: MessageBlock[];
  toolsUsed?: string[];
  recommendedProducts?: RecommendedProduct[];
  imagePreview?: string | null;
  timestamp: string;
  copied?: boolean;
}

const HIDDEN_ROUTES = ['/login', '/register', '/forgot-password', '/reset-password'];

const TOOL_LABELS: Record<string, string> = {
  search_products: 'Tra cứu danh mục',
  get_product_detail: 'Chi tiết sản phẩm',
  check_stock: 'Kiểm tra tồn kho',
  get_expiring_lots: 'Kiểm tra lô cận hạn'
};

@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-widget.component.html',
  styleUrls: ['./chat-widget.component.css']
})
export class ChatWidgetComponent implements OnDestroy {
  @ViewChild('messagesContainer') messagesContainer?: ElementRef<HTMLDivElement>;
  @ViewChild('chatInputEl') chatInputEl?: ElementRef<HTMLInputElement>;
  @ViewChild('visionFileInput') visionFileInput?: ElementRef<HTMLInputElement>;

  isOpen = signal(false);
  isExpanded = signal(false);
  isHidden = signal(false);
  isSending = signal(false);
  streamingStatus = signal('Đang phân tích câu hỏi...');
  showHistory = signal(false);
  isLoadingHistory = signal(false);

  sessionId = signal<string | null>(null);
  guestToken = signal<string | null>(null);
  sessions = signal<ChatSessionItem[]>([]);
  currentRoute = signal<string>('/');
  inputText = '';

  pendingImageBase64 = signal<string | null>(null);
  pendingImageMime = signal<string | null>(null);
  pendingImageName = signal<string>('');

  messages = signal<UiChatMessage[]>([
    this.createMessage(
      'assistant',
      'Xin chào! Mình là **Trợ lý FruitStore**.\nMình có thể giúp bạn:\n- Tìm trái cây theo loại, xuất xứ và xem giá bán\n- Kiểm tra tồn kho thực tế tại cửa hàng\n- Gợi ý cách bảo quản hoặc nhận diện trái cây từ ảnh bạn tải lên'
    )
  ]);

  suggestions = signal<string[]>([
    'Xoài cát Hòa Lộc giá bao nhiêu và còn hàng không?',
    'Cửa hàng đang có những loại trái cây nào?',
    'Cách bảo quản dâu tây tươi lâu?'
  ]);

  isLoggedIn = computed(() => this.authService.isLoggedIn());
  isInternalStaff = computed(() =>
    this.authService.hasRole('ADMIN', 'MANAGER', 'WAREHOUSE')
  );

  private routerSub: Subscription;
  private activeStreamSub?: Subscription;

  constructor(
    private chatbotService: ChatbotService,
    private authService: AuthService,
    private toast: ToastService,
    private router: Router
  ) {
    this.updateVisibility(this.router.url);
    this.routerSub = this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe(e => this.updateVisibility(e.urlAfterRedirects));

    effect(() => {
      this.messages();
      this.isSending();
      this.isOpen();
      this.scrollToBottom();
    });
  }

  ngOnDestroy(): void {
    this.routerSub.unsubscribe();
    this.activeStreamSub?.unsubscribe();
  }

  private updateVisibility(url: string): void {
    const path = url.split('?')[0];
    this.currentRoute.set(url);
    this.isHidden.set(HIDDEN_ROUTES.some(r => path.startsWith(r)));
  }

  private nowLabel(iso?: string): string {
    const dt = iso ? new Date(iso) : new Date();
    return dt.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  }

  private createMessage(
    role: 'user' | 'assistant',
    content: string,
    toolsUsed?: string[],
    recommendedProducts?: RecommendedProduct[],
    imagePreview?: string | null,
    createdAt?: string
  ): UiChatMessage {
    return {
      role,
      content,
      blocks: this.parseMessageBlocks(content),
      toolsUsed,
      recommendedProducts,
      imagePreview,
      timestamp: this.nowLabel(createdAt)
    };
  }

  private parseMessageBlocks(raw: string): MessageBlock[] {
    const lines = (raw || '').replace(/\r\n/g, '\n').split('\n');
    const blocks: MessageBlock[] = [];

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        continue;
      }
      const bulletMatch = trimmed.match(/^[-*•]\s+(.+)$/);
      if (bulletMatch) {
        blocks.push({ type: 'bullet', runs: this.parseInlineRuns(bulletMatch[1]) });
        continue;
      }
      const orderedMatch = trimmed.match(/^(\d+\.)\s+(.+)$/);
      if (orderedMatch) {
        blocks.push({
          type: 'ordered',
          marker: orderedMatch[1],
          runs: this.parseInlineRuns(orderedMatch[2])
        });
        continue;
      }
      blocks.push({ type: 'paragraph', runs: this.parseInlineRuns(trimmed) });
    }

    return blocks.length > 0
      ? blocks
      : [{ type: 'paragraph', runs: [{ text: raw }] }];
  }

  private parseInlineRuns(text: string): InlineRun[] {
    const runs: InlineRun[] = [];
    const tokenRegex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = tokenRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        runs.push({ text: text.slice(lastIndex, match.index) });
      }
      const token = match[0];
      if (token.startsWith('**') && token.endsWith('**')) {
        runs.push({ text: token.slice(2, -2), bold: true });
      } else if (token.startsWith('`') && token.endsWith('`')) {
        runs.push({ text: token.slice(1, -1), code: true });
      }
      lastIndex = tokenRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      runs.push({ text: text.slice(lastIndex) });
    }
    return runs;
  }

  formatToolNames(tools: string[] | undefined): string[] {
    if (!tools || tools.length === 0) {
      return [];
    }
    return Array.from(new Set(tools)).map(t => TOOL_LABELS[t] ?? t);
  }

  resolveProductImage(imageUrl?: string | null): string | null {
    return this.chatbotService.resolveImageUrl(imageUrl);
  }

  formatPrice(price?: string | null): string {
    if (!price) {
      return '';
    }
    const num = Number(price);
    if (Number.isNaN(num)) {
      return price;
    }
    return `${num.toLocaleString('vi-VN')} ₫`;
  }

  openProductInShop(prod: RecommendedProduct): void {
    this.router.navigate(['/shop'], {
      queryParams: { q: prod.sku || prod.name }
    });
  }

  toggleOpen(): void {
    this.isOpen.update(v => !v);
    if (this.isOpen()) {
      if (this.isInternalStaff() && this.messages().length === 1) {
        this.suggestions.set([
          'Có lô trái cây nào sắp hết hạn không?',
          'Kiểm tra tồn kho Xoài cát Hòa Lộc',
          'Liệt kê các sản phẩm đang mở bán'
        ]);
      }
      setTimeout(() => this.chatInputEl?.nativeElement.focus(), 60);
    }
  }

  toggleExpand(): void {
    this.isExpanded.update(v => !v);
  }

  toggleHistory(): void {
    const next = !this.showHistory();
    this.showHistory.set(next);
    if (next && this.isLoggedIn()) {
      this.loadSessions();
    }
  }

  loadSessions(): void {
    this.isLoadingHistory.set(true);
    this.chatbotService.getSessions().subscribe({
      next: list => {
        this.sessions.set(list);
        this.isLoadingHistory.set(false);
      },
      error: () => {
        this.isLoadingHistory.set(false);
        this.toast.error('Không thể tải lịch sử trò chuyện.');
      }
    });
  }

  selectSession(session: ChatSessionItem): void {
    this.isLoadingHistory.set(true);
    this.chatbotService.getSessionMessages(session.id).subscribe({
      next: rows => {
        this.sessionId.set(session.id);
        this.messages.set(
          rows.map(r =>
            this.createMessage(
              r.role === 'user' ? 'user' : 'assistant',
              r.content,
              r.tools_used,
              undefined,
              null,
              r.created_at
            )
          )
        );
        this.showHistory.set(false);
        this.isLoadingHistory.set(false);
      },
      error: () => {
        this.isLoadingHistory.set(false);
        this.toast.error('Không thể khôi phục nội dung phiên trò chuyện.');
      }
    });
  }

  deleteHistorySession(event: Event, session: ChatSessionItem): void {
    event.stopPropagation();
    this.chatbotService.deleteSession(session.id).subscribe({
      next: () => {
        this.sessions.update(list => list.filter(s => s.id !== session.id));
        if (this.sessionId() === session.id) {
          this.resetConversation();
        }
      },
      error: () => this.toast.error('Không thể xóa phiên trò chuyện.')
    });
  }

  resetConversation(): void {
    this.activeStreamSub?.unsubscribe();
    this.sessionId.set(null);
    this.guestToken.set(null);
    this.showHistory.set(false);
    this.clearPendingImage();
    this.messages.set([
      this.createMessage(
        'assistant',
        'Đã tạo cuộc trò chuyện mới. Bạn muốn tra cứu thông tin gì tại FruitStore?'
      )
    ]);
  }

  triggerImagePicker(): void {
    this.visionFileInput?.nativeElement.click();
  }

  onVisionFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) {
      return;
    }
    const allowed = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowed.includes(file.type)) {
      this.toast.error('Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.');
      return;
    }
    if (file.size > 4 * 1024 * 1024) {
      this.toast.error('Ảnh vượt quá giới hạn 4 MB.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      this.pendingImageBase64.set(String(reader.result || ''));
      this.pendingImageMime.set(file.type);
      this.pendingImageName.set(file.name);
      if (!this.inputText.trim()) {
        this.inputText = 'Đây là trái cây gì, cách bảo quản và cửa hàng có bán không?';
      }
      this.chatInputEl?.nativeElement.focus();
    };
    reader.readAsDataURL(file);
  }

  clearPendingImage(): void {
    this.pendingImageBase64.set(null);
    this.pendingImageMime.set(null);
    this.pendingImageName.set('');
  }

  copyReply(index: number): void {
    const msg = this.messages()[index];
    if (!msg || !navigator.clipboard) {
      return;
    }
    navigator.clipboard.writeText(msg.content).then(() => {
      this.messages.update(list =>
        list.map((m, i) => (i === index ? { ...m, copied: true } : m))
      );
      setTimeout(() => {
        this.messages.update(list =>
          list.map((m, i) => (i === index ? { ...m, copied: false } : m))
        );
      }, 1500);
    });
  }

  sendQuickPrompt(text: string): void {
    this.inputText = text;
    this.send();
  }

  send(): void {
    const trimmed = this.inputText.trim();
    if ((!trimmed && !this.pendingImageBase64()) || this.isSending()) {
      return;
    }

    const question = trimmed || 'Nhận diện loại trái cây trong ảnh giúp tôi.';
    const imgB64 = this.pendingImageBase64();
    const imgMime = this.pendingImageMime();

    this.inputText = '';
    this.clearPendingImage();
    this.showHistory.set(false);
    this.messages.update(list => [
      ...list,
      this.createMessage('user', question, undefined, undefined, imgB64)
    ]);

    this.isSending.set(true);
    this.streamingStatus.set('Đang phân tích câu hỏi...');

    let assistantIndex = -1;
    let accumulated = '';

    this.activeStreamSub = this.chatbotService
      .sendMessageStream({
        message: question,
        session_id: this.sessionId(),
        guest_token: this.guestToken(),
        current_route: this.currentRoute(),
        image_base64: imgB64,
        image_mime_type: imgMime
      })
      .subscribe({
        next: evt => {
          if (evt.type === 'status') {
            this.streamingStatus.set(evt.message || 'Đang tra cứu dữ liệu...');
            return;
          }
          if (evt.type === 'delta') {
            accumulated += evt.text;
            if (assistantIndex === -1) {
              this.messages.update(list => {
                assistantIndex = list.length;
                return [...list, this.createMessage('assistant', accumulated)];
              });
            } else {
              this.messages.update(list =>
                list.map((m, i) =>
                  i === assistantIndex
                    ? {
                        ...m,
                        content: accumulated,
                        blocks: this.parseMessageBlocks(accumulated)
                      }
                    : m
                )
              );
            }
            return;
          }
          if (evt.type === 'done') {
            this.sessionId.set(evt.session_id);
            if (evt.guest_token) {
              this.guestToken.set(evt.guest_token);
            }
            if (assistantIndex !== -1) {
              this.messages.update(list =>
                list.map((m, i) =>
                  i === assistantIndex
                    ? {
                        ...m,
                        toolsUsed: evt.tools_used,
                        recommendedProducts: evt.recommended_products
                      }
                    : m
                )
              );
            }
            if (evt.suggestions && evt.suggestions.length > 0) {
              this.suggestions.set(evt.suggestions);
            }
            this.isSending.set(false);
          }
        },
        error: err => {
          const errMsg =
            err?.message ||
            'Không thể kết nối tới Trợ lý AI lúc này. Vui lòng thử lại sau.';
          this.messages.update(list => [
            ...list,
            this.createMessage('assistant', errMsg)
          ]);
          this.isSending.set(false);
        }
      });
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const el = this.messagesContainer?.nativeElement;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    }, 30);
  }
}
