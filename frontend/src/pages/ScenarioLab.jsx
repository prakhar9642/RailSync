import { useEffect, useRef, useState } from "react";
import Navbar from "../components/layout/Navbar.jsx";
import Footer from "../components/layout/Footer.jsx";
import Button from "../components/ui/Button.jsx";
import DataAssumptions from "../components/analysis/DataAssumptions.jsx";
import OutstandingWork from "../components/analysis/OutstandingWork.jsx";
import RiskControls, { RiskResult } from "../components/planning/RiskControls.jsx";
import { riskOptions } from "../utils/risk.js";
import RecoveryTimeline from "../components/planning/RecoveryTimeline.jsx";
import { reoptimizePlan } from "../services/api.js";
import { proofLabel, sectionLabel, territoryLabel, trainFullLabel } from "../utils/planningLabels.js";
import "./scenario/scenario.css";
import "./analysis/analysis.css";

export default function ScenarioLab({ session, setSession, onNavigate, onHome }) {
  const { plan, territory, trains, tasks, recovery, riskConfig } = session;
  const trainIds = [...new Set(trains.map((r) => r.train_id))];
  const [trainId, setTrainId] = useState(recovery?.disruption.train_id ?? trainIds[0] ?? "");
  const [delay, setDelay] = useState(recovery?.disruption.delay_minutes ?? 25);
  const [scenarioType, setScenarioType] = useState(recovery?.disruption.type ?? "TRAIN_DELAY");
  const [sectionId, setSectionId] = useState(territory?.sections?.[0]?.section_id ?? "");
  const [crewType, setCrewType] = useState(Object.keys(territory?.resources?.crew?.reduce((all, item) => ({ ...all, [item.resource_id]: true }), {}) ?? {})[0] ?? "TRACK_CREW");
  const [machineType, setMachineType] = useState(territory?.resources?.machines?.[0]?.resource_id ?? "TOWER_WAGON");
  const [effectiveTime, setEffectiveTime] = useState(plan?.planning_context?.horizon_start?.slice(0, 16) ?? "");
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
      const effective_time = effectiveTime ? `${effectiveTime}:00` : plan.planning_context.horizon_start;
      const disruptions = {
        TRAIN_DELAY: { type: "TRAIN_DELAY", train_id: trainId, delay_minutes: Number(delay), effective_time },
        CREW_UNAVAILABLE: { type: "CREW_UNAVAILABLE", crew_type: crewType, effective_time },
        MACHINE_UNAVAILABLE: { type: "MACHINE_UNAVAILABLE", machine_type: machineType, effective_time },
        POWER_ISOLATION_CANCELLED: { type: "POWER_ISOLATION_CANCELLED", section_ids: [sectionId], effective_time },
        SECTION_UNAVAILABLE: { type: "SECTION_UNAVAILABLE", section_id: sectionId, start_time: effective_time, end_time: plan.planning_context.horizon_end, effective_time },
        WEATHER_RESTRICTION: { type: "WEATHER_RESTRICTION", delay_minutes: Number(delay), train_ids: [], effective_time },
        EMERGENCY_WORK: { type: "EMERGENCY_WORK", effective_time, task: { task_id: `EMERGENCY_${sectionId}`, department: "ENGINEERING", section_id: sectionId, task_type: "Emergency track inspection", duration_minutes: 20, criticality: 10, urgency: 10, overdue_days: 0, deadline: plan.planning_context.horizon_end, requires_power_block: false, crew_type: "TRACK_CREW", compatibility_group: `EMERGENCY_${sectionId}` } },
      };
      const result = await reoptimizePlan(plan, disruptions[scenarioType],
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
      <header className="scenario-hero"><span>Scenario Lab</span>
        <h1>What happens when reality changes?</h1>
        <p>Apply a time-aware operational disruption. RailSync freezes elapsed or explicitly frozen work, then repairs only the remaining plan while preserving feasible decisions.</p>
      </header>
      <div className="scenario-flow"><strong>Current plan</strong><span aria-hidden="true">→</span><strong>Disruption</strong><span aria-hidden="true">→</span><strong>Recovered plan</strong></div>
      {!plan ? <section className="analysis-empty">
        <h2>Generate a plan in Planning before running a scenario.</h2>
        <p>No base plan is available in this session.</p>
        <Button onClick={() => onNavigate("planning")}>Open Planning</Button>
      </section> : <>
        <form className="scenario-form" onSubmit={runScenario}>
          <div><span>Current base plan</span><strong>{plan.blocks.length} possessions · {proofLabel(plan.proof_state)}</strong><small>{territoryLabel(territory)}</small></div>
          <label>Disruption<select aria-label="Disruption type" value={scenarioType} disabled={busy} onChange={(event) => setScenarioType(event.target.value)}>
            <option value="TRAIN_DELAY">Train delay</option><option value="CREW_UNAVAILABLE">Crew unavailable</option><option value="MACHINE_UNAVAILABLE">Machine unavailable</option><option value="POWER_ISOLATION_CANCELLED">Power isolation cancelled</option><option value="SECTION_UNAVAILABLE">Section unavailable</option><option value="WEATHER_RESTRICTION">Weather restriction</option><option value="EMERGENCY_WORK">Emergency work</option>
          </select></label>
          {scenarioType === "TRAIN_DELAY" ? <label>Train<select aria-label="Scenario train" value={trainId} disabled={busy} onChange={(event) => setTrainId(event.target.value)}>
            {trainIds.map((id) => <option key={id} value={id}>{trainFullLabel(id, territory)}</option>)}
          </select></label> : null}
          {["TRAIN_DELAY", "WEATHER_RESTRICTION"].includes(scenarioType) ? <label>Delay (minutes)<input aria-label="Delay minutes" type="number" min="0" max="1440" step="1" required value={delay} disabled={busy} onChange={(event) => setDelay(event.target.value)} /></label> : null}
          {["POWER_ISOLATION_CANCELLED", "SECTION_UNAVAILABLE", "EMERGENCY_WORK"].includes(scenarioType) ? <label>Section<select value={sectionId} onChange={(event) => setSectionId(event.target.value)}>{territory.sections.map((section) => <option value={section.section_id} key={section.section_id}>{sectionLabel(territory, section.section_id)}</option>)}</select></label> : null}
          {scenarioType === "CREW_UNAVAILABLE" ? <label>Crew pool<select value={crewType} onChange={(event) => setCrewType(event.target.value)}>{(territory.resources?.crew ?? []).map((item) => <option key={item.resource_id}>{item.resource_id}</option>)}</select></label> : null}
          {scenarioType === "MACHINE_UNAVAILABLE" ? <label>Machine pool<select value={machineType} onChange={(event) => setMachineType(event.target.value)}>{(territory.resources?.machines ?? []).map((item) => <option key={item.resource_id}>{item.resource_id}</option>)}</select></label> : null}
          <label>Effective time<input type="datetime-local" value={effectiveTime} onChange={(event) => setEffectiveTime(event.target.value)} /></label>
          <Button type="submit" disabled={busy || (scenarioType === "TRAIN_DELAY" && !trainId)} ariaBusy={busy}>{busy ? "Recovering plan…" : "Run Scenario"}</Button>
        </form>
        <p className="scenario-note">Simulation only — recovered changes are not automatically applied. Each run starts from the base plan.</p>
        <RiskControls config={riskConfig} onChange={(config) => setSession((current) => ({ ...current, riskConfig: config }))}
          trains={trains} territory={territory} disabled={busy} />
        {busy ? <p role="status">Recomputing protected train windows and solving minimum-change recovery…</p> : null}
        {error ? <div className="scenario-error" role="alert"><strong>Scenario failed</strong><p>{error.message}</p></div> : null}
        {recovery ? <>
          <section className="recovery-summary" aria-labelledby="recovery-heading">
            <div className="scenario-flow" aria-label="Scenario recovery sequence">
              <span>CURRENT PLAN</span>
              <span aria-hidden="true">→</span>
              <span>DISRUPTION</span>
              <span aria-hidden="true">→</span>
              <strong>RECOVERED PLAN</strong>
            </div>
            <div className="scenario-section-heading">
              <div><span>CP-SAT minimum-change recovery</span><h2 id="recovery-heading">Recovery result</h2></div>
              <strong>{proofLabel(recovery.recovered_plan.proof_state)}</strong>
            </div>
            {recovery.recovered_plan.proof_state !== "FULLY_OPTIMAL" ? <p className="recovery-proof-note">Valid bounded recovery; minimum change is not fully proven.</p> : null}
            <p className="recovery-disruption-subhead">
              <strong>{recovery.disruption.type.toLowerCase().replaceAll("_", " ")}</strong> at <strong>{recovery.disruption.effective_time ?? plan.planning_context.horizon_start}</strong>. Original base plan remains preserved; {recovery.immutable_task_ids.length} task(s) were immutable.
            </p>
            <div className="recovery-outcome-cards">
              <div className="recovery-card card-retained">
                <span className="recovery-card-label">UNCHANGED</span>
                <strong>{metrics.retained_blocks}</strong>
                <small>possessions kept</small>
              </div>
              <div className="recovery-card card-shifted">
                <span className="recovery-card-label">SHIFTED</span>
                <strong>{metrics.shifted_blocks}</strong>
                <small>retimed windows</small>
              </div>
              <div className="recovery-card card-cancelled">
                <span className="recovery-card-label">CANCELLED</span>
                <strong>{metrics.cancelled_blocks}</strong>
                <small>groups broken</small>
              </div>
              <div className="recovery-card card-new">
                <span className="recovery-card-label">NEW</span>
                <strong>{metrics.new_blocks}</strong>
                <small>rescheduled</small>
              </div>
            </div>
          </section>
          <RecoveryTimeline result={recovery} territory={territory} tasks={tasks} originalTrains={trains} />
          <div className="scenario-apply-row"><Button onClick={() => setSession((current) => ({ ...current, plan: { ...plan, blocks: recovery.recovered_plan.blocks, unscheduled_tasks: recovery.recovered_plan.unscheduled_tasks, proof_state: recovery.recovered_plan.proof_state }, recovery: null }))}>Apply recovered plan explicitly</Button>{recovery.escalation_required ? <strong>Escalation required: an immutable block was invalidated.</strong> : null}</div>
          <details className="recovery-technical-details">
            <summary>View recovery technical details</summary>
            <div className="recovery-technical-body">
              <section className="recovery-findings">
                <h3>Why repair was needed</h3>
                {recovery.invalidated_blocks.length ? <ul>{recovery.invalidated_blocks.map((b) => <li key={b.block_id}>
                  <strong>{b.task_ids.map((id) => names.get(id) ?? id).join(" + ")}</strong> ({b.block_id}): {b.reason_code.replaceAll("_", " ").toLowerCase()}.
                </li>)}</ul> : <p>No original possession was invalidated by the supplied delay.</p>}
              </section>
              <dl className="recovery-metrics">
                {[["Unchanged possessions",metrics.retained_blocks],["Shifted possessions",metrics.shifted_blocks],["Cancelled groups",metrics.cancelled_blocks],
                  ["New groups",metrics.new_blocks],["Unchanged task starts",metrics.retained_tasks],["Shifted tasks",metrics.shifted_tasks],
                  ["Outstanding tasks",metrics.unscheduled_tasks_after_disruption],["Total task displacement",`${metrics.total_shift_minutes} min`]].map(([label,value]) =>
                  <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
              </dl>
              <p className="scenario-note">Groups match by section and task membership, not block ID. A cancelled group can be regrouped without losing its work. Displacement sums absolute start changes for previously scheduled tasks still scheduled.</p>
              <p className="recovery-affected-text"><strong>Affected sections:</strong> {recovery.affected_sections.map((id) => sectionLabel(territory,id)).join("; ") || "None"}</p>
              <p className="recovery-unscheduled-text"><strong>Newly unscheduled:</strong> {recovery.newly_unscheduled_task_ids.map((id) => names.get(id) ?? id).join(", ") || "None"}</p>
              <RiskResult risk={recovery.risk} />
              <OutstandingWork items={recovery.recovered_plan.unscheduled_diagnostics} territory={territory} />
            </div>
          </details>
        </> : null}
      </>}
      <DataAssumptions territory={session.territory} />
    </main>
    <Footer />
  </div>;
}
