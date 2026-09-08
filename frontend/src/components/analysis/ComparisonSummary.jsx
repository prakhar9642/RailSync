import { proofLabel } from "../../utils/planningLabels.js";

const metricRows = [
  ["Maintenance delivered", "scheduled_task_count", (value) => `${value} tasks`],
  ["Outstanding work", "unscheduled_task_count", (value) => `${value} tasks`],
  ["Productive maintenance", "productive_minutes", (value) => `${value} min`],
  ["Infrastructure possession", "possession_minutes", (value) => `${value} min`],
  ["Possessions", "block_count", String],
  ["Integrated possessions", "integrated_blocks", String],
  ["Criticality served", "criticality_served", String],
  ["Urgency served", "urgency_served", String],
  ["Overdue days served", "overdue_days_served", String],
  ["Delivery efficiency", "maintenance_delivery_efficiency", (value) => value == null ? "Unavailable" : `${value.toFixed(2)}×`],
  ["Minimum boundary slack", "minimum_boundary_slack_minutes", (value) => `${value} min`],
  ["Total boundary slack", "total_boundary_slack_minutes", (value) => `${value} min`],
];

export default function ComparisonSummary({ analysis }) {
  const { fairness, baseline, railsync } = analysis;
  const showSavings =
    fairness.same_task_set &&
    fairness.possession_saved_minutes != null &&
    fairness.possession_reduction_percent != null;
  const exactComparison =
    baseline.proof_state === "FULLY_OPTIMAL" && railsync.proof_state === "FULLY_OPTIMAL";

  return (
    <section className="analysis-comparison" aria-labelledby="comparison-heading">
      <div className="analysis-section-heading">
        <span>Fair technical comparison</span>
        <h2 id="comparison-heading">Did coordination reduce possession time?</h2>
        <p>{fairness.statement}</p>
      </div>

      {showSavings ? (
        <div className="analysis-outcome">
          <strong>{fairness.possession_saved_minutes} possession-minutes avoided</strong>
          <span>{fairness.possession_reduction_percent.toFixed(1)}% reduction for the same delivered work</span>
        </div>
      ) : (
        <div className="analysis-outcome is-neutral">
          <strong>No pure possession-saving claim</strong>
          <span>Compare delivered work and service measures directly below.</span>
        </div>
      )}

      {!exactComparison ? (
        <p className="analysis-proof-caveat">
          At least one plan is bounded feasible, so this is not presented as an exact globally optimal comparison.
        </p>
      ) : null}

      <div className="comparison-table" role="table" aria-label="Baseline and RailSync metrics">
        <div className="comparison-table-row is-header" role="row">
          <span role="columnheader">Measure</span>
          <strong role="columnheader">Non-integrated CP-SAT</strong>
          <strong role="columnheader">RailSync</strong>
        </div>
        {metricRows.map(([label, key, formatter]) => (
          <div className="comparison-table-row" role="row" key={key}>
            <span role="cell">{label}</span>
            <strong role="cell">{formatter(baseline.metrics[key])}</strong>
            <strong role="cell">{formatter(railsync.metrics[key])}</strong>
          </div>
        ))}
        <div className="comparison-table-row" role="row">
          <span role="cell">Proof state</span>
          <strong role="cell">{proofLabel(baseline.proof_state)}</strong>
          <strong role="cell">{proofLabel(railsync.proof_state)}</strong>
        </div>
      </div>
      <p className="comparison-definition">
        Delivery efficiency is productive maintenance minutes divided by possession minutes. It is an accounting ratio, not an AI score.
      </p>
    </section>
  );
}
