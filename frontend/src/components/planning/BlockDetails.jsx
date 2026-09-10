import {
  departmentLabel,
  resourceStateLabel,
  sectionLabel,
} from "../../utils/planningLabels.js";
import { durationMinutes, timeLabel } from "../../utils/timeline.js";

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

  if (!block) return null;

  const blockTasks = block.tasks.map((taskId) => taskById.get(taskId)).filter(Boolean);
  const departments = [...new Set(blockTasks.map((t) => departmentLabel(t.department)))];
  const deptSummary = departments.length > 0 ? departments.join(" + ") : "Maintenance";
  const totalDuration = durationMinutes(block.start_time, block.end_time);
  const protectedSections = block.section_ids?.length ? block.section_ids : [block.section_id];

  // High-level feasibility checks from diagnostic
  const sectionPassed = diagnostic?.feasibility?.section_match === "PASSED";
  const durationPassed = diagnostic?.feasibility?.duration_fit === "PASSED";
  const trainPassed = diagnostic?.feasibility?.train_conflict === "PASSED";
  const resourcesUnknown = diagnostic?.tasks?.some((task) => Object.values(task.resource_checks ?? {}).includes("UNKNOWN"));
  const resourcesPassed = diagnostic?.tasks?.length > 0 && diagnostic.tasks.every((t) =>
    Object.values(t.resource_checks ?? {}).every((s) => s !== "FAILED" && s !== "UNKNOWN")
  );
  const deadlinePassed = diagnostic?.tasks?.every((t) => t.deadline_check === "PASSED") ?? true;

  const minSlack = diagnostic?.robustness?.minimum_boundary_slack_minutes;

  return (
    <section className="block-details" aria-labelledby="block-details-heading">
      <div className="workspace-column-heading">
        <div>
          <span className="planner-kicker">Selected possession</span>
          <h2 id="block-details-heading">Why this possession?</h2>
        </div>
      </div>

      <div className="block-details-content">
        {/* Header & Location */}
        <div className="block-details-location">
          <strong>{protectedSections.map((id) => sectionLabel(territory, id)).join(" · ")}</strong>
          <span>
            {timeLabel(block.start_time)}–{timeLabel(block.end_time)} · Total possession: {totalDuration} min
          </span>
          <span>Capacity: {(block.capacity_resource_ids?.length ? block.capacity_resource_ids : protectedSections).join(" + ")}{block.track_ids?.length ? ` · Track ${block.track_ids.join(" + ")}` : " · Conservative whole-section protection"}</span>
        </div>

        {/* Department & Sharing badge */}
        <div className="block-details-dept-pill">
          <strong>{deptSummary}</strong>
          <small>{block.integrated ? "Integrated possession" : "Individual possession"}</small>
        </div>

        {/* Operational phase structure (SET | WORK | REL) */}
        <div className="block-phase-breakdown" aria-label="Possession phase structure">
          <div className="phase-chip set" title="Setup">
            <span>SET</span>
            <small>Setup</small>
          </div>
          <div className="phase-chip work" title="Maintenance activity">
            <span>WORK</span>
            <small>Maintenance activity</small>
          </div>
          <div className="phase-chip rel" title="Release">
            <span>REL</span>
            <small>Release</small>
          </div>
        </div>

        {/* Tasks inside this block */}
        <div className="block-details-tasks">
          <span>Maintenance tasks</span>
          <div className="block-task-list">
            {block.tasks.map((taskId) => {
              const task = taskById.get(taskId);
              return (
                <article key={taskId}>
                  <strong>{task?.task_type ?? taskId}</strong>
                  <small>{task ? `${departmentLabel(task.department)} · ${task.duration_minutes} min` : taskId}</small>
                </article>
              );
            })}
          </div>
        </div>

        {/* High-level Feasibility Checklist */}
        {diagnostic ? (
          <div className="block-feasibility-summary">
            <span>High-level feasibility</span>
            <ul className="block-feasibility-list">
              <li className={sectionPassed ? "is-passed" : "is-failed"}>
                <span className="check-icon">{sectionPassed ? "✓" : "✗"}</span>
                <span>Correct section</span>
              </li>
              <li className={durationPassed ? "is-passed" : "is-failed"}>
                <span className="check-icon">{durationPassed ? "✓" : "✗"}</span>
                <span>Duration fits</span>
              </li>
              <li className={trainPassed ? "is-passed" : "is-failed"}>
                <span className="check-icon">{trainPassed ? "✓" : "✗"}</span>
                <span>No protected train conflict</span>
              </li>
              <li className={resourcesPassed ? "is-passed" : "is-failed"}>
                <span className="check-icon">{resourcesUnknown ? "?" : resourcesPassed ? "✓" : "✗"}</span>
                <span>{resourcesUnknown ? "Resource availability unconfirmed" : resourcesPassed ? "Required resource checks clear" : "Resource constraint failed"}</span>
              </li>
              <li className={deadlinePassed ? "is-passed" : "is-failed"}>
                <span className="check-icon">{deadlinePassed ? "✓" : "✗"}</span>
                <span>Deadline satisfied</span>
              </li>
            </ul>
          </div>
        ) : null}

        {/* Minimum boundary slack */}
        <div className="block-slack-summary">
          <span className="slack-label">Minimum boundary slack</span>
          <strong className="slack-value">{minSlack != null ? `${minSlack} min` : "Unavailable"}</strong>
        </div>

        {/* PROGRESSIVE DISCLOSURE: Technical explanation */}
        <details className="block-technical-details">
          <summary>
            <span>View technical explanation</span>
          </summary>
          <div className="block-technical-body">
            <dl className="block-details-facts">
              <div><dt>Canonical block</dt><dd>{block.block_id}</dd></div>
              <div><dt>Canonical section</dt><dd>{block.section_id}</dd></div>
              <div><dt>Physical footprint</dt><dd>{protectedSections.join(" + ")}</dd></div>
              <div><dt>Capacity resources</dt><dd>{(block.capacity_resource_ids?.length ? block.capacity_resource_ids : protectedSections).join(" + ")}</dd></div>
              <div><dt>Track allocation</dt><dd>{block.track_ids?.length ? block.track_ids.join(" + ") : "Conservative / not separately identified"}</dd></div>
              <div><dt>Power isolation zone</dt><dd>{block.power_isolation_zone_id ?? "Not required"}</dd></div>
              <div><dt>Possession start</dt><dd>{formatTimestamp(block.start_time)}</dd></div>
              <div><dt>Possession end</dt><dd>{formatTimestamp(block.end_time)}</dd></div>
              <div><dt>Total possession</dt><dd>{totalDuration} min</dd></div>
              <div><dt>Window ID</dt><dd>{diagnostic?.window_id ?? "Direct"}</dd></div>
            </dl>

            {diagnostic ? (
              <>
                <div className="block-details-checks">
                  <span>Full feasibility checks</span>
                  <dl>
                    <div><dt>Section match</dt><dd>{checkLabel(diagnostic.feasibility.section_match)}</dd></div>
                    <div><dt>Duration fit</dt><dd>{checkLabel(diagnostic.feasibility.duration_fit)}</dd></div>
                    <div><dt>Train conflict</dt><dd>{checkLabel(diagnostic.feasibility.train_conflict)}</dd></div>
                    <div><dt>Candidate window</dt><dd>{checkLabel(diagnostic.feasibility.candidate_window)}</dd></div>
                    <div><dt>Compatibility</dt><dd>{checkLabel(diagnostic.integration.compatibility_status)}</dd></div>
                  </dl>
                </div>

                <div className="block-details-checks">
                  <span>Task resources and deadline</span>
                  {diagnostic.tasks.map((task) => (
                    <article className="block-task-diagnostic" key={task.task_id}>
                      <strong>{task.task_type} <small>({task.task_id})</small></strong>
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
                      <div><dt>Before slack</dt><dd>{diagnostic.robustness.before_boundary_slack_minutes} min</dd></div>
                      <div><dt>After slack</dt><dd>{diagnostic.robustness.after_boundary_slack_minutes} min</dd></div>
                      <div><dt>Minimum slack</dt><dd>{diagnostic.robustness.minimum_boundary_slack_minutes} min</dd></div>
                    </dl>
                  ) : <p>Unavailable</p>}
                </div>
              </>
            ) : null}

            {block.explanation?.length > 0 ? (
              <div className="block-details-why">
                <span>Optimizer diagnostics</span>
                <ul>
                  {block.explanation.map((reason) => (
                    <li key={reason}><span aria-hidden="true">✓</span>{reason}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </details>
      </div>
    </section>
  );
}
