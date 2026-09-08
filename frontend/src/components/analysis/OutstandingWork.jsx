import {
  departmentLabel,
  priorityLabel,
  resourceStateLabel,
  sectionLabel,
} from "../../utils/planningLabels.js";

const reasonLabels = {
  WRONG_SECTION: "No candidate window on the required section",
  INSUFFICIENT_USABLE_DURATION: "Usable candidate window is too short",
  DEADLINE_VIOLATION: "Candidate placement would miss the task deadline",
  POWER_BLOCK_UNAVAILABLE: "Required power block failed its availability check",
  CREW_UNAVAILABLE: "Required crew failed its availability check",
  MACHINE_UNAVAILABLE: "Required machine failed its availability check",
  POWER_WINDOW_UNAVAILABLE: "Power window unavailable for a valid reservation",
};

function resourceStates(candidateWindows, resource) {
  const states = [...new Set(
    candidateWindows
      .map((window) => window.resource_checks?.[resource])
      .filter(Boolean),
  )];
  return states.length > 0 ? states.map(resourceStateLabel).join(" / ") : "Unavailable";
}

export default function OutstandingWork({ items, territory }) {
  return (
    <section className="outstanding-analysis" aria-labelledby="outstanding-heading">
      <div className="analysis-section-heading">
        <span>Outstanding maintenance</span>
        <h2 id="outstanding-heading">Work not placed under supplied constraints</h2>
      </div>
      {items.length === 0 ? (
        <p className="analysis-empty-line">No outstanding maintenance in this plan.</p>
      ) : (
        <div className="outstanding-list">
          {items.map((item) => (
            <article key={item.task.task_id}>
              <div>
                <h3>{item.task.task_type}</h3>
                <p>{departmentLabel(item.task.department)} · {item.task.task_id}</p>
              </div>
              <dl>
                <div><dt>Section</dt><dd>{sectionLabel(territory, item.task.section_id)} <small>{item.task.section_id}</small></dd></div>
                <div><dt>Priority</dt><dd>{priorityLabel(item.task)}</dd></div>
                <div><dt>Crew check</dt><dd>{resourceStates(item.candidate_windows, "crew")}</dd></div>
                <div><dt>Machine check</dt><dd>{resourceStates(item.candidate_windows, "machine")}</dd></div>
                <div><dt>Power check</dt><dd>{resourceStates(item.candidate_windows, "power")}</dd></div>
              </dl>
              <div className="outstanding-reasons">
                <strong>Factual candidate-window findings</strong>
                {item.reason_codes.length > 0 ? (
                  <ul>
                    {item.reason_codes.map((reason) => (
                      <li key={reason}>{reasonLabels[reason] ?? reason.replaceAll("_", " ").toLowerCase()}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No executable placement found under supplied constraints.</p>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
