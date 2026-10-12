export interface Contract {
  id: number;
  name: string;
  is_active?: boolean;
}

export interface Instance {
  id: number;
  name: string;
  conn_str?: string;
}

export interface UserProfile {
  username: string;
  full_name?: string;
  role: string;
  mfa_enabled: boolean;
  profile_photo?: string | null;
}

export interface UserItem {
  id: number;
  username: string;
  role: string;
  mfa_enabled: boolean;
}

export interface ChatMessage {
  id?: number;
  text: string;
  isUser: boolean;
  isError?: boolean;
  options?: string[];
  timestamp?: string;
}

export interface ChatResponse {
  reply: string;
  message?: string;
  options?: string[];
}

export interface DbaActionResponse {
  type: string;
  title?: string;
  message?: string;
  detail?: string;
  data?: any;
}

export interface HistoricalCpuData {
  labels: string[];
  data: number[];
  simulated?: boolean;
}
