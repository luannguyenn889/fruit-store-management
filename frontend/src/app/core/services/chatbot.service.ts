/**
 * Module: core/services/chatbot.service.ts
 * Nhiệm vụ: Giao tiếp với Chatbot Service (:8007) qua API Gateway (`/api/v1/chatbot`),
 *           tự động đính kèm Bearer JWT nếu người dùng đã đăng nhập.
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

export interface ChatResponse {
  session_id: string;
  reply: string;
  tools_used: string[];
  suggestions: string[];
}

export interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant' | string;
  content: string;
  tools_used: string[];
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatbotService {
  private readonly apiUrl = `${environment.apiUrl}/chatbot`;

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

  sendMessage(message: string, sessionId?: string | null): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(
      `${this.apiUrl}/chat`,
      {
        message,
        session_id: sessionId || null
      },
      { headers: this.getOptionalHeaders() }
    );
  }
}
