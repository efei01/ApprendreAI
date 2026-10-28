import type { AnalysisResult } from "./types";

// Replaced with the real value at build time. It is public (visible in the browser),
// which is fine: it is only a URL. Secrets never go in NEXT_PUBLIC_ variables.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** An error whose message is safe and readable to show to the user. */
export class ApiError extends Error {}

export async function analyzePassage(text: string): Promise<AnalysisResult> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
  } catch {
    // fetch() only throws when no HTTP response arrived at all (server down, CORS blocked, offline).
    throw new ApiError("Could not reach the server. Is the backend running?");
  }

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response));
  }
  return (await response.json()) as AnalysisResult;
}

/** FastAPI errors look like {"detail": "..."} or, for validation errors, {"detail": [{"msg": "..."}]}. */
async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = body.detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail) && typeof detail[0]?.msg === "string") {
        return `Invalid input: ${detail[0].msg}`;
      }
    }
  } catch {
    // Response body was not JSON; fall through to the generic message.
  }
  return `Request failed (HTTP ${response.status}). Please try again.`;
}
