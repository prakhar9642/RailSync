function formatTimestamp(timestamp) {
  if (!timestamp) return "—";
  const [date, time] = timestamp.split("T");
  return `${date} ${time.slice(0, 5)}`;
}

function durationMinutes(block) {
  return Math.round((new Date(block.end_time) - new Date(block.start_time)) / 60_000);
}

function departmentLabel(department) {
  return department === "ENGINEERING" ? "Engineering" : department;
}

export default function BlockDetails({ block, tasks }) {
  const taskById = new Map(tasks.map((task) => [task.task_id, task]));
  const departments = block
    ? [...new Set(block.tasks.map((id) => taskById.get(id)?.department).filter(Boolean))]
    : [];

  return (
    <section className="block-details" aria-labelledby="block-details-heading">
      <div className="workspace-column-heading">
        <div>
          <span className="planner-kicker">Selected result</span>
          <h2 id="block-details-heading">Block Details</h2>
        </div>
      </div>

      {block ? (
        <div className="block-details-content">
          <dl className="block-details-facts">
            <div><dt>Block ID</dt><dd>{block.block_id}</dd></div>
            <div><dt>Section</dt><dd>{block.section_id}</dd></div>
            <div><dt>Start</dt><dd>{formatTimestamp(block.start_time)}</dd></div>
            <div><dt>End</dt><dd>{formatTimestamp(block.end_time)}</dd></div>
            <div><dt>Duration</dt><dd>{durationMinutes(block)} min</dd></div>
            <div><dt>Integrated</dt><dd>{block.integrated ? "Yes" : "No"}</dd></div>
          </dl>

          <div className="block-details-tasks">
            <span>Task IDs</span>
            <div>
              {block.tasks.map((taskId) => <strong key={taskId}>{taskId}</strong>)}
            </div>
          </div>

          <div className="block-details-departments">
            <span>Departments</span>
            <p>{departments.map(departmentLabel).join(" + ") || "Not available"}</p>
          </div>

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
