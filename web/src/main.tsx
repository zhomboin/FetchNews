import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";

import { LoginPage } from "./features/auth/login-page";
import { ArticlesPage } from "./features/articles/articles-page";
import { ArticleHistoryDetailPage } from "./features/articles/article-history-detail-page";
import { IngestionRunsPage } from "./features/ingestion/ingestion-runs-page";
import { OpsDashboardPage } from "./features/ops/ops-dashboard-page";
import { OpsDetailPage } from "./features/ops/ops-detail-page";
import { StoriesPage } from "./features/stories/stories-page";
import { configureAccessTokenResolver, fetchAuthConfig, fetchCurrentUser, fetchHealth, login } from "./lib/api";
import { getAccessToken, useAuthStore } from "./lib/auth-store";
import "./styles.css";

const QUERY_CLIENT = new QueryClient();
const DEFAULT_HEALTH_STATUS = "Preview mode";
const BACKEND_OFFLINE_STATUS = "Preview mode | Backend offline";
const NAV_SECTIONS = [
  { path: "/", label: "Overview" },
  { path: "/ingestion", label: "Ingestion" },
  { path: "/stories", label: "Stories" },
  { path: "/articles", label: "Drafts" },
  { path: "/publishing", label: "Publishing" },
] as const;

configureAccessTokenResolver(getAccessToken);

type ShellProps = {
  health: string;
  onLogout: () => void;
};

function Shell({ health, onLogout }: ShellProps): React.JSX.Element {
  const currentUser = useAuthStore((state) => state.user);

  return (
    <div className="console-shell">
      <aside className="console-rail">
        <div className="rail-head">
          <div className="brand-mark">
            <span />
            <span />
          </div>
          <div>
            <p className="brand-name">FetchNews</p>
            <p className="brand-subtitle">Signal Review Console</p>
          </div>
        </div>

        <nav className="rail-nav">
          {NAV_SECTIONS.map((section) => (
            <NavLink key={section.path} to={section.path} end={section.path === "/"}>
              {section.label}
            </NavLink>
          ))}
        </nav>

        <div className="rail-foot">
          <p>Operator</p>
          <strong>{currentUser?.displayName ?? "Guest"}</strong>
          <span>{currentUser?.role ?? "auth disabled"}</span>
          <button type="button" className="detail-link detail-link-soft rail-logout" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="console-main">
        <Routes>
          <Route path="/" element={<OpsDashboardPage health={health} mode="overview" />} />
          <Route path="/ingestion" element={<IngestionRunsPage health={health} />} />
          <Route path="/stories" element={<StoriesPage health={health} />} />
          <Route path="/articles" element={<ArticlesPage health={health} />} />
          <Route path="/articles/history" element={<ArticleHistoryDetailPage />} />
          <Route path="/publishing" element={<OpsDashboardPage health={health} mode="publishing" />} />
          <Route path="/ops/details" element={<OpsDetailPage health={health} />} />
          <Route path="*" element={<OpsDashboardPage health={health} mode="overview" />} />
        </Routes>
      </main>
    </div>
  );
}

function App(): React.JSX.Element {
  const [health, setHealth] = React.useState(DEFAULT_HEALTH_STATUS);
  const [loginError, setLoginError] = React.useState<string | null>(null);
  const [loginPending, setLoginPending] = React.useState(false);
  const [authSyncPending, setAuthSyncPending] = React.useState(true);

  const authEnabled = useAuthStore((state) => state.authEnabled);
  const configLoaded = useAuthStore((state) => state.configLoaded);
  const currentUser = useAuthStore((state) => state.user);
  const accessToken = useAuthStore((state) => state.accessToken);
  const setAuthConfig = useAuthStore((state) => state.setAuthConfig);
  const setSession = useAuthStore((state) => state.setSession);
  const clearSession = useAuthStore((state) => state.clearSession);

  React.useEffect(() => {
    fetchHealth()
      .then((data) => setHealth(`${data.service} | ${data.status}`))
      .catch(() => setHealth(BACKEND_OFFLINE_STATUS));
  }, []);

  React.useEffect(() => {
    let cancelled = false;

    async function syncAuth(): Promise<void> {
      try {
        const config = await fetchAuthConfig();
        if (cancelled) {
          return;
        }
        setAuthConfig(config.authEnabled);

        if (!config.authEnabled) {
          setAuthSyncPending(false);
          return;
        }

        if (accessToken === null) {
          clearSession();
          setAuthSyncPending(false);
          return;
        }

        const user = await fetchCurrentUser();
        if (cancelled) {
          return;
        }
        setSession(accessToken, user);
      } catch {
        if (!cancelled) {
          setAuthConfig(false);
          clearSession();
        }
      } finally {
        if (!cancelled) {
          setAuthSyncPending(false);
        }
      }
    }

    void syncAuth();

    return () => {
      cancelled = true;
    };
  }, [accessToken, clearSession, setAuthConfig, setSession]);

  async function handleLogin(username: string, password: string): Promise<void> {
    setLoginPending(true);
    setLoginError(null);
    try {
      const session = await login({ username, password });
      setSession(session.accessToken, session.user);
    } catch {
      setLoginError("登录失败，请检查用户名和密码。");
    } finally {
      setLoginPending(false);
    }
  }

  function handleLogout(): void {
    clearSession();
    QUERY_CLIENT.clear();
    setLoginError(null);
  }

  if (!configLoaded || authSyncPending) {
    return (
      <div className="login-shell">
        <section className="login-panel login-loading-panel">
          <p className="eyebrow">Protected Console</p>
          <h1>正在同步登录状态</h1>
          <p className="lede">系统正在确认鉴权配置和当前会话，请稍候。</p>
        </section>
      </div>
    );
  }

  if (authEnabled && currentUser === null) {
    return <LoginPage errorMessage={loginError} isSubmitting={loginPending} onSubmit={handleLogin} />;
  }

  return (
    <BrowserRouter>
      <Shell health={health} onLogout={handleLogout} />
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={QUERY_CLIENT}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
