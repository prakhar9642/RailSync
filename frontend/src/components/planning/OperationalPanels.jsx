import { useEffect, useMemo, useState } from "react";
import {
  askCopilot,
  exportBlocksCsv,
  getAlerts,
  getDataSources,
  getResources,
  getRollingPlan,
  openPrintReport,
  runWhatIf,
  transitionPlan,
  transitionBlock,
  validateTaskImport,
} from "../../services/api.js";
import { proofLabel } from "../../utils/planningLabels.js";
import DataAssumptions from "../analysis/DataAssumptions.jsx";

const readable = (value = "") => value.toLowerCase().replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());

const NEXT_STATE = { DRAFT: "REVIEWED", REVIEWED: "APPROVED", APPROVED: "PUBLISHED" };
const NEXT_BLOCK_STATE = { DRAFT: "FROZEN", FROZEN: "IN_PROGRESS", IN_PROGRESS: "COMPLETED" };
const BLOCK_ACTION_LABEL = { DRAFT: "Freeze", FROZEN: "Start", IN_PROGRESS: "Complete", COMPLETED: "Completed", CANCELLED: "Cancelled" };

function parseImport(text, filename) {
  if (filename.toLowerCase().endsWith(".json")) return JSON.parse(text);
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  const headers = lines.shift().split(",").map((item) => item.trim());
  return lines.map((line) => Object.fromEntries(line.split(",").map((value, index) => {
    const key = headers[index];
    const cleaned = value.trim();
    return [key, ["duration_minutes", "criticality", "urgency", "overdue_days"].includes(key) ? Number(cleaned) : cleaned];
  })));
}

export default function OperationalPanels({ territory, plan, tasks, selectedTaskId, selectedBlock, onApplyPlan, onUpdateBlock }) {
  const [tab, setTab] = useState("monthly");
  const [operational, setOperational] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [identity, setIdentity] = useState(plan?.plan_identity ?? null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [whatIf, setWhatIf] = useState(null);
  const [copilotQuestion, setCopilotQuestion] = useState("");
  const [copilotAnswer, setCopilotAnswer] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const selectedTask = useMemo(() => tasks.find((item) => item.task_id === selectedTaskId), [tasks, selectedTaskId]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getRollingPlan(territory.territory_id, { signal: controller.signal }),
      getResources(territory.territory_id, { signal: controller.signal }),
      getAlerts(territory.territory_id, { signal: controller.signal }),
      getDataSources(territory.territory_id, { signal: controller.signal }),
    ]).then(([rolling, resources, alerts, sources]) => setOperational({ rolling, resources, alerts, sources }))
      .catch((error) => { if (error.name !== "AbortError") setLoadError(error); });
    return () => controller.abort();
  }, [territory.territory_id, plan?.plan_identity?.plan_id]);

  async function advanceLifecycle() {
    const target = NEXT_STATE[identity?.state];
    if (!target) return;
    setBusy(true); setMessage("");
    try {
      const result = await transitionPlan(identity.plan_id, target, { note: `Advanced from Planning Workspace` });
      setIdentity(result.identity); setMessage(`Plan advanced to ${readable(target).toLowerCase()}.`);
    } catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }

  async function advanceBlock() {
    const next = NEXT_BLOCK_STATE[selectedBlock?.status ?? "DRAFT"];
    if (!identity || !selectedBlock || !next) return;
    setBusy(true); setMessage("");
    try {
      const updated = await transitionBlock(identity.plan_id, selectedBlock.block_id, next);
      onUpdateBlock(updated); setMessage(`${selectedBlock.block_id} advanced to ${readable(next).toLowerCase()}.`);
    } catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }

  async function previewWhatIf() {
    if (!selectedTask) return;
    setBusy(true); setMessage("");
    try {
      const response = await runWhatIf(territory.territory_id, [{ task_id: selectedTask.task_id, duration_minutes: selectedTask.duration_minutes + 10 }], { parentPlanId: identity?.plan_id });
      setWhatIf(response.result);
    } catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }

  async function ask(event) {
    event.preventDefault(); if (!copilotQuestion.trim()) return;
    setBusy(true);
    try {
      const actionRequested = /what.?if|move|reschedul|extend/i.test(copilotQuestion) && selectedTask;
      const result = await askCopilot({
        territory_id: territory.territory_id,
        question: copilotQuestion,
        selected_block: selectedBlock,
        parent_plan_id: identity?.plan_id,
        task_overrides: actionRequested ? [{ task_id: selectedTask.task_id, duration_minutes: selectedTask.duration_minutes + 10 }] : [],
      });
      setCopilotAnswer(result);
    } catch (error) { setCopilotAnswer({ answer: error.message, engine: "ERROR" }); } finally { setBusy(false); }
  }

  async function importFile(event) {
    const file = event.target.files?.[0]; if (!file) return;
    try {
      if (file.name.toLowerCase().endsWith(".xlsx")) {
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        for (let offset = 0; offset < bytes.length; offset += 32768) {
          binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
        }
        setImportResult(await validateTaskImport(territory.territory_id, null, { workbookBase64: btoa(binary) }));
      } else {
        const records = parseImport(await file.text(), file.name);
        setImportResult(await validateTaskImport(territory.territory_id, records));
      }
    } catch (error) { setImportResult({ valid: false, errors: [{ code: "PARSE_ERROR", detail: error.message }] }); }
  }

  const rollingRows = operational?.rolling?.[tab] ?? [];
  const alerts = operational?.alerts?.alerts ?? [];
  return <div className="operations-shell compact-tools">
    <details className="operations-card">
      <summary>Alerts · {operational ? alerts.length : "…"}</summary>
      <div className="tool-body"><ul className="operations-list">{alerts.map((alert) => <li key={alert.code + alert.task_id}>
        <strong>{alert.code === "OVERDUE_MAINTENANCE" ? "Maintenance overdue" : alert.code === "CRITICAL_TASK_PENDING" ? "Critical maintenance pending" : readable(alert.code)}</strong>
        <small>{readable(alert.severity)} priority</small><p>{alert.message}</p>
      </li>)}{operational && !alerts.length ? <li>No active alerts.</li> : null}</ul></div>
    </details>
    <details className="operations-card">
      <summary>Resources</summary>
      <div className="tool-body">{operational ? <dl className="resource-counts">
        <div><dt>Crews</dt><dd>{operational.resources.crew.length} pools</dd></div>
        <div><dt>Machines</dt><dd>{operational.resources.machines.length} pools</dd></div>
        <div><dt>Power</dt><dd>{Object.keys(operational.resources.power_windows).length} calendars</dd></div>
      </dl> : <p>Loading resources…</p>}</div>
    </details>
    <details className="operations-card">
      <summary>Plan Tools</summary>
      <div className="tool-body">
        <h3>Rolling planning</h3>
        <div className="operations-tabs">{[["monthly", "Monthly"], ["weekly", "Weekly"], ["day_of", "Day-of"]].map(([key, label]) => <button key={key} type="button" className={tab === key ? "is-active" : ""} onClick={() => setTab(key)}>{label}</button>)}</div>
        <ul className="operations-list">{rollingRows.map((row, index) => <li key={row.period ?? row.date ?? index}><strong>{row.period ?? row.date}</strong><p>{readable(row.planning_state)} · {row.demand_count ?? row.candidate_task_ids?.length ?? row.blocks?.length ?? 0} items</p></li>)}</ul>
        <h3>Plan lifecycle</h3>
        {identity ? <><p><span className="lifecycle-badge">{readable(identity.state)}</span> Version {identity.version}</p>
          <div className="operations-actions">
            <button type="button" disabled={busy || !NEXT_STATE[identity.state]} onClick={advanceLifecycle}>{NEXT_STATE[identity.state] ? `Advance to ${readable(NEXT_STATE[identity.state]).toLowerCase()}` : "Published"}</button>
            <button type="button" disabled={busy || !selectedBlock || !NEXT_BLOCK_STATE[selectedBlock?.status ?? "DRAFT"]} onClick={advanceBlock}>{selectedBlock ? `${BLOCK_ACTION_LABEL[selectedBlock.status ?? "DRAFT"] ?? "Update"} ${selectedBlock.block_id}` : "Select block"}</button>
            <button type="button" onClick={() => exportBlocksCsv(plan.blocks)}>Export CSV</button>
            <button type="button" onClick={() => openPrintReport(plan.blocks)}>Print / PDF</button>
          </div></> : <p>Generate a plan to start a draft.</p>}
        <h3>Plan alternatives</h3>
        <ul className="operations-list">{(plan?.alternatives ?? []).map((alternative) => <li key={alternative.alternative_id}><strong>{alternative.label}</strong><p>{alternative.metrics.possession_minutes} possession min · {alternative.metrics.scheduled_task_count} tasks · {proofLabel(alternative.proof_state)}</p><small>{alternative.tradeoff}</small></li>)}</ul>
        <h3>What-if preview</h3>
        <p>{selectedTask ? `Test ${selectedTask.task_type} at ${selectedTask.duration_minutes + 10} minutes (+10).` : "Select a maintenance task first."}</p>
        <div className="operations-actions"><button type="button" disabled={busy || !selectedTask} onClick={previewWhatIf}>Run what-if</button>{whatIf ? <button type="button" onClick={() => onApplyPlan(whatIf)}>Apply preview as new draft</button> : null}</div>
        {whatIf ? <p>{whatIf.blocks.length} blocks · {whatIf.unscheduled_tasks.length} outstanding · {proofLabel(whatIf.proof_state)}</p> : null}
        {message ? <p role="status">{message}</p> : null}
      </div>
    </details>
    <details className="operations-card">
      <summary>Data &amp; Assumptions</summary>
      <div className="tool-body">
        <dl className="resource-counts"><div><dt>Train traffic</dt><dd>Public timetable-derived</dd></div><div><dt>Maintenance demand</dt><dd>Prototype scenario</dd></div><div><dt>Optimization</dt><dd>RailSync CP-SAT</dd></div></dl>
        <DataAssumptions territory={territory} />
        <h3>Import Maintenance Demand</h3>
        <p>Preview and validate CSV, Excel or JSON demand.</p>
        <label className="import-file-label">Select demand file<input className="import-file-input" aria-label="Import maintenance demand" type="file" accept=".csv,.xlsx,.json" onChange={importFile} /></label>
        {importResult ? <p role="status">{importResult.valid ? `${importResult.preview.length} rows valid; preview only.` : `${importResult.errors.length} validation errors.`}</p> : null}
        {operational ? <p>{operational.sources.datasets.length} datasets · {operational.sources.service_source_urls.length} timetable sources</p> : null}
      </div>
    </details>
    <details className="operations-card copilot-tool">
      <summary>✦ RailSync Copilot</summary>
      <div className="tool-body"><p>Ask about the current plan or explore a what-if.</p>
        <form className="copilot-form" onSubmit={ask}><input aria-label="Ask RailSync Copilot" value={copilotQuestion} onChange={(event) => setCopilotQuestion(event.target.value)} placeholder="Why this possession?" /><button type="submit" disabled={busy}>Ask</button></form>
        {copilotAnswer ? <div className="copilot-answer"><p>{copilotAnswer.answer}</p>{copilotAnswer.action_preview ? <small>CP-SAT preview ready; the current plan is unchanged.</small> : null}</div> : null}
      </div>
    </details>
    {loadError ? <p role="alert">{loadError.message}</p> : null}
  </div>;
}
