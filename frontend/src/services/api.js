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
  return request("/territories?include_test=false", { signal });
}

export function getTasks(territoryId, { signal } = {}) {
  return request(`/tasks${territoryQuery(territoryId)}`, { signal });
}

export function getTrains(territoryId, { signal } = {}) {
  return request(`/trains${territoryQuery(territoryId)}`, { signal });
}

export function getRollingPlan(territoryId, { signal } = {}) {
  return request(`/rolling-plan${territoryQuery(territoryId)}`, { signal });
}

export function getResources(territoryId, { signal } = {}) {
  return request(`/resources${territoryQuery(territoryId)}`, { signal });
}

export function getAlerts(territoryId, { signal } = {}) {
  return request(`/alerts${territoryQuery(territoryId)}`, { signal });
}

export function getDataSources(territoryId, { signal } = {}) {
  return request(`/data-sources${territoryQuery(territoryId)}`, { signal });
}

export function transitionPlan(planId, targetState, { actor = "planner", note = "", signal } = {}) {
  return request(`/plans/${encodeURIComponent(planId)}/transition`, {
    method: "POST", signal, headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_state: targetState, actor, note }),
  });
}

export function transitionBlock(planId, blockId, targetStatus, { actor = "planner", signal } = {}) {
  return request(`/plans/${encodeURIComponent(planId)}/blocks/${encodeURIComponent(blockId)}/status`, {
    method: "POST", signal, headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_status: targetStatus, actor }),
  });
}

export function runWhatIf(territoryId, taskOverrides, { parentPlanId, signal } = {}) {
  return request("/what-if", {
    method: "POST", signal, headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ territory_id: territoryId, task_overrides: taskOverrides, parent_plan_id: parentPlanId }),
  });
}

export function explainBlock(block, { signal } = {}) {
  return request("/explain", {
    method: "POST", signal, headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ block }),
  });
}

export function askCopilot(payload, { signal } = {}) {
  return request("/copilot", {
    method: "POST", signal, headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function validateTaskImport(territoryId, records, { signal, workbookBase64 } = {}) {
  return request("/import/tasks/validate", {
    method: "POST", signal, headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ territory_id: territoryId, records, workbook_base64: workbookBase64 }),
  });
}

async function downloadExport(path, blocks, filename, { print = false } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blocks }),
  });
  if (!response.ok) throw new ApiError(`Export failed with HTTP ${response.status}.`, { status: response.status });
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  if (print) {
    const report = window.open(url, "_blank", "noopener,noreferrer");
    if (!report) throw new ApiError("Allow pop-ups to open the print/PDF report.");
  } else {
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = filename; anchor.click();
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 30000);
}

export function exportBlocksCsv(blocks) {
  return downloadExport("/export/blocks.csv", blocks, "railsync-blocks.csv");
}

export function openPrintReport(blocks) {
  return downloadExport("/export/print", blocks, "railsync-plan.html", { print: true });
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
