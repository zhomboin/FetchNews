import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";

import { fetchHealth } from "./lib/api";
import "./styles.css";

const queryClient = new QueryClient();

function Dashboard() {
  const [health, setHealth] = React.useState<string>("checking");

  React.useEffect(() => {
    fetchHealth()
      .then((data) => setHealth(`${data.service}: ${data.status}`))
      .catch(() => setHealth("backend unavailable"));
  }, []);

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">FetchNews Console</p>
        <h1>AI 资讯运营控制台骨架</h1>
        <p className="lede">
          当前是 Phase 01 最小骨架，目标是验证 React SPA、路由和 API 联通链路。
        </p>
        <div className="status-card">
          <span>Backend</span>
          <strong>{health}</strong>
        </div>
      </section>
    </main>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="frame">
        <aside className="nav">
          <div>
            <p className="brand">FN</p>
            <p className="brand-copy">FetchNews</p>
          </div>
          <nav>
            <NavLink to="/">Dashboard</NavLink>
            <NavLink to="/stories">Stories</NavLink>
            <NavLink to="/articles">Articles</NavLink>
            <NavLink to="/publishing">Publishing</NavLink>
          </nav>
        </aside>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/stories" element={<Dashboard />} />
          <Route path="/articles" element={<Dashboard />} />
          <Route path="/publishing" element={<Dashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
