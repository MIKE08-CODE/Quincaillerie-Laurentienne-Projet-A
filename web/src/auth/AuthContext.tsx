import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

import { authApi, type CurrentUser } from "../api/auth";

/**
 * Session web. Le jeton d'accès (15 min) reste EN MÉMOIRE seulement : jamais dans localStorage ni
 * sessionStorage (un script injecté ne peut pas le relire après rechargement). Le jeton de
 * rafraîchissement est un cookie httpOnly géré par le navigateur et l'API (A-AUTH-02).
 */
interface AuthState {
  token: string | null;
  user: CurrentUser | null;
  signIn: (token: string) => Promise<CurrentUser>;
  restore: () => Promise<CurrentUser | null>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<CurrentUser | null>(null);

  const signIn = useCallback(async (accessToken: string) => {
    const me = await authApi.me(accessToken);
    setToken(accessToken);
    setUser(me);
    return me;
  }, []);

  /** Après un rechargement de page : nouveau jeton d'accès à partir du cookie, s'il existe. */
  const restore = useCallback(async () => {
    try {
      const { access_token } = await authApi.refresh();
      return await signIn(access_token);
    } catch {
      return null;
    }
  }, [signIn]);

  const signOut = useCallback(async () => {
    try {
      await authApi.logout(token ?? undefined);
    } finally {
      setToken(null);
      setUser(null);
    }
  }, [token]);

  const value = useMemo(
    () => ({ token, user, signIn, restore, signOut }),
    [token, user, signIn, restore, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context)
    throw new Error("useAuth doit être utilisé dans <AuthProvider>");
  return context;
}
