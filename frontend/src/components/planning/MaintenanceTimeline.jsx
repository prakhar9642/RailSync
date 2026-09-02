const HORIZON_MINUTES = 6 * 60;
const HOURS = ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00", "06:00"];

function minutesFromMidnight(timestamp) {
  const time = timestamp.split("T")[1];
  const [hours, minutes] = time.split(":").map(Number);
  return hours * 60 + minutes;
}

function rangeStyle(startTime, endTime) {
  const start = minutesFromMidnight(startTime);
  const end = minutesFromMidnight(endTime);
  return {
    left: `${(start / HORIZON_MINUTES) * 100}%`,
    width: `${((end - start) / HORIZON_MINUTES) * 100}%`,
  };
}

function TimelineGrid() {
  return (
    <span className="timeline-hour-lines" aria-hidden="true">
      {HOURS.map((hour, index) => (
        <i key={hour} style={{ left: `${(index / (HOURS.length - 1)) * 100}%` }} />
      ))}
    </span>
  );
}

export default function MaintenanceTimeline({
  sectionId,
  occupancy,
  selectedTask,
  previewBlock,
  optimizationStage,
}) {
  const showProposed = optimizationStage === "proposed";
  const showValid = optimizationStage === "generated";
  const showBlock = showProposed || showValid;

  return (
    <section className="planner-timeline-column" aria-labelledby="timeline-heading">
      <div className="workspace-column-heading timeline-heading">
        <div>
          <span className="planner-kicker">Six-hour horizon</span>
          <h2 id="timeline-heading">Train Occupancy + Maintenance Timeline</h2>
        </div>
        <span className="timeline-section-chip">{sectionId}</span>
      </div>

      <div className="timeline-legend" aria-label="Timeline legend">
        <span><i className="train" />Train occupancy</span>
        <span><i className="proposed" />Proposed maintenance</span>
        <span><i className="valid" />Valid maintenance</span>
        <span><i className="conflict" />Conflict only</span>
      </div>

      <div className="planner-timeline-chart">
        <div className="timeline-axis-row" aria-hidden="true">
          <span />
          <div className="planner-timeline-axis">
            {HOURS.map((hour) => (
              <time key={hour}>{hour}</time>
            ))}
          </div>
        </div>

        <div className="timeline-lanes">
          {occupancy.map((train) => (
            <div className="planner-timeline-row" key={train.train_id}>
              <span className="timeline-lane-label">{train.train_id}</span>
              <div className="planner-timeline-track">
                <TimelineGrid />
                <span
                  className="planner-timeline-bar train"
                  style={rangeStyle(train.entry_time, train.exit_time)}
                  title={`${train.train_id} occupies ${sectionId}`}
                >
                  {train.train_id}
                </span>
              </div>
            </div>
          ))}

          <div className="planner-timeline-row maintenance-row">
            <span className="timeline-lane-label">
              {selectedTask?.task_id ?? "Maintenance"}
            </span>
            <div className="planner-timeline-track">
              <TimelineGrid />
              {!showBlock ? (
                <span
                  className="timeline-free-window"
                  style={rangeStyle(previewBlock.start_time, previewBlock.end_time)}
                >
                  Free gap
                </span>
              ) : null}
              {showBlock ? (
                <span
                  className={`planner-timeline-bar maintenance ${
                    showValid ? "valid" : "proposed"
                  }`}
                  style={rangeStyle(previewBlock.start_time, previewBlock.end_time)}
                >
                  {showValid ? "Valid block" : "Proposed block"}
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <div className="timeline-reading-order" aria-label="How to read the timeline">
        <span>Train occupies section</span>
        <b aria-hidden="true">→</b>
        <span>Free gap exists</span>
        <b aria-hidden="true">→</b>
        <span>Maintenance fits the gap</span>
      </div>
    </section>
  );
}
