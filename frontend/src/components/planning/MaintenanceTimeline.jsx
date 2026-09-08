import { trainLabel } from "../../utils/planningLabels.js";
import { buildTicks, dateLabel, rangeStyle, timeLabel } from "../../utils/timeline.js";

function TimelineGrid({ ticks }) {
  return (
    <span className="timeline-hour-lines" aria-hidden="true">
      {ticks.map((tick) => <i key={tick.key} style={{ left: tick.left }} />)}
    </span>
  );
}

export default function MaintenanceTimeline({
  sectionId,
  occupancy,
  blocks,
  horizon,
  hasPlan,
  selectedBlockId,
  onSelectBlock,
  territory,
}) {
  const ticks = buildTicks(horizon);
  if (!horizon) return null;

  return (
    <section className="planner-timeline-column" aria-labelledby="timeline-heading">
      <div className="workspace-column-heading timeline-heading">
        <div>
          <span className="planner-kicker">
            {dateLabel(horizon.start_time)} · {timeLabel(horizon.start_time)}–{timeLabel(horizon.end_time)}
          </span>
          <h2 id="timeline-heading">Train Occupancy + Maintenance Timeline</h2>
        </div>
        <span className="timeline-section-chip">{sectionId}</span>
      </div>

      <div className="timeline-legend" aria-label="Timeline legend">
        <span><i className="train" />Train occupancy</span>
        <span><i className="valid" />Optimized possession</span>
      </div>

      <div className="planner-timeline-chart">
        <div className="timeline-axis-row" aria-hidden="true">
          <span />
          <div className="planner-timeline-axis">
            {ticks.map((tick) => <time key={tick.key}>{tick.label}</time>)}
          </div>
        </div>

        <div className="timeline-lanes">
          {occupancy.map((train) => (
            <div
              className="planner-timeline-row"
              key={`${train.train_id}-${train.entry_time}`}
            >
              <span className="timeline-lane-label" title={train.train_id}>
                {trainLabel(train.train_id, territory)}
              </span>
              <div className="planner-timeline-track">
                <TimelineGrid ticks={ticks} />
                <span
                  className="planner-timeline-bar train"
                  style={rangeStyle(train.entry_time, train.exit_time, horizon)}
                  title={`${train.train_id}: ${timeLabel(train.entry_time)}–${timeLabel(train.exit_time)}`}
                >
                  {trainLabel(train.train_id, territory)}
                </span>
              </div>
            </div>
          ))}
          {occupancy.length === 0 ? (
            <p className="timeline-empty">No protected train occupancy on this section.</p>
          ) : null}

          <div className="planner-timeline-row maintenance-row">
            <span className="timeline-lane-label">Possessions</span>
            <div className="planner-timeline-track">
              <TimelineGrid ticks={ticks} />
              {blocks.map((block) => (
                <button
                  key={block.block_id}
                  type="button"
                  className={`planner-timeline-bar maintenance valid ${
                    selectedBlockId === block.block_id ? "is-selected" : ""
                  }`}
                  style={rangeStyle(block.start_time, block.end_time, horizon)}
                  title={`${block.block_id}: ${timeLabel(block.start_time)}–${timeLabel(block.end_time)}`}
                  onClick={() => onSelectBlock(block.block_id)}
                >
                  {block.integrated ? `Shared ${block.block_id}` : block.block_id}
                </button>
              ))}
              {blocks.length === 0 ? (
                <span className="timeline-maintenance-empty">
                  {hasPlan ? "No possession scheduled on this section" : "Run optimizer to generate possessions"}
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <div className="timeline-reading-order">
        Possession bars use the complete setup, productive work, and release interval returned by FastAPI.
      </div>
    </section>
  );
}
