function formatTime(timestamp) {
  return timestamp.split("T")[1].slice(0, 5);
}

export default function BlockDetails({ block }) {
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
          <div className="block-details-time">
            <strong>{block.section_id}</strong>
            <span>
              {formatTime(block.start_time)} – {formatTime(block.end_time)}
            </span>
          </div>

          <div className="block-details-tasks">
            <span>Tasks</span>
            <div>
              {block.tasks.map((taskId) => (
                <strong key={taskId}>{taskId}</strong>
              ))}
            </div>
          </div>

          <div className="block-details-why">
            <span>Why this block?</span>
            <ul>
              {block.explanation.map((reason) => (
                <li key={reason}>
                  <span aria-hidden="true">✓</span>
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <p className="block-details-empty">
          Run the planning preview to reveal a valid maintenance block.
        </p>
      )}
    </section>
  );
}
