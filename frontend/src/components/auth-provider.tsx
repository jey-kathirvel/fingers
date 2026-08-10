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
  api,
  getActiveBrandId,
  getActiveOrgId,
  getToken,
  setActiveBrandId,
  setActiveOrgId,
  setToken,
  type Brand,
  type Membership,
  type User,
} from "@/lib/api";

type AuthState = {
  ready: boolean;
  user: User | null;
  memberships: Membership[];
  brands: Brand[];
  orgId: string | null;
  brandId: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setOrgId: (id: string) => Promise<void>;
  setBrandId: (id: string) => void;
  refreshBrands: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [orgId, setOrgIdState] = useState<string | null>(null);
  const [brandId, setBrandIdState] = useState<string | null>(null);

  const refreshBrands = useCallback(async (organizationId?: string | null) => {
    const activeOrg = organizationId ?? getActiveOrgId();
    if (!activeOrg || !getToken()) {
      setBrands([]);
      return;
    }
    const list = await api<Brand[]>("/api/brands", { orgId: activeOrg });
    setBrands(list);
    const currentBrand = getActiveBrandId();
    if (currentBrand && list.some((b) => b.id === currentBrand)) {
      setBrandIdState(currentBrand);
    } else if (list[0]) {
      setActiveBrandId(list[0].id);
      setBrandIdState(list[0].id);
    } else {
      setActiveBrandId(null);
      setBrandIdState(null);
    }
  }, []);

  const bootstrap = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setReady(true);
      return;
    }
    try {
      const me = await api<User>("/api/auth/me");
      const membershipList = await api<Membership[]>("/api/users/me/memberships");
      setUser(me);
      setMemberships(membershipList);
      let activeOrg = getActiveOrgId();
      if (!activeOrg || !membershipList.some((m) => m.organization_id === activeOrg)) {
        activeOrg = membershipList[0]?.organization_id ?? null;
        setActiveOrgId(activeOrg);
      }
      setOrgIdState(activeOrg);
      await refreshBrands(activeOrg);
    } catch {
      setToken(null);
      setUser(null);
      setMemberships([]);
      setBrands([]);
    } finally {
      setReady(true);
    }
  }, [refreshBrands]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api<{ access_token: string }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
        orgId: null,
      });
      setToken(res.access_token);
      setReady(false);
      await bootstrap();
    },
    [bootstrap],
  );

  const logout = useCallback(async () => {
    try {
      if (getToken()) await api("/api/auth/logout", { method: "POST" });
    } catch {
      /* ignore */
    }
    setToken(null);
    setActiveOrgId(null);
    setActiveBrandId(null);
    setUser(null);
    setMemberships([]);
    setBrands([]);
    setOrgIdState(null);
    setBrandIdState(null);
  }, []);

  const setOrgId = useCallback(
    async (id: string) => {
      setActiveOrgId(id);
      setOrgIdState(id);
      await refreshBrands(id);
    },
    [refreshBrands],
  );

  const setBrandId = useCallback((id: string) => {
    setActiveBrandId(id);
    setBrandIdState(id);
  }, []);

  const value = useMemo(
    () => ({
      ready,
      user,
      memberships,
      brands,
      orgId,
      brandId,
      login,
      logout,
      setOrgId,
      setBrandId,
      refreshBrands: () => refreshBrands(),
    }),
    [
      ready,
      user,
      memberships,
      brands,
      orgId,
      brandId,
      login,
      logout,
      setOrgId,
      setBrandId,
      refreshBrands,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
