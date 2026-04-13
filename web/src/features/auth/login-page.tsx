import React from "react";

type LoginPageProps = {
  errorMessage: string | null;
  isSubmitting: boolean;
  onSubmit: (username: string, password: string) => Promise<void> | void;
};

/**
 * Minimal login entry for the protected review console.
 */
export function LoginPage({ errorMessage, isSubmitting, onSubmit }: LoginPageProps): React.JSX.Element {
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await onSubmit(username.trim(), password);
  }

  return (
    <div className="login-shell">
      <section className="login-panel">
        <div className="login-copy">
          <p className="eyebrow">受保护控制台</p>
          <h1>登录 FetchNews 控制台</h1>
          <p className="lede">使用具备权限的账号进入审核、编辑和运维界面，继续处理 AI 资讯生产链路。</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="field-shell">
            <span>用户名</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="请输入用户名"
            />
          </label>

          <label className="field-shell">
            <span>密码</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="请输入密码"
            />
          </label>

          {errorMessage ? <p className="login-error">{errorMessage}</p> : null}

          <button
            type="submit"
            className="button-primary login-submit"
            disabled={isSubmitting || username.trim() === "" || password === ""}
          >
            {isSubmitting ? "登录中..." : "登录"}
          </button>
        </form>
      </section>
    </div>
  );
}
