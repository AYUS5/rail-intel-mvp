import type { SearchTelemetry, TrainSearchRequest, TrainSearchResponse } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_RAIL_INTEL_API_BASE_URL ?? "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = Number(process.env.NEXT_PUBLIC_RAIL_INTEL_REQUEST_TIMEOUT_MS ?? 12000);

export interface SearchResultEnvelope {
  data: TrainSearchResponse;
  telemetry: SearchTelemetry;
}

export class RailIntelApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
  ) {
    super(message);
    this.name = "RailIntelApiError";
  }
}

export async function searchTrains(request: TrainSearchRequest): Promise<SearchResultEnvelope> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const requestStartedAt = new Date();
  const requestUrl = `${API_BASE_URL.replace(/\/$/, "")}/api/v1/search/trains`;

  try {
    const response = await fetch(requestUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    if (!response.ok) {
      const detail = await readErrorDetail(response);
      throw new RailIntelApiError(detail, response.status);
    }

    const data = (await response.json()) as TrainSearchResponse;
    const requestCompletedAt = new Date();
    return {
      data,
      telemetry: {
        latencyMs: requestCompletedAt.getTime() - requestStartedAt.getTime(),
        requestUrl,
        requestStartedAt: requestStartedAt.toISOString(),
        requestCompletedAt: requestCompletedAt.toISOString(),
      },
    };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new RailIntelApiError(`Request timed out after ${REQUEST_TIMEOUT_MS} ms`);
    }
    if (error instanceof RailIntelApiError) {
      throw error;
    }
    throw new RailIntelApiError(error instanceof Error ? error.message : "Unknown backend error");
  } finally {
    window.clearTimeout(timeout);
  }
}

async function readErrorDetail(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Backend returned HTTP ${response.status}`;
  } catch {
    return `Backend returned HTTP ${response.status}`;
  }
}

