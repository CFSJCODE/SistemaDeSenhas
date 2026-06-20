import { FormEvent, useState } from "react";
import { LogIn, LockKeyhole } from "lucide-react";

import { api } from "../services/api";
import type { AuthResponse } from "../types";

type Props = {
  onLogin: (auth: AuthResponse) => void;
  initialError?: string;
};

export default function LoginPage({ onLogin, initialError = "" }: Props) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(initialError);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const auth = await api.login({ username, password });
      onLogin(auth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao entrar.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-panel compact">
        <div className="auth-mark">
          <LockKeyhole size={24} />
          <span>Sistema de Senhas</span>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Usuário
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label>
            Senha
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-button" disabled={submitting} type="submit">
            <LogIn size={18} />
            {submitting ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}
