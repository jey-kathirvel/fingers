export type User = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
};

export type Membership = {
  id: string;
  organization_id: string;
  user_id: string;
  role: string;
  organization?: Organization;
};

export type Brand = {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description?: string | null;
  website?: string | null;
  primary_color?: string | null;
  tone_of_voice?: string | null;
  target_audience?: string | null;
  is_active: boolean;
};

export type DashboardOverview = {
  followers: number;
  reach: number;
  impressions: number;
  engagement_rate: number;
  clicks: number;
  leads: number;
  published_posts: number;
  response_backlog: number;
  brands_count: number;
  connected_accounts: number;
  failed_posts: number;
  scheduled_posts: number;
  approval_items: number;
  integration_health: { platform: string; status: string }[];
  action_queue: { id: string; type: string; title: string; priority: string }[];
  recommendations: { id: string; title: string; detail: string }[];
};

const TOKEN_KEY = "fingers_token";
const ORG_KEY = "fingers_org";
const BRAND_KEY = "fingers_brand";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getActiveOrgId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ORG_KEY);
}

export function setActiveOrgId(id: string | null) {
  if (typeof window === "undefined") return;
  if (id) localStorage.setItem(ORG_KEY, id);
  else localStorage.removeItem(ORG_KEY);
}

export function getActiveBrandId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(BRAND_KEY);
}

export function setActiveBrandId(id: string | null) {
  if (typeof window === "undefined") return;
  if (id) localStorage.setItem(BRAND_KEY, id);
  else localStorage.removeItem(BRAND_KEY);
}

export async function api<T>(
  path: string,
  options: RequestInit & { orgId?: string | null } = {},
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const orgId = options.orgId === undefined ? getActiveOrgId() : options.orgId;
  if (orgId) headers.set("X-Organization-Id", orgId);

  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    let detail = "Request failed";
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
