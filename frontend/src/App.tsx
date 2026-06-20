import { useEffect, useState } from "react";
import { LockKeyhole } from "lucide-react";

import LoginPage from "./pages/LoginPage";
import SetupPage from "./pages/SetupPage";
import VaultPage from "./pages/VaultPage";
import { api, clearToken, getStoredToken, storeToken } from "./services/api";
import type { AuthResponse, SessionInfo, StatusResponse } from "./types";

type AppState = "loading" | "setup" | "login" | "vault";

export default function App() {
  const [appState, setAppState] = useState<AppState>("loading");
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void bootstrap();
  }, []);

  async function bootstrap() {
    setError("");
    try {
      const currentStatus = await api.status();
      setStatus(currentStatus);
      if (!currentStatus.configured) {
        clearToken();
        setAppState("setup");
        return;
      }

      if (getStoredToken()) {
        try {
          const me = await api.me();
          setSession(me);
          setAppState("vault");
          return;
        } catch {
          clearToken();
        }
      }
      setAppState("login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar o aplicativo.");
      setAppState("login");
    }
  }

  function acceptAuth(auth: AuthResponse) {
    storeToken(auth.token);
    setSession({
      username: auth.username,
      role: auth.role,
      expires_at: auth.expires_at
    });
    setAppState("vault");
  }

  async function handleLogout() {
    try {
      await api.logout();
    } catch {
      // The local token is cleared even if the server session has already expired.
    }
    clearToken();
    setSession(null);
    setAppState(status?.configured === false ? "setup" : "login");
  }

  if (appState === "loading") {
    return (
      <main className="center-shell">
        <div className="brand-lock" aria-hidden="true">
          <LockKeyhole size={28} />
        </div>
      </main>
    );
  }

  if (appState === "setup") {
    return <SetupPage onSetup={acceptAuth} initialError={error} />;
  }

  if (appState === "vault" && session) {
    return <VaultPage session={session} vaultPath={status?.vault_path ?? ""} onLogout={handleLogout} />;
  }

  return <LoginPage onLogin={acceptAuth} initialError={error} />;
}
