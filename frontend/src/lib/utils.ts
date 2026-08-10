import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8090/api";

export type User = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  created_at: string;
};

export type Brand = {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description?: string | null;
  website?: string | null;
  logo_url?: string | null;
  primary_color?: string | null;
  tone_of_voice?: string | null;
  target_audience?: string | null;
  default_cta?: string | null;
  is_active: boolean;
  created_at: string;
};

export type ActiveContext = {
  user: User;
  organization?: Organization | null;
  brand?: Brand | null;
  role?: string | null;
  permissions: string[];
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
  failed_posts: number;
  scheduled_posts: number;
  approval_items: number;
  integration_health: { platform: string; status: string }[];
  ai_recommendations: string[];
};

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}
