import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { ArticlesPage } from "./features/articles/articles-page";
import { IngestionRunsPage } from "./features/ingestion/ingestion-runs-page";
import { PreviewDashboard } from "./features/preview/preview-dashboard";
import { StoriesPage } from "./features/stories/stories-page";
import { fetchHealth } from "./lib/api";
import "./styles.css";

const QUERY_CLIENT = new QueryClient();
const DEFAULT_HEALTH_STATUS = "预览模式";
const BACKEND_OFFLINE_STATUS = "预览模式 | 后端未连接";
const NAV_SECTIONS = [
  { path: "/", label: "总览" },
  { path: "/ingestion", label: "采集运行" },
  { path: "/stories", label: "聚类结果" },
  { path: "/articles", label: "草稿中心" },
  { path: "/publishing", label: "发布与日志" },
];

function Shell(): React.JSX.Element {
  const location = useLocation();
  const [health, setHealth] = React.useState(DEFAULT_HEALTH_STATUS);

  React.useEffect(() => {
    fetchHealth()
      .then((data) => setHealth(`${data.service} | ${data.status}`))
      .catch(() => setHealth(BACKEND_OFFLINE_STATUS));
  }, []);

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
          <p>主题方向</p>
          <strong>暖白金属极简</strong>
          <span>企业秩序感 + 轻未来感</span>
        </div>
      </aside>

      <main className="console-main">
        <Routes>
          <Route path="/" element={<PreviewDashboard health={health} currentPath={location.pathname} />} />
          <Route path="/ingestion" element={<IngestionRunsPage health={health} />} />
          <Route path="/stories" element={<StoriesPage health={health} />} />
          <Route path="/articles" element={<ArticlesPage health={health} />} />
          <Route path="/publishing" element={<PreviewDashboard health={health} currentPath={location.pathname} />} />
          <Route path="*" element={<PreviewDashboard health={health} currentPath={location.pathname} />} />
        </Routes>
      </main>
    </div>
  );
}

function App(): React.JSX.Element {
  return (
    <BrowserRouter>
      <Shell />
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