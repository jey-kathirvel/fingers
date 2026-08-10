"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  apiFetch,
  type ActiveContext,
  type Brand,
  type Organization,
} from "@/lib/utils";

type AuthState = {
  token: string | null;
  context: ActiveContext | null;
  brands: Brand[];
  organizations: Organization[];
  activeBrandId: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  setActiveBrandId: (id: string) => void;
};

const AuthContext = createContext<AuthState | null>(null);
const TOKEN_KEY = "fingers_token";
const BRAND_KEY = "fingers_active_brand";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [context, setContext] = useState<ActiveContext | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [activeBrandId, setActiveBrandIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const setActiveBrandId = useCallback((id: string) => {
    setActiveBrandIdState(id);
    localStorage.setItem(BRAND_KEY, id);
  }, []);

  const refresh = useCallback(async () => {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (!saved) {
      setToken(null);
      setContext(null);
      setBrands([]);
      setOrganizations([]);
      setLoading(false);
      return;
    }
    setToken(saved);
    const me = await apiFetch<ActiveContext>("/auth/me", {}, saved);
    setContext(me);
    const orgs = await apiFetch<Organization[]>("/organizations", {}, saved);
    setOrganizations(orgs);
    const orgId = me.organization?.id || orgs[0]?.id;
    if (orgId) {
      const brandList = await apiFetch<Brand[]>(
        `/brands?organization_id=${orgId}`,
        {},
        saved,
      );
      setBrands(brandList);
      const savedBrand = localStorage.getItem(BRAND_KEY);
      const nextBrand =
        brandList.find((b) => b.id === savedBrand)?.id ||
        me.brand?.id ||
        brandList[0]?.id ||
        null;
      if (nextBrand) setActiveBrandId(nextBrand);
    }
    setLoading(false);
  }, [setActiveBrandId]);

  useEffect(() => {
    refresh().catch(() => {
      localStorage.removeItem(TOKEN_KEY);
      setLoading(false);
    });
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem(TOKEN_KEY, res.access_token);
      setToken(res.access_token);
      await refresh();
    },
    [refresh],
  );

  const logout = useCallback(async () => {
    if (token) {
      try {
        await apiFetch("/auth/logout", { method: "POST" }, token);
      } catch {
        // ignore network logout failures
      }
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(BRAND_KEY);
    setToken(null);
    setContext(null);
    setBrands([]);
    setOrganizations([]);
    setActiveBrandIdState(null);
  }, [token]);

  const value = useMemo(
    () => ({
      token,
      context,
      brands,
      organizations,
      activeBrandId,
      loading,
      login,
      logout,
      refresh,
      setActiveBrandId,
    }),
    [
      token,
      context,
      brands,
      organizations,
      activeBrandId,
      loading,
      login,
      logout,
      refresh,
      setActiveBrandId,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
