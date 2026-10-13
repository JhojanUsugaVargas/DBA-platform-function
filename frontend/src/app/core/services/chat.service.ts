import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ChatResponse } from '../models';

export interface ChatHistoryItem {
  id: number;
  user_id: number;
  content: string;
  username?: string;
  is_bot?: boolean;
  timestamp?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private readonly baseUrl = `${environment.apiUrl}/chat`;

  constructor(private http: HttpClient) {}

  getHistory(): Observable<ChatHistoryItem[]> {
    return this.http.get<ChatHistoryItem[]>(`${this.baseUrl}/history`);
  }

  sendMessage(message: string): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.baseUrl}/message`, { message });
  }

  clearHistory(): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/history`);
  }
}
