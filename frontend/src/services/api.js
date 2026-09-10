const DEFAULT_API_BASE_URL = "/api";

export const API_BASE_URL = (
  import.meta.env?.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, { status = 0, code = "BACKEND_UNAVAILABLE" } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...options.headers,
      },
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError("RailSync backend is unavailable.");
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // The status remains useful even when a server returns a non-JSON error page.
  }

  if (!response.ok) {
    if (response.status === 502 || response.status === 504) {
      throw new ApiError("RailSync backend is unavailable.");
    }
    const detail = payload?.detail;
    throw new ApiError(
      detail?.message || `RailSync request failed with HTTP ${response.status}.`,
      {
        status: response.status,
        code: detail?.code || `HTTP_${response.status}`,
      },
    );
  }

  return payload;
}

function territoryQuery(territoryId) {
  return `?territory_id=${encodeURIComponent(territoryId)}`;
}

export function getTerritory(territoryId, { signal } = {}) {
  return request(`/dashboard${territoryQuery(territoryId)}`, { signal });
}

export function getTerritories({ signal } = {}) {
  return request("/territories", { signal });
}

export function getTasks(territoryId, { signal } = {}) {
  return request(`/tasks${territoryQuery(territoryId)}`, { signal });
}

export function getTrains(territoryId, { signal } = {}) {
  return request(`/trains${territoryQuery(territoryId)}`, { signal });
}

export function optimizePlan(territoryId, { signal, risk_mode = "STATIC", risk_profiles = [] } = {}) {
  return request("/optimize", {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ territory_id: territoryId, risk_mode, risk_profiles }),
  });
}

export function getMlStatus({ signal } = {}) {
  return request("/ml/status", { signal });
}

export function reoptimizePlan(plan, disruption, { signal, risk_mode = "STATIC", risk_profiles = [] } = {}) {
  return request("/reoptimize", {
    method: "POST", signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      territory_id: plan.planning_context.territory_id,
      horizon_start: plan.planning_context.horizon_start,
      horizon_end: plan.planning_context.horizon_end,
      current_plan: { blocks: plan.blocks, unscheduled_tasks: plan.unscheduled_tasks },
      disruption, risk_mode, risk_profiles,
    }),
  });
}
