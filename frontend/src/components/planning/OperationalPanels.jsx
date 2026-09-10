import { useEffect, useMemo, useState } from "react";
import {
  askCopilot,
  explainBlock,
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
  const [explanation, setExplanation] = useState(null);
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
      setIdentity(result.identity); setMessage(`Plan advanced to ${target}.`);
    } catch (error) { setMessage(error.message); } finally { setBusy(false); }
  }

  async function advanceBlock() {
    const next = NEXT_BLOCK_STATE[selectedBlock?.status ?? "DRAFT"];
    if (!identity || !selectedBlock || !next) return;
    setBusy(true); setMessage("");
    try {
      const updated = await transitionBlock(identity.plan_id, selectedBlock.block_id, next);
      onUpdateBlock(updated); setMessage(`${selectedBlock.block_id} advanced to ${next}.`);
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

  async function explainSelected() {
    if (!selectedBlock) return;
    setExplanation(await explainBlock(selectedBlock));
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
  return <div className="operations-shell">
    <section className="operations-card">
      <span className="planner-kicker">Rolling planning and control</span>
      <h2>Monthly → weekly → day-of</h2>
      <div className="operations-tabs">{[["monthly", "Monthly"], ["weekly", "Weekly"], ["day_of", "Day-of"]].map(([key, label]) => <button key={key} type="button" className={tab === key ? "is-active" : ""} onClick={() => setTab(key)}>{label}</button>)}</div>
      {loadError ? <p role="alert">{loadError.message}</p> : <ul className="operations-list">{rollingRows.map((row, index) => <li key={row.period ?? row.date ?? index}><strong>{row.period ?? row.date}</strong><br />{row.planning_state?.replaceAll("_", " ")} · {row.demand_count ?? row.candidate_task_ids?.length ?? row.blocks?.length ?? 0} item(s)</li>)}</ul>}
      <h3>Plan lifecycle</h3>
      {identity ? <><p><span className="lifecycle-badge">{identity.state}</span> {identity.plan_id} · version {identity.version}</p><div className="operations-actions"><button type="button" disabled={busy || !NEXT_STATE[identity.state]} onClick={advanceLifecycle}>{NEXT_STATE[identity.state] ? `Advance to ${NEXT_STATE[identity.state]}` : "Published"}</button><button type="button" disabled={busy || !selectedBlock || !NEXT_BLOCK_STATE[selectedBlock?.status ?? "DRAFT"]} onClick={advanceBlock}>{selectedBlock ? `${BLOCK_ACTION_LABEL[selectedBlock.status ?? "DRAFT"] ?? "Update"} ${selectedBlock.block_id}` : "Select block"}</button><button type="button" disabled={!plan} onClick={() => exportBlocksCsv(plan.blocks)}>Export CSV</button><button type="button" disabled={!plan} onClick={() => openPrintReport(plan.blocks)}>Print / PDF</button></div></> : <p>Generate a plan to start a controlled draft.</p>}
      <h3>Solver-backed alternatives</h3>
      <ul className="operations-list">{(plan?.alternatives ?? []).map((alternative) => <li key={alternative.alternative_id}><strong>{alternative.label}</strong><br />{alternative.metrics.possession_minutes} possession min · {alternative.metrics.scheduled_task_count} tasks · {alternative.proof_state.replaceAll("_", " ")}<br /><small>{alternative.tradeoff}</small></li>)}</ul>
      <h3>What-if preview</h3>
      <p>{selectedTask ? `Test ${selectedTask.task_type} at ${selectedTask.duration_minutes + 10} minutes (+10).` : "Select a maintenance task first."}</p>
      <div className="operations-actions"><button type="button" disabled={busy || !selectedTask} onClick={previewWhatIf}>Run what-if</button>{whatIf ? <button type="button" onClick={() => onApplyPlan(whatIf)}>Apply preview as new draft</button> : null}</div>
      {whatIf ? <p>Preview: {whatIf.blocks.length} blocks, {whatIf.unscheduled_tasks.length} outstanding · {whatIf.proof_state.replaceAll("_", " ")}. No base data changed.</p> : null}
      {message ? <p role="status">{message}</p> : null}
    </section>

    <section className="operations-card">
      <span className="planner-kicker">Operational context</span><h2>Resources, alerts, and Copilot</h2>
      <h3>Alerts</h3><ul className="operations-list">{(operational?.alerts?.alerts ?? []).slice(0, 4).map((alert) => <li key={alert.code + alert.task_id}><strong>{alert.severity} · {alert.code}</strong><br />{alert.message}</li>)}{operational?.alerts?.alerts?.length === 0 ? <li>No active derived alerts.</li> : null}</ul>
      <h3>Resource readiness</h3><p>{operational ? `${operational.resources.crew.length} crew pools · ${operational.resources.machines.length} machine pools · ${Object.keys(operational.resources.power_windows).length} section power calendars` : "Loading resources…"}</p>
      <h3>Explain selected decision</h3><div className="operations-actions"><button type="button" disabled={!selectedBlock} onClick={explainSelected}>Explain block</button></div>{explanation ? <div className="copilot-answer"><strong>{explanation.summary}</strong><p>{explanation.reasoning.join(" · ")}</p><small>{explanation.counterfactual}</small></div> : null}
      <h3>RailSync Copilot</h3><form className="copilot-form" onSubmit={ask}><input aria-label="Ask RailSync Copilot" value={copilotQuestion} onChange={(event) => setCopilotQuestion(event.target.value)} placeholder="Why this block, or what if it runs 10 min longer?" /><button type="submit" disabled={busy}>Ask</button></form>{copilotAnswer ? <div className="copilot-answer"><strong>{copilotAnswer.engine.replaceAll("_", " ")}</strong><p>{copilotAnswer.answer}</p>{copilotAnswer.action_preview ? <small>Action routed through CP-SAT; preview is not applied.</small> : null}</div> : null}
      <h3>Import maintenance demand</h3><p>Validate a canonical CSV, Excel, or JSON file before any import is applied.</p><input type="file" accept=".csv,.xlsx,.json" onChange={importFile} />{importResult ? <p className={importResult.valid ? "" : "is-error"}>{importResult.valid ? `${importResult.preview.length} row(s) valid; preview only.` : `${importResult.errors.length} validation error(s).`}</p> : null}
      <h3>Data sources</h3><p>{operational ? `${operational.sources.datasets.length} loaded datasets · ${operational.sources.service_source_urls.length} public timetable links · ${operational.sources.sources.map((item) => item.label).join(" + ")}` : "Loading provenance…"}</p>
    </section>
  </div>;
}
