import type {
  AuditLog,
  AuthResponse,
  Entry,
  EntryForm,
  SessionInfo,
  StatusResponse,
  UserSummary
} from "../types";

const TOKEN_KEY = "sds_session_token";
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getStoredToken();
  const hasBody = options.body !== undefined;

  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let message = `Erro ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      // Keep the HTTP fallback message.
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  status: () => request<StatusResponse>("/api/status"),
  setup: (payload: {
    admin_username: string;
    admin_password: string;
    viewer_username: string;
    viewer_password: string;
  }) =>
    request<AuthResponse>("/api/setup", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  login: (payload: { username: string; password: string }) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  me: () => request<SessionInfo>("/api/auth/me"),
  entries: () => request<Entry[]>("/api/passwords"),
  reveal: (id: string) => request<{ id: string; secret: string }>(`/api/passwords/${id}/secret`),
  createEntry: (payload: EntryForm) =>
    request<Entry>("/api/passwords", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updateEntry: (id: string, payload: EntryForm) =>
    request<Entry>(`/api/passwords/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  deleteEntry: (id: string) => request<void>(`/api/passwords/${id}`, { method: "DELETE" }),
  auditLogs: () => request<AuditLog[]>("/api/audit-logs"),
  users: () => request<UserSummary[]>("/api/users"),
  changeLoginPassword: (username: string, payload: { new_password: string }) =>
    request<UserSummary>(`/api/users/${encodeURIComponent(username)}/password`, {
      method: "PUT",
      body: JSON.stringify(payload)
    })
};
