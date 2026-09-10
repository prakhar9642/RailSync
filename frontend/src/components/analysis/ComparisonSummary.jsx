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

export function ComparisonDetails({ analysis }) {
  const { baseline, railsync } = analysis;
  const exactComparison =
    baseline.proof_state === "FULLY_OPTIMAL" && railsync.proof_state === "FULLY_OPTIMAL";

  return (
    <details className="comparison-technical-details" aria-label="Full technical comparison">
      <summary>
        <span>View full technical comparison</span>
      </summary>
      <div className="comparison-technical-body">
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
      </div>
    </details>
  );
}

export default function ComparisonSummary({ analysis }) {
  const { fairness, baseline, railsync } = analysis;
  const showSavings =
    fairness.same_task_set &&
    fairness.possession_saved_minutes != null &&
    fairness.possession_reduction_percent != null;

  return (
    <section className="analysis-comparison" aria-labelledby="comparison-heading">
      <div className="analysis-section-heading">
        <span>Fair technical comparison</span>
        <h2 id="comparison-heading">Did coordination reduce possession time?</h2>
        <p>{fairness.statement}</p>
      </div>

      {showSavings ? (
        <div className="analysis-outcome-card">
          <div className="outcome-primary-stat">
            <div className="outcome-duration-shift"><div><small>Baseline</small><strong>{baseline.metrics.possession_minutes} <small>min</small></strong></div><span aria-hidden="true">→</span><div><small>RailSync</small><strong>{railsync.metrics.possession_minutes} <small>min</small></strong></div></div>
            <strong className="outcome-saved-stat">
              {fairness.possession_saved_minutes} possession-minutes avoided
            </strong>
            <span className="outcome-reduction-badge">
              {fairness.possession_reduction_percent.toFixed(1)}% reduction
            </span>
          </div>

          <div className="outcome-sub-stats">
            <div className="outcome-stat-chip">
              <strong>{railsync.metrics.scheduled_task_count}</strong>
              <span>tasks delivered in both plans</span>
            </div>
            <div className="outcome-stat-chip">
              <strong>{baseline.metrics.block_count} → {railsync.metrics.block_count}</strong>
              <span>possessions</span>
            </div>
            <div className="outcome-stat-chip">
              <strong>{baseline.metrics.integrated_blocks} → {railsync.metrics.integrated_blocks}</strong>
              <span>integrated possessions</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="analysis-outcome is-neutral">
          <strong>No pure possession-saving claim</strong>
          <span>Compare delivered work and service measures directly below.</span>
        </div>
      )}
    </section>
  );
}
