import { create } from "zustand";

import type { AuthUserRecord } from "./api";

const AUTH_STORAGE_KEY = "fetchnews-auth-session";

type StoredAuthSession = {
  accessToken: string | null;
  user: AuthUserRecord | null;
};

type AuthState = StoredAuthSession & {
  authEnabled: boolean;
  configLoaded: boolean;
  setAuthConfig: (authEnabled: boolean) => void;
  setSession: (accessToken: string, user: AuthUserRecord) => void;
  clearSession: () => void;
};

function readStoredSession(): StoredAuthSession {
  if (typeof window === "undefined") {
    return { accessToken: null, user: null };
  }

  const rawValue = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (rawValue === null) {
    return { accessToken: null, user: null };
  }

  try {
    const parsed = JSON.parse(rawValue) as Partial<StoredAuthSession>;
    return {
      accessToken: typeof parsed.accessToken === "string" ? parsed.accessToken : null,
      user: parsed.user ?? null,
    };
  } catch {
    return { accessToken: null, user: null };
  }
}

function writeStoredSession(session: StoredAuthSession): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

const INITIAL_SESSION = readStoredSession();

/**
 * Minimal auth state for the internal review console.
 */
export const useAuthStore = create<AuthState>((set) => ({
  accessToken: INITIAL_SESSION.accessToken,
  user: INITIAL_SESSION.user,
  authEnabled: false,
  configLoaded: false,
  setAuthConfig: (authEnabled) =>
    set((current) => {
      if (!authEnabled) {
        writeStoredSession({ accessToken: null, user: null });
        return {
          ...current,
          authEnabled,
          configLoaded: true,
          accessToken: null,
          user: null,
        };
      }
      return { ...current, authEnabled, configLoaded: true };
    }),
  setSession: (accessToken, user) => {
    writeStoredSession({ accessToken, user });
    set({ accessToken, user });
  },
  clearSession: () => {
    writeStoredSession({ accessToken: null, user: null });
    set({ accessToken: null, user: null });
  },
}));

export function getAccessToken(): string | null {
  return useAuthStore.getState().accessToken;
}
