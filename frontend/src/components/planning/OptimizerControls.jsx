import Button from "../ui/Button.jsx";

const STATUS = {
  idle: "Ready",
  evaluating: "Evaluating train occupancy...",
  finding: "Finding valid maintenance window...",
  proposed: "Proposed block found...",
  generated: "Plan generated",
};

export default function OptimizerControls({ optimizationStage, onOptimize }) {
  const busy = ["evaluating", "finding", "proposed"].includes(optimizationStage);

  return (
    <section className="optimizer-controls" aria-labelledby="optimizer-heading">
      <div className="workspace-column-heading">
        <div>
          <span className="planner-kicker">Plan action</span>
          <h2 id="optimizer-heading">Optimizer Controls</h2>
        </div>
      </div>

      <label className="planner-field">
        <span>Planning Horizon</span>
        <select defaultValue="6">
          <option value="6">6 hours</option>
        </select>
      </label>

      <label className="planner-field">
        <span>Planning Profile</span>
        <select defaultValue="availability">
          <option value="availability">Availability First</option>
        </select>
      </label>

      <Button
        className="planner-optimize-button"
        onClick={onOptimize}
        disabled={busy}
        ariaBusy={busy}
      >
        {busy ? "Optimizing..." : "Optimize Plan"}
      </Button>

      <div
        className={`optimizer-status status-${optimizationStage}`}
        role="status"
        aria-live="polite"
      >
        <span className="optimizer-status-dot" aria-hidden="true" />
        <div>
          <small>Status</small>
          <strong>{STATUS[optimizationStage]}</strong>
        </div>
      </div>

      <p className="optimizer-local-note">
        Frontend planning preview. No solver request is sent in this phase.
      </p>
    </section>
  );
}
