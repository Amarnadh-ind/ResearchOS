// ── ResearchOS API Client ─────────────────────────────

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetcher<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error: ${res.status} - ${error}`);
  }
  return res.json();
}

export const api = {
  startResearch: (data: { prompt: string; depth: string; max_sources: number; pages?: number; layout?: string; font?: string; visual_mode?: string }) =>
    fetcher<{ session_id: string; status: string; message: string }>("/api/research", {
      method: "POST",
      body: JSON.stringify({ ...data, output_format: "ieee" }),
    }),

  getSession: (sessionId: string) =>
    fetcher<Record<string, unknown>>(`/api/research/${sessionId}`),

  getPaper: (sessionId: string) =>
    fetcher<Record<string, unknown>>(`/api/research/${sessionId}/paper`),

  listSessions: () =>
    fetcher<Record<string, unknown>[]>("/api/research"),

  getAgentsStatus: () =>
    fetcher<{ agents: Record<string, unknown>[] }>("/api/agents/status"),

  getPipelineInfo: () =>
    fetcher<{ pipeline: Record<string, unknown>[] }>("/api/agents/pipeline"),
};
