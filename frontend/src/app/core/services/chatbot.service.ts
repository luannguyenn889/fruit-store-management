/**
 * Module: core/services/chatbot.service.ts
 * Nhiệm vụ: Giao tiếp với Chatbot Service (:8007) qua API Gateway (`/api/v1/chatbot`),
 *           hỗ trợ SSE Streaming, gửi ảnh (Vision), ngữ cảnh trang và quản lý lịch sử phiên.
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

export interface RecommendedProduct {
  id: string;
  sku?: string | null;
  name: string;
  unit?: string | null;
  price?: string | null;
  image_url?: string | null;
  available_quantity?: string | null;
}

export interface ChatRequestPayload {
  message: string;
  session_id?: string | null;
  current_route?: string | null;
  product_id?: string | null;
  image_base64?: string | null;
  image_mime_type?: string | null;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  tools_used: string[];
  recommended_products: RecommendedProduct[];
  suggestions: string[];
}

export interface ChatSessionItem {
  id: string;
  title: string;
  user_role: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant' | string;
  content: string;
  tools_used: string[];
  created_at: string;
}

export type ChatStreamEvent =
  | { type: 'status'; message: string }
  | { type: 'delta'; text: string }
  | {
      type: 'done';
      session_id: string;
      tools_used: string[];
      recommended_products: RecommendedProduct[];
      suggestions: string[];
    };

@Injectable({
  providedIn: 'root'
})
export class ChatbotService {
  private readonly apiUrl = `${environment.apiBaseUrl}/chatbot`;
  private readonly gatewayOrigin = environment.apiBaseUrl.replace(/\/api\/v1\/?$/, '');

  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) {}

  private getOptionalHeaders(): HttpHeaders {
    const token = this.authService.getToken();
    return token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
  }

  resolveImageUrl(imageUrl?: string | null): string | null {
    if (!imageUrl) {
      return null;
    }
    if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
      return imageUrl;
    }
    return `${this.gatewayOrigin}${imageUrl.startsWith('/') ? '' : '/'}${imageUrl}`;
  }

  sendMessage(payload: ChatRequestPayload): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.apiUrl}/chat`, payload, {
      headers: this.getOptionalHeaders()
    });
  }

  /** Streaming phản hồi theo thời gian thực qua SSE (`POST /api/v1/chatbot/chat/stream`). */
  sendMessageStream(payload: ChatRequestPayload): Observable<ChatStreamEvent> {
    return new Observable<ChatStreamEvent>(observer => {
      const controller = new AbortController();
      const token = this.authService.getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream'
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      fetch(`${this.apiUrl}/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal
      })
        .then(async res => {
          if (!res.ok) {
            let errMsg = `HTTP ${res.status}`;
            try {
              const errJson = await res.json();
              errMsg = errJson?.message || errMsg;
            } catch {
              // ignore parse error
            }
            throw new Error(errMsg);
          }
          if (!res.body) {
            throw new Error('Trình duyệt không hỗ trợ streaming response.');
          }

          const reader = res.body.getReader();
          const decoder = new TextDecoder('utf-8');
          let buffer = '';

          while (true) {
            const { value, done } = await reader.read();
            if (done) {
              break;
            }
            buffer += decoder.decode(value, { stream: true });
            const rawEvents = buffer.split('\n\n');
            buffer = rawEvents.pop() || '';

            for (const block of rawEvents) {
              const lines = block.split('\n');
              let eventName = 'message';
              let dataLine = '';
              for (const line of lines) {
                if (line.startsWith('event:')) {
                  eventName = line.slice(6).trim();
                } else if (line.startsWith('data:')) {
                  dataLine += line.slice(5).trim();
                }
              }
              if (!dataLine) {
                continue;
              }
              try {
                const parsed = JSON.parse(dataLine);
                if (eventName === 'status') {
                  observer.next({ type: 'status', message: parsed.message || '' });
                } else if (eventName === 'delta') {
                  observer.next({ type: 'delta', text: parsed.text || '' });
                } else if (eventName === 'done') {
                  observer.next({
                    type: 'done',
                    session_id: parsed.session_id,
                    tools_used: parsed.tools_used || [],
                    recommended_products: parsed.recommended_products || [],
                    suggestions: parsed.suggestions || []
                  });
                } else if (eventName === 'error') {
                  throw new Error(parsed.message || 'Lỗi streaming Chatbot');
                }
              } catch (e) {
                if (e instanceof Error && eventName === 'error') {
                  throw e;
                }
              }
            }
          }
          observer.complete();
        })
        .catch(err => {
          if (err?.name !== 'AbortError') {
            observer.error(err);
          }
        });

      return () => controller.abort();
    });
  }

  getSessions(): Observable<ChatSessionItem[]> {
    return this.http.get<ChatSessionItem[]>(`${this.apiUrl}/sessions`, {
      headers: this.getOptionalHeaders()
    });
  }

  getSessionMessages(sessionId: string): Observable<ChatMessageItem[]> {
    return this.http.get<ChatMessageItem[]>(
      `${this.apiUrl}/sessions/${sessionId}/messages`,
      { headers: this.getOptionalHeaders() }
    );
  }

  deleteSession(sessionId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/sessions/${sessionId}`, {
      headers: this.getOptionalHeaders()
    });
  }
}
