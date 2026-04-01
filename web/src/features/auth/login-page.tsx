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
  const [username, setUsername] = React.useState("admin");
  const [password, setPassword] = React.useState("admin-secret");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await onSubmit(username.trim(), password);
  }

  return (
    <div className="login-shell">
      <section className="login-panel">
        <div className="login-copy">
          <p className="eyebrow">Protected Console</p>
          <h1>???????</h1>
          <p className="lede">
            ??????????????????????????????????
          </p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="field-shell">
            <span>???</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="admin"
            />
          </label>

          <label className="field-shell">
            <span>??</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="?????"
            />
          </label>

          {errorMessage ? <p className="login-error">{errorMessage}</p> : null}

          <button
            type="submit"
            className="button-primary login-submit"
            disabled={isSubmitting || username.trim() === "" || password === ""}
          >
            {isSubmitting ? "???..." : "?????"}
          </button>
        </form>
      </section>
    </div>
  );
}
