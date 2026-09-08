import {
  departmentLabel,
  resourceStateLabel,
  sectionLabel,
} from "../../utils/planningLabels.js";
import { durationMinutes } from "../../utils/timeline.js";

function formatTimestamp(timestamp) {
  if (!timestamp) return "—";
  const [date, time] = timestamp.split("T");
  return `${date} ${time.slice(0, 5)}`;
}

function checkLabel(value) {
  if (value === "CONDITIONAL") return "Conditionally compatible";
  if (value === "INCOMPATIBLE") return "Incompatible";
  if (value === "NOT_EVALUATED") return "Not evaluated";
  return resourceStateLabel(value);
}

function resourceSummary(task, resource) {
  const state = task.resource_checks?.[resource];
  const requirement = resource === "crew"
    ? task.crew_type
    : resource === "machine"
      ? task.machine_type
      : task.requires_power_block ? "Power isolation" : null;
  return `${requirement ?? "Not required"}: ${checkLabel(state ?? "NOT_EVALUATED")}`;
}

export default function BlockDetails({ block, diagnostic, tasks, territory }) {
  const taskById = new Map(tasks.map((task) => [task.task_id, task]));

  return (
    <section className="block-details" aria-labelledby="block-details-heading">
      <div className="workspace-column-heading">
        <div>
          <span className="planner-kicker">Selected result</span>
          <h2 id="block-details-heading">Block explanation</h2>
        </div>
      </div>

      {block ? (
        <div className="block-details-content">
          <div className="block-details-location">
            <strong>{sectionLabel(territory, block.section_id)}</strong>
            <span>{block.section_id} · {block.block_id}</span>
          </div>

          <dl className="block-details-facts">
            <div><dt>Possession start</dt><dd>{formatTimestamp(block.start_time)}</dd></div>
            <div><dt>Possession end</dt><dd>{formatTimestamp(block.end_time)}</dd></div>
            <div><dt>Reserved duration</dt><dd>{durationMinutes(block.start_time, block.end_time)} min</dd></div>
            <div><dt>Sharing</dt><dd>{block.integrated ? "Integrated possession" : "Individual possession"}</dd></div>
          </dl>

          <div className="block-details-tasks">
            <span>Maintenance inside this possession</span>
            <div className="block-task-list">
              {block.tasks.map((taskId) => {
                const task = taskById.get(taskId);
                return (
                  <article key={taskId}>
                    <strong>{task?.task_type ?? taskId}</strong>
                    <small>{task ? `${departmentLabel(task.department)} · ${taskId}` : taskId}</small>
                  </article>
                );
              })}
            </div>
          </div>

          {diagnostic ? (
            <>
              <div className="block-details-checks">
                <span>Feasibility checks</span>
                <dl>
                  <div><dt>Correct section</dt><dd>{checkLabel(diagnostic.feasibility.section_match)}</dd></div>
                  <div><dt>Duration fits</dt><dd>{checkLabel(diagnostic.feasibility.duration_fit)}</dd></div>
                  <div><dt>Protected train occupancy</dt><dd>{checkLabel(diagnostic.feasibility.train_conflict)}</dd></div>
                  <div><dt>Candidate window</dt><dd>{checkLabel(diagnostic.feasibility.candidate_window)}</dd></div>
                  <div><dt>Compatibility</dt><dd>{checkLabel(diagnostic.integration.compatibility_status)}</dd></div>
                </dl>
              </div>

              <div className="block-details-checks">
                <span>Task resources and deadline</span>
                {diagnostic.tasks.map((task) => (
                  <article className="block-task-diagnostic" key={task.task_id}>
                    <strong>{task.task_type}</strong>
                    <dl>
                      <div><dt>Crew</dt><dd>{resourceSummary(task, "crew")}</dd></div>
                      <div><dt>Machine</dt><dd>{resourceSummary(task, "machine")}</dd></div>
                      <div><dt>Power</dt><dd>{resourceSummary(task, "power")}</dd></div>
                      <div><dt>Deadline</dt><dd>{checkLabel(task.deadline_check)}</dd></div>
                    </dl>
                  </article>
                ))}
              </div>

              <div className="block-details-checks">
                <span>Deterministic boundary slack</span>
                {diagnostic.robustness ? (
                  <dl>
                    <div><dt>Before</dt><dd>{diagnostic.robustness.before_boundary_slack_minutes} min</dd></div>
                    <div><dt>After</dt><dd>{diagnostic.robustness.after_boundary_slack_minutes} min</dd></div>
                    <div><dt>Minimum</dt><dd>{diagnostic.robustness.minimum_boundary_slack_minutes} min</dd></div>
                  </dl>
                ) : <p>Unavailable</p>}
              </div>
            </>
          ) : (
            <p className="block-diagnostic-unavailable">Detailed checks are unavailable for this result.</p>
          )}

          {block.explanation.length > 0 ? (
            <div className="block-details-why">
              <span>Optimizer output</span>
              <ul>
                {block.explanation.map((reason) => (
                  <li key={reason}><span aria-hidden="true">✓</span>{reason}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : (
        <p className="block-details-empty">
          Generate a plan and select an optimized possession to inspect it.
        </p>
      )}
    </section>
  );
}
