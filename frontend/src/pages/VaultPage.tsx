import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Copy,
  Eye,
  EyeOff,
  KeyRound,
  LogOut,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Search,
  Shield,
  Trash2,
  User,
  X
} from "lucide-react";

import { api } from "../services/api";
import type { AuditLog, Entry, EntryForm, SessionInfo, UserSummary } from "../types";

type Props = {
  session: SessionInfo;
  vaultPath: string;
  onLogout: () => void;
};

const emptyForm: EntryForm = {
  title: "",
  username: "",
  secret: "",
  url: "",
  category: "",
  notes: ""
};

export default function VaultPage({ session, vaultPath, onLogout }: Props) {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"senhas" | "logs">("senhas");
  const [editorMode, setEditorMode] = useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = useState<Entry | null>(null);
  const [form, setForm] = useState<EntryForm>(emptyForm);
  const [passwordTarget, setPasswordTarget] = useState<UserSummary | null>(null);
  const [loginPassword, setLoginPassword] = useState("");
  const [loginPasswordConfirm, setLoginPasswordConfirm] = useState("");
  const [passwordSubmitting, setPasswordSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isAdmin = session.role === "admin";

  useEffect(() => {
    void loadEntries();
    if (isAdmin) {
      void loadAdminData();
    }
  }, [isAdmin]);

  const filteredEntries = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return entries;
    return entries.filter((entry) =>
      [entry.title, entry.username, entry.url, entry.category, entry.notes].some((value) =>
        value.toLowerCase().includes(term)
      )
    );
  }, [entries, query]);

  async function loadEntries() {
    setLoading(true);
    setError("");
    try {
      setEntries(await api.entries());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar senhas.");
    } finally {
      setLoading(false);
    }
  }

  async function loadAdminData() {
    try {
      const [logs, currentUsers] = await Promise.all([api.auditLogs(), api.users()]);
      setAuditLogs(logs);
      setUsers(currentUsers);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar dados administrativos.");
    }
  }

  async function reveal(entry: Entry) {
    if (secrets[entry.id]) {
      setSecrets((current) => {
        const next = { ...current };
        delete next[entry.id];
        return next;
      });
      return;
    }

    try {
      const response = await api.reveal(entry.id);
      setSecrets((current) => ({ ...current, [entry.id]: response.secret }));
      if (isAdmin) void loadAdminData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao revelar senha.");
    }
  }

  async function copySecret(entry: Entry) {
    try {
      const response = secrets[entry.id] ? { secret: secrets[entry.id] } : await api.reveal(entry.id);
      await navigator.clipboard.writeText(response.secret);
      setMessage("Copiado");
      window.setTimeout(() => setMessage(""), 1600);
      if (isAdmin) void loadAdminData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao copiar senha.");
    }
  }

  function openCreate() {
    setEditorMode("create");
    setEditing(null);
    setForm(emptyForm);
  }

  function openEdit(entry: Entry) {
    setEditorMode("edit");
    setEditing(entry);
    setForm({
      title: entry.title,
      username: entry.username,
      secret: "",
      url: entry.url,
      category: entry.category,
      notes: entry.notes
    });
  }

  function closeEditor() {
    setEditorMode(null);
    setEditing(null);
    setForm(emptyForm);
  }

  async function submitEntry(event: FormEvent) {
    event.preventDefault();
    if (!isAdmin) return;
    setError("");
    try {
      if (editing) {
        const payload = { ...form };
        if (!payload.secret) {
          delete (payload as Partial<EntryForm>).secret;
        }
        await api.updateEntry(editing.id, payload as EntryForm);
      } else {
        await api.createEntry(form);
      }
      closeEditor();
      setSecrets({});
      await loadEntries();
      await loadAdminData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar senha.");
    }
  }

  async function deleteEntry(entry: Entry) {
    if (!window.confirm(`Excluir "${entry.title}"?`)) return;
    try {
      await api.deleteEntry(entry.id);
      setSecrets((current) => {
        const next = { ...current };
        delete next[entry.id];
        return next;
      });
      await loadEntries();
      await loadAdminData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao excluir senha.");
    }
  }

  function openLoginPasswordChange(user: UserSummary) {
    setPasswordTarget(user);
    setLoginPassword("");
    setLoginPasswordConfirm("");
    setError("");
  }

  function closeLoginPasswordChange() {
    setPasswordTarget(null);
    setLoginPassword("");
    setLoginPasswordConfirm("");
  }

  async function submitLoginPassword(event: FormEvent) {
    event.preventDefault();
    if (!passwordTarget) return;
    if (loginPassword !== loginPasswordConfirm) {
      setError("As senhas informadas nao conferem.");
      return;
    }

    setPasswordSubmitting(true);
    setError("");
    try {
      await api.changeLoginPassword(passwordTarget.username, { new_password: loginPassword });
      closeLoginPasswordChange();
      await loadAdminData();
      setMessage("Senha de login atualizada");
      window.setTimeout(() => setMessage(""), 1800);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao alterar senha de login.");
    } finally {
      setPasswordSubmitting(false);
    }
  }

  const editorOpen = isAdmin && editorMode !== null;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Sistema de Senhas</h1>
          <p>{vaultPath}</p>
        </div>
        <div className="session-box">
          <span className={`role-chip ${session.role}`}>
            {session.role === "admin" ? <Shield size={15} /> : <User size={15} />}
            {session.username}
          </span>
          <button className="icon-button" title="Sair" onClick={onLogout}>
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <section className="toolbar">
        <div className="search-box">
          <Search size={18} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Pesquisar" />
        </div>
        <div className="toolbar-actions">
          {isAdmin ? (
            <div className="tabs">
              <button className={activeTab === "senhas" ? "active" : ""} onClick={() => setActiveTab("senhas")}>
                Senhas
              </button>
              <button className={activeTab === "logs" ? "active" : ""} onClick={() => setActiveTab("logs")}>
                Logs
              </button>
            </div>
          ) : null}
          <button className="icon-button" title="Atualizar" onClick={() => void loadEntries()}>
            <RefreshCw size={18} />
          </button>
          {isAdmin ? (
            <button className="primary-button small" onClick={openCreate}>
              <Plus size={17} />
              Nova
            </button>
          ) : null}
        </div>
      </section>

      {message ? <div className="toast">{message}</div> : null}
      {error ? <div className="error-bar">{error}</div> : null}

      {activeTab === "logs" && isAdmin ? (
        <section className="content-grid logs-layout">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Usuário</th>
                  <th>Ação</th>
                  <th>Registro</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{formatDate(log.at)}</td>
                    <td>{log.username}</td>
                    <td>{translateAction(log.action)}</td>
                    <td>{typeof log.metadata.title === "string" ? log.metadata.title : log.entry_id ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <aside className="side-panel static-panel">
            <h2>Usuários</h2>
            {users.map((user) => (
              <div className="user-row" key={user.id}>
                <div className="user-info">
                  <span>{user.username}</span>
                  <strong>{user.role}</strong>
                </div>
                <button className="icon-button" title="Alterar senha de login" onClick={() => openLoginPasswordChange(user)}>
                  <KeyRound size={17} />
                </button>
              </div>
            ))}
            {passwordTarget ? (
              <form className="entry-form password-form" onSubmit={submitLoginPassword}>
                <div className="panel-heading">
                  <h2>{passwordTarget.username}</h2>
                  <button className="icon-button" type="button" title="Fechar" onClick={closeLoginPasswordChange}>
                    <X size={18} />
                  </button>
                </div>
                <label>
                  Nova senha de login
                  <input
                    required
                    minLength={8}
                    type="password"
                    autoComplete="new-password"
                    value={loginPassword}
                    onChange={(event) => setLoginPassword(event.target.value)}
                  />
                </label>
                <label>
                  Confirmar senha
                  <input
                    required
                    minLength={8}
                    type="password"
                    autoComplete="new-password"
                    value={loginPasswordConfirm}
                    onChange={(event) => setLoginPasswordConfirm(event.target.value)}
                  />
                </label>
                <button className="primary-button" disabled={passwordSubmitting} type="submit">
                  <Save size={18} />
                  {passwordSubmitting ? "Salvando..." : "Atualizar login"}
                </button>
              </form>
            ) : null}
          </aside>
        </section>
      ) : (
        <section className={`content-grid ${editorOpen ? "with-editor" : ""}`}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Serviço</th>
                  <th>Usuário</th>
                  <th>Categoria</th>
                  <th>Senha</th>
                  <th>Atualizado</th>
                  <th className="actions-col"></th>
                </tr>
              </thead>
              <tbody>
                {filteredEntries.map((entry) => (
                  <tr key={entry.id}>
                    <td>
                      <div className="entry-title">
                        <strong>{entry.title}</strong>
                        {entry.url ? (
                          <a href={entry.url} target="_blank" rel="noreferrer">
                            {entry.url}
                          </a>
                        ) : null}
                      </div>
                    </td>
                    <td>{entry.username || "-"}</td>
                    <td>{entry.category || "-"}</td>
                    <td>
                      <code className="secret-cell">{secrets[entry.id] ?? "••••••••••••"}</code>
                    </td>
                    <td>{formatDate(entry.updated_at)}</td>
                    <td>
                      <div className="row-actions">
                        <button className="icon-button" title="Revelar" onClick={() => void reveal(entry)}>
                          {secrets[entry.id] ? <EyeOff size={17} /> : <Eye size={17} />}
                        </button>
                        <button className="icon-button" title="Copiar" onClick={() => void copySecret(entry)}>
                          <Copy size={17} />
                        </button>
                        {isAdmin ? (
                          <>
                            <button className="icon-button" title="Editar" onClick={() => openEdit(entry)}>
                              <Pencil size={17} />
                            </button>
                            <button className="icon-button danger" title="Excluir" onClick={() => void deleteEntry(entry)}>
                              <Trash2 size={17} />
                            </button>
                          </>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && filteredEntries.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="empty-row">
                      Nenhum registro
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          {editorOpen ? (
            <aside className="side-panel">
              <div className="panel-heading">
                <h2>{editing ? "Editar" : "Nova senha"}</h2>
                <button className="icon-button" title="Fechar" onClick={closeEditor}>
                  <X size={18} />
                </button>
              </div>
              <form className="entry-form" onSubmit={submitEntry}>
                <label>
                  Serviço
                  <input
                    required
                    value={form.title}
                    onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                  />
                </label>
                <label>
                  Usuário
                  <input
                    value={form.username}
                    onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
                  />
                </label>
                <label>
                  Senha
                  <input
                    required={!editing}
                    type="password"
                    value={form.secret}
                    placeholder={editing ? "Manter senha atual" : ""}
                    onChange={(event) => setForm((current) => ({ ...current, secret: event.target.value }))}
                  />
                </label>
                <label>
                  URL
                  <input
                    value={form.url}
                    onChange={(event) => setForm((current) => ({ ...current, url: event.target.value }))}
                  />
                </label>
                <label>
                  Categoria
                  <input
                    value={form.category}
                    onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}
                  />
                </label>
                <label>
                  Notas
                  <textarea
                    value={form.notes}
                    onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                  />
                </label>
                <button className="primary-button" type="submit">
                  <Save size={18} />
                  Salvar
                </button>
              </form>
            </aside>
          ) : null}
        </section>
      )}
    </main>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(date);
}

function translateAction(action: string) {
  const labels: Record<string, string> = {
    vault_created: "Cofre criado",
    login: "Login",
    secret_revealed: "Senha revelada",
    entry_created: "Criado",
    entry_updated: "Atualizado",
    entry_deleted: "Excluído",
    login_password_changed: "Senha de login alterada"
  };
  return labels[action] ?? action;
}
