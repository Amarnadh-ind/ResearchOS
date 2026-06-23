// ── ResearchOS API Client ─────────────────────────────

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TIMEOUT = 30000; // 30 seconds

async function fetcher<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);
  
  try {
    console.log("[DEBUG] FETCH START", { path, method: options?.method || "GET", url: `${API_URL}${path}` });
    const res = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
    
    console.log("[DEBUG] FETCH RESPONSE", { path, status: res.status, ok: res.ok });
    
    if (!res.ok) {
      const error = await res.text();
      console.error("[DEBUG] FETCH ERROR RESPONSE", { path, status: res.status, error });
      throw new Error(`API Error: ${res.status} - ${error}`);
    }
    
    const data = await res.json();
    console.log("[DEBUG] FETCH SUCCESS", { path, data });
    return data;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.error("[DEBUG] FETCH TIMEOUT", { path });
      throw new Error(`API Timeout: ${path} after ${API_TIMEOUT}ms`);
    }
    console.error("[DEBUG] FETCH EXCEPTION", { path, error });
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
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

  getPdfHealth: () =>
    fetcher<{ status: string; renderers: Record<string, unknown>; any_renderer_available: boolean }>("/api/diagnostics/pdf"),
};
