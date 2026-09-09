import { useEffect, useRef, useState } from "react";
import Navbar from "../components/layout/Navbar.jsx";
import Button from "../components/ui/Button.jsx";
import DataAssumptions from "../components/analysis/DataAssumptions.jsx";
import OutstandingWork from "../components/analysis/OutstandingWork.jsx";
import RiskControls, { RiskResult } from "../components/planning/RiskControls.jsx";
import { riskOptions } from "../utils/risk.js";
import RecoveryTimeline from "../components/planning/RecoveryTimeline.jsx";
import { reoptimizePlan } from "../services/api.js";
import { proofLabel, sectionLabel, trainLabel } from "../utils/planningLabels.js";
import "./scenario/scenario.css";
import "./analysis/analysis.css";

export default function ScenarioLab({ session, setSession, onNavigate, onHome }) {
  const { plan, territory, trains, tasks, recovery, riskConfig } = session;
  const trainIds = [...new Set(trains.map((r) => r.train_id))];
  const [trainId, setTrainId] = useState(recovery?.disruption.train_id ?? trainIds[0] ?? "");
  const [delay, setDelay] = useState(recovery?.disruption.delay_minutes ?? 25);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const controller = useRef(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function runScenario(event) {
    event.preventDefault();
    controller.current?.abort();
    const requestController = new AbortController();
    controller.current = requestController;
    setBusy(true); setError(null);
    setSession((current) => ({ ...current, recovery: null }));
    try {
      const result = await reoptimizePlan(plan, { type: "TRAIN_DELAY", train_id: trainId, delay_minutes: Number(delay) },
        { signal: requestController.signal, ...riskOptions(riskConfig) });
      if (requestController.signal.aborted) return;
      setSession((current) => current.plan === plan ? { ...current, recovery: result } : current);
    } catch (err) {
      if (err.name !== "AbortError") setError(err);
    } finally {
      if (!requestController.signal.aborted) setBusy(false);
    }
  }
  const names = new Map(tasks.map((t) => [t.task_id,t.task_type]));
  const metrics = recovery?.recovery_metrics;
  return <div className="scenario-page">
    <Navbar workspace activeWorkspaceView="scenario" onNavigateWorkspace={onNavigate} onHome={onHome} />
    <main className="scenario-main">
      <header className="scenario-hero"><span>Scenario Lab · Synthetic forecast experiment</span>
        <h1>What happens when reality changes?</h1>
        <p>Apply a train delay to the current planning result. RailSync repairs the plan while prioritizing maintenance service and preserving existing possessions where possible.</p>
      </header>
      {!plan ? <section className="analysis-empty">
        <h2>Generate a plan in Planning before running a scenario.</h2>
        <p>No base plan is available in this session.</p>
        <Button onClick={() => onNavigate("planning")}>Open Planning</Button>
      </section> : <>
        <form className="scenario-form" onSubmit={runScenario}>
          <div><span>Current base plan</span><strong>{plan.blocks.length} possessions · {proofLabel(plan.proof_state)}</strong><small>{territory.display_name}</small></div>
          <label>Disruption<select disabled aria-label="Disruption type"><option>Train delay</option></select></label>
          <label>Train<select aria-label="Scenario train" value={trainId} disabled={busy} onChange={(event) => setTrainId(event.target.value)}>
            {trainIds.map((id) => <option key={id} value={id}>{trainLabel(id,territory)} · {id}</option>)}
          </select></label>
          <label>Delay (minutes)<input aria-label="Delay minutes" type="number" min="0" max="1440" step="1" required value={delay} disabled={busy} onChange={(event) => setDelay(event.target.value)} /></label>
          <Button type="submit" disabled={busy || !trainId} ariaBusy={busy}>{busy ? "Recovering plan…" : "Run Scenario"}</Button>
        </form>
        <p className="scenario-note">Each run starts from the original Planning result. This is a full-horizon what-if simulation; it does not represent work already in progress or automatically approve a recovered plan.</p>
        <RiskControls config={riskConfig} onChange={(config) => setSession((current) => ({ ...current, riskConfig: config }))}
          trains={trains} territory={territory} disabled={busy} />
        {busy ? <p role="status">Recomputing protected train windows and solving minimum-change recovery…</p> : null}
        {error ? <div className="scenario-error" role="alert"><strong>Scenario failed</strong><p>{error.message}</p></div> : null}
        {recovery ? <>
          <section className="recovery-summary" aria-labelledby="recovery-heading">
            <div className="scenario-section-heading"><div><span>Returned by CP-SAT</span><h2 id="recovery-heading">Recovery result</h2></div>
              <strong>{proofLabel(recovery.recovered_plan.proof_state)}</strong></div>
            {recovery.recovered_plan.proof_state !== "FULLY_OPTIMAL" ? <p>Valid bounded recovery; minimum change is not fully proven.</p> : null}
            <p>{trainLabel(recovery.disruption.train_id,territory)} delayed by {recovery.disruption.delay_minutes} minutes. The original base plan remains available.</p>
            <dl className="recovery-metrics">
              {[["Unchanged possessions",metrics.retained_blocks],["Shifted possessions",metrics.shifted_blocks],["Cancelled groups",metrics.cancelled_blocks],
                ["New groups",metrics.new_blocks],["Unchanged task starts",metrics.retained_tasks],["Shifted tasks",metrics.shifted_tasks],
                ["Outstanding tasks",metrics.unscheduled_tasks_after_disruption],["Task displacement",`${metrics.total_shift_minutes} min`]].map(([label,value]) =>
                <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
            </dl>
            <p className="scenario-note">Groups match by section and task membership, not block ID. A cancelled group can be regrouped without losing its work. Displacement sums absolute start changes for previously scheduled tasks still scheduled.</p>
            <p>Affected sections: {recovery.affected_sections.map((id) => sectionLabel(territory,id)).join("; ")}</p>
            <p>Newly unscheduled: {recovery.newly_unscheduled_task_ids.map((id) => names.get(id) ?? id).join(", ") || "None"}</p>
            <RiskResult risk={recovery.risk} />
          </section>
          <RecoveryTimeline result={recovery} territory={territory} tasks={tasks} originalTrains={trains} />
          <section className="recovery-findings"><h2>Why repair was needed</h2>
            {recovery.invalidated_blocks.length ? <ul>{recovery.invalidated_blocks.map((b) => <li key={b.block_id}>
              <strong>{b.task_ids.map((id) => names.get(id) ?? id).join(" + ")}</strong> · {b.block_id}: fails train protection after the injected delay.
            </li>)}</ul> : <p>No original possession was invalidated by the supplied delay.</p>}
          </section>
          <OutstandingWork items={recovery.recovered_plan.unscheduled_diagnostics} territory={territory} />
        </> : null}
      </>}
      <DataAssumptions defaultOpen />
    </main>
  </div>;
}
