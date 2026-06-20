export type Role = "admin" | "viewer";

export type StatusResponse = {
  configured: boolean;
  vault_path: string;
};

export type AuthResponse = {
  token: string;
  username: string;
  role: Role;
  expires_at: string;
};

export type SessionInfo = {
  username: string;
  role: Role;
  expires_at: string;
};

export type Entry = {
  id: string;
  title: string;
  username: string;
  url: string;
  category: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type EntryForm = {
  title: string;
  username: string;
  secret: string;
  url: string;
  category: string;
  notes: string;
};

export type AuditLog = {
  id: string;
  at: string;
  username: string;
  action: string;
  entry_id: string | null;
  metadata: Record<string, unknown>;
};

export type UserSummary = {
  id: string;
  username: string;
  role: Role;
  created_at: string;
  updated_at: string;
};
