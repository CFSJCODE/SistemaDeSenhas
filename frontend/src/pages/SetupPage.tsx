import { FormEvent, useState } from "react";
import { KeyRound, LockKeyhole } from "lucide-react";

import { api } from "../services/api";
import type { AuthResponse } from "../types";

type Props = {
  onSetup: (auth: AuthResponse) => void;
  initialError?: string;
};

export default function SetupPage({ onSetup, initialError = "" }: Props) {
  const [adminUsername, setAdminUsername] = useState("admin");
  const [adminPassword, setAdminPassword] = useState("");
  const [viewerUsername, setViewerUsername] = useState("user");
  const [viewerPassword, setViewerPassword] = useState("");
  const [error, setError] = useState(initialError);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const auth = await api.setup({
        admin_username: adminUsername,
        admin_password: adminPassword,
        viewer_username: viewerUsername,
        viewer_password: viewerPassword
      });
      onSetup(auth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao criar o cofre.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-panel">
        <div className="auth-mark">
          <LockKeyhole size={24} />
          <span>Sistema de Senhas</span>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Admin
            <input value={adminUsername} onChange={(event) => setAdminUsername(event.target.value)} />
          </label>
          <label>
            Senha admin
            <input
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={adminPassword}
              onChange={(event) => setAdminPassword(event.target.value)}
            />
          </label>
          <label>
            Leitura
            <input value={viewerUsername} onChange={(event) => setViewerUsername(event.target.value)} />
          </label>
          <label>
            Senha leitura
            <input
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={viewerPassword}
              onChange={(event) => setViewerPassword(event.target.value)}
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-button" disabled={submitting} type="submit">
            <KeyRound size={18} />
            {submitting ? "Criando..." : "Criar cofre"}
          </button>
        </form>
      </section>
    </main>
  );
}
