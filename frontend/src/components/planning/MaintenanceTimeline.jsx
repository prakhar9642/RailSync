import { useCallback, useMemo, useRef, useState } from "react";
import {
  trainLabel,
  canonicalTrainId,
  departmentLabel,
  sectionLabel,
} from "../../utils/planningLabels.js";
import {
  buildTicks,
  dateLabel,
  durationMinutes,
  rangeStyle,
  timeLabel,
} from "../../utils/timeline.js";

function TimelineGrid({ ticks }) {
  return (
    <span className="timeline-hour-lines" aria-hidden="true">
      {ticks.map((tick) => (
        <i key={tick.key} style={{ left: tick.left }} />
      ))}
    </span>
  );
}

// 2D railway train glyph (top-down / front rail silhouette)
function TrainGlyph() {
  return (
    <svg
      className="train-glyph"
      viewBox="0 0 14 14"
      width="12"
      height="12"
      aria-hidden="true"
    >
      <rect
        x="2"
        y="1"
        width="10"
        height="12"
        rx="2.5"
        fill="currentColor"
        fillOpacity="0.25"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <rect
        x="3.5"
        y="3"
        width="7"
        height="3"
        rx="1"
        fill="currentColor"
        fillOpacity="0.9"
      />
      <circle cx="4.5" cy="10" r="1.1" fill="currentColor" />
      <circle cx="9.5" cy="10" r="1.1" fill="currentColor" />
      <line
        x1="1"
        y1="13"
        x2="3"
        y2="13"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <line
        x1="11"
        y1="13"
        x2="13"
        y2="13"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
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
  tasks = [],
}) {
  const chartRef = useRef(null);
  const [selectedTrainKey, setSelectedTrainKey] = useState(null);
  const [tooltip, setTooltip] = useState(null);
  const [prevSectionId, setPrevSectionId] = useState(sectionId);

  if (prevSectionId !== sectionId) {
    setPrevSectionId(sectionId);
    setSelectedTrainKey(null);
    setTooltip(null);
  }

  const ticks = buildTicks(horizon);
  const taskById = useMemo(
    () => new Map(tasks.map((task) => [task.task_id, task])),
    [tasks],
  );

  const trainLanes = useMemo(() => {
    if (!occupancy.length) return [];
    const sorted = [...occupancy].sort(
      (a, b) => new Date(a.entry_time) - new Date(b.entry_time),
    );
    const lanes = [];
    for (const train of sorted) {
      const start = new Date(train.entry_time).getTime();
      let placed = false;
      for (const lane of lanes) {
        const last = lane[lane.length - 1];
        const lastEnd = new Date(last.exit_time).getTime();
        if (start >= lastEnd) {
          lane.push(train);
          placed = true;
          break;
        }
      }
      if (!placed) {
        lanes.push([train]);
      }
    }
    return lanes;
  }, [occupancy]);

  const selectedTrain = useMemo(() => {
    if (!selectedTrainKey) return null;
    return (
      occupancy.find(
        (t) => `${t.train_id}-${t.entry_time}` === selectedTrainKey,
      ) ?? null
    );
  }, [occupancy, selectedTrainKey]);

  const handleTrainHover = useCallback(
    (train, event) => {
      const targetRect = event.currentTarget.getBoundingClientRect();
      const parentRect = chartRef.current?.getBoundingClientRect();
      if (!parentRect) return;

      const leftPercent =
        ((targetRect.left + targetRect.width / 2 - parentRect.left) /
          parentRect.width) *
        100;
      const topPx = targetRect.top - parentRect.top;

      setTooltip({
        type: "train",
        trainId: train.train_id,
        human: trainLabel(train.train_id, territory),
        canonical: canonicalTrainId(train.train_id),
        section: sectionLabel(territory, sectionId),
        entryTime: timeLabel(train.entry_time),
        exitTime: timeLabel(train.exit_time),
        duration: durationMinutes(train.entry_time, train.exit_time),
        leftPercent,
        topPx,
      });
    },
    [territory, sectionId],
  );

  const handleBlockHover = useCallback(
    (block, deptText, event) => {
      const targetRect = event.currentTarget.getBoundingClientRect();
      const parentRect = chartRef.current?.getBoundingClientRect();
      if (!parentRect) return;

      const leftPercent =
        ((targetRect.left + targetRect.width / 2 - parentRect.left) /
          parentRect.width) *
        100;
      const topPx = targetRect.top - parentRect.top;

      const blockTaskNames = block.tasks
        .map((id) => taskById.get(id)?.task_type ?? id)
        .filter(Boolean);

      setTooltip({
        type: "block",
        blockId: block.block_id,
        section: sectionLabel(territory, block.section_id),
        startTime: timeLabel(block.start_time),
        endTime: timeLabel(block.end_time),
        duration: durationMinutes(block.start_time, block.end_time),
        deptText,
        integrated: block.integrated,
        tasks: blockTaskNames,
        leftPercent,
        topPx,
      });
    },
    [territory, taskById],
  );

  const hideTooltip = useCallback(() => {
    setTooltip(null);
  }, []);

  if (!horizon) return null;

  return (
    <section
      className="planner-timeline-column"
      aria-labelledby="timeline-heading"
    >
      <div className="workspace-column-heading timeline-heading">
        <div className="timeline-title-group">
          <div className="timeline-kicker-row">
            <span className="planner-kicker">
              {dateLabel(horizon.start_time)} · {timeLabel(horizon.start_time)}–{timeLabel(horizon.end_time)}
            </span>
            <span className="timeline-scope-badge">Selected-section view</span>
          </div>
          <h2 id="timeline-heading">Train Occupancy + Maintenance</h2>
          <div className="timeline-section-scope-display">
            <strong className="timeline-scope-name">
              {sectionLabel(territory, sectionId)}
            </strong>
            <span className="timeline-section-code">{sectionId}</span>
          </div>
        </div>
      </div>

      <div className="timeline-legend" aria-label="Timeline legend">
        <span>
          <i className="train" />
          Train occupancy
        </span>
        <span>
          <i className="valid" />
          Optimized possession (SET | WORK | REL)
        </span>
      </div>

      {selectedTrain ? (
        <div className="timeline-selected-train-banner">
          <div className="selected-train-pill">
            <TrainGlyph />
            <strong>{trainLabel(selectedTrain.train_id, territory)}</strong>
            {trainLabel(selectedTrain.train_id, territory) !== canonicalTrainId(selectedTrain.train_id) ? (
              <span className="selected-train-id">
                {canonicalTrainId(selectedTrain.train_id)}
              </span>
            ) : null}
          </div>
          <div className="selected-train-meta">
            <span className="selected-train-section">
              {sectionLabel(territory, sectionId)}
            </span>
            <span className="selected-train-times">
              Entry: {timeLabel(selectedTrain.entry_time)} · Exit:{" "}
              {timeLabel(selectedTrain.exit_time)} (
              {durationMinutes(selectedTrain.entry_time, selectedTrain.exit_time)}{" "}
              min)
            </span>
          </div>
          <button
            type="button"
            className="selected-train-close"
            onClick={() => setSelectedTrainKey(null)}
            aria-label="Dismiss train selection"
          >
            ×
          </button>
        </div>
      ) : null}

      <div className="planner-timeline-chart" ref={chartRef}>
        {tooltip ? (
          <div
            className={`timeline-floating-tooltip is-${tooltip.type} ${
              tooltip.leftPercent > 72
                ? "align-right"
                : tooltip.leftPercent < 28
                  ? "align-left"
                  : "align-center"
            }`}
            style={{
              left: `${Math.max(4, Math.min(96, tooltip.leftPercent))}%`,
              top: `${tooltip.topPx}px`,
            }}
            role="tooltip"
          >
            {tooltip.type === "train" ? (
              <div className="tooltip-train-box">
                <div className="tooltip-header-row">
                  <TrainGlyph />
                  <strong>{tooltip.human}</strong>
                  {tooltip.human !== tooltip.canonical ? <small>{tooltip.canonical}</small> : null}
                </div>
                <div className="tooltip-section-name">{tooltip.section}</div>
                <div className="tooltip-times-row">
                  <span>Entry: {tooltip.entryTime}</span>
                  <span>Exit: {tooltip.exitTime}</span>
                  <span className="tooltip-duration">
                    ({tooltip.duration} min)
                  </span>
                </div>
              </div>
            ) : (
              <div className="tooltip-block-box">
                <div className="tooltip-header-row">
                  <strong>{tooltip.deptText}</strong>
                  <small>{tooltip.blockId}</small>
                </div>
                <div className="tooltip-type-tag">
                  {tooltip.integrated
                    ? "Integrated possession"
                    : "Individual possession"}
                </div>
                <div className="tooltip-section-name">{tooltip.section}</div>
                <div className="tooltip-times-row">
                  <span>
                    {tooltip.startTime} → {tooltip.endTime}
                  </span>
                  <span className="tooltip-duration">
                    ({tooltip.duration} min)
                  </span>
                </div>
                {tooltip.tasks?.length > 0 ? (
                  <div className="tooltip-task-list">
                    {tooltip.tasks.join(" · ")}
                  </div>
                ) : null}
              </div>
            )}
          </div>
        ) : null}

        <div className="timeline-axis-row" aria-hidden="true">
          <span />
          <div className="planner-timeline-axis">
            {ticks.map((tick) => (
              <time key={tick.key}>{tick.label}</time>
            ))}
          </div>
        </div>

        <div className="timeline-lanes">
          {trainLanes.map((lane, laneIdx) => (
            <div className="planner-timeline-row" key={`train-lane-${laneIdx}`}>
              <span
                className="timeline-lane-label"
                title={lane
                  .map((t) => trainLabel(t.train_id, territory))
                  .join(", ")}
              >
                {trainLanes.length === 1 ? "Trains" : `Trains · T${laneIdx + 1}`}
              </span>
              <div className="planner-timeline-track">
                <TimelineGrid ticks={ticks} />
                {lane.map((train) => {
                  const human = trainLabel(train.train_id, territory);
                  const canonical = canonicalTrainId(train.train_id);
                  const trainKey = `${train.train_id}-${train.entry_time}`;
                  const isSelected = selectedTrainKey === trainKey;

                  return (
                    <button
                      key={trainKey}
                      type="button"
                      className={`planner-timeline-bar train ${
                        isSelected ? "is-selected" : ""
                      }`}
                      style={rangeStyle(
                        train.entry_time,
                        train.exit_time,
                        horizon,
                      )}
                      onClick={() =>
                        setSelectedTrainKey((curr) =>
                          curr === trainKey ? null : trainKey,
                        )
                      }
                      onMouseEnter={(e) => handleTrainHover(train, e)}
                      onMouseLeave={hideTooltip}
                      aria-label={`${human}${human !== canonical ? ` (${canonical})` : ""}: ${timeLabel(
                        train.entry_time,
                      )} to ${timeLabel(train.exit_time)}`}
                    >
                      <TrainGlyph />
                      <span className="train-bar-human">{human}</span>
                      {human !== canonical ? (
                        <small className="train-bar-canonical">{canonical}</small>
                      ) : null}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          {occupancy.length === 0 ? (
            <p className="timeline-empty">
              No protected train occupancy on this section.
            </p>
          ) : null}

          <div className="planner-timeline-row maintenance-row">
            <span className="timeline-lane-label">Possessions</span>
            <div className="planner-timeline-track">
              <TimelineGrid ticks={ticks} />
              {blocks.map((block) => {
                const blockTasks = block.tasks
                  .map((id) => taskById.get(id))
                  .filter(Boolean);
                const depts = [
                  ...new Set(
                    blockTasks.map((t) => departmentLabel(t.department)),
                  ),
                ];
                const deptText =
                  depts.length > 0 ? depts.join(" + ") : "Maintenance";
                const isSelected = selectedBlockId === block.block_id;

                return (
                  <button
                    key={block.block_id}
                    type="button"
                    className={`planner-timeline-bar maintenance valid ${
                      block.integrated ? "is-integrated" : ""
                    } ${isSelected ? "is-selected" : ""}`}
                    style={rangeStyle(block.start_time, block.end_time, horizon)}
                    onClick={() => onSelectBlock(block.block_id)}
                    onMouseEnter={(e) => handleBlockHover(block, deptText, e)}
                    onMouseLeave={hideTooltip}
                    aria-label={`${deptText} (${block.block_id}): ${timeLabel(
                      block.start_time,
                    )} to ${timeLabel(block.end_time)}`}
                  >
                    <span
                      className="possession-phase setup"
                      aria-hidden="true"
                    >
                      <span className="phase-letter">SET</span>
                    </span>
                    <span className="possession-phase work">
                      <strong className="possession-dept-title">
                        {deptText}
                      </strong>
                      <span className="possession-meta-sub">
                        <small className="possession-type-tag">
                          {block.integrated ? "Integrated" : "Individual"}
                        </small>
                        <small className="possession-id-tag">
                          {block.block_id}
                        </small>
                      </span>
                    </span>
                    <span
                      className="possession-phase release"
                      aria-hidden="true"
                    >
                      <span className="phase-letter">REL</span>
                    </span>
                  </button>
                );
              })}
              {blocks.length === 0 ? (
                <span className="timeline-maintenance-empty">
                  {hasPlan
                    ? "No possession scheduled on this section"
                    : "Run optimizer to generate possessions"}
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <div className="timeline-reading-order">
        Possession includes setup, maintenance activity and release.
      </div>
    </section>
  );
}
