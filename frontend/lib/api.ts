export const STATUSES = [
  "saved",
  "applied",
  "assessment",
  "interview",
  "offer",
  "rejected",
] as const;

export type Status = (typeof STATUSES)[number];

export interface Application {
  id: number;
  company: string;
  title: string;
  location: string | null;
  url: string | null;
  status: Status;
  description: string | null;
  notes: string | null;
  applied_on: string | null;
  created_at: string;
  updated_at: string;
}

export interface NewApplication {
  company: string;
  title: string;
  location?: string;
  url?: string;
  status?: Status;
  description?: string;
}

export type WorkMode = "onsite" | "hybrid" | "remote";

/** What the model pulled out of a pasted posting. Every field can be missing. */
export interface ExtractedJob {
  company: string | null;
  title: string | null;
  location: string | null;
  work_mode: WorkMode | null;
  salary_range: string | null;
  required_skills: string[];
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      // body was not JSON; keep the status text
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  list: () => request<Application[]>("/api/v1/applications?limit=200"),
  create: (input: NewApplication) =>
    request<Application>("/api/v1/applications", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  update: (id: number, patch: Partial<Pick<Application, "status" | "notes" | "applied_on">>) =>
    request<Application>(`/api/v1/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  remove: (id: number) =>
    request<void>(`/api/v1/applications/${id}`, { method: "DELETE" }),
  /** Extract fields from posting text. Nothing is saved until the user adds it. */
  extract: (text: string) =>
    request<ExtractedJob>("/api/v1/extract", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
};
