import { useMemo, useState } from "react";
import { departmentLabel, sectionLabel } from "../../utils/planningLabels.js";
import { buildTicks, rangeStyle, timeLabel } from "../../utils/timeline.js";

function TimelineGrid({ ticks }) {
  return (
    <span className="analysis-timeline-grid" aria-hidden="true">
      {ticks.map((tick) => <i key={tick.key} style={{ left: tick.left }} />)}
    </span>
  );
}

export default function PairedPossessionTimeline({ analysis, territory, tasks, horizon }) {
  const taskById = useMemo(
    () => new Map(tasks.map((task) => [task.task_id, task])),
    [tasks],
  );
  const availableSections = useMemo(
    () => territory.sections.filter((section) =>
      [...analysis.baseline.blocks, ...analysis.railsync.blocks].some(
        (block) => block.section_id === section.section_id,
      ),
    ),
    [analysis, territory.sections],
  );
  const preferredSection =
    analysis.integrated_blocks[0]?.section_id ?? availableSections[0]?.section_id ?? "";
  const [sectionId, setSectionId] = useState(preferredSection);
  const ticks = buildTicks(horizon);
  const planners = [
    ["Baseline", analysis.baseline.blocks, "baseline"],
    ["RailSync", analysis.railsync.blocks, "railsync"],
  ];

  return (
    <section className="paired-analysis" aria-labelledby="paired-timeline-heading">
      <div className="analysis-section-heading with-control">
        <div>
          <span>Signature analysis</span>
          <h2 id="paired-timeline-heading">Baseline vs RailSync possession timeline</h2>
          <p>Both lanes use the same territory, horizon, constraints, and selected section.</p>
        </div>
        <label>
          <span>Section</span>
          <select value={sectionId} onChange={(event) => setSectionId(event.target.value)}>
            {availableSections.map((section) => (
              <option key={section.section_id} value={section.section_id}>
                {sectionLabel(territory, section.section_id)} · {section.section_id}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="paired-timeline">
        <div className="paired-axis-row" aria-hidden="true">
          <span />
          <div>{ticks.map((tick) => <time key={tick.key}>{tick.label}</time>)}</div>
        </div>
        {planners.map(([label, allBlocks, className]) => {
          const blocks = allBlocks.filter((block) => block.section_id === sectionId);
          return (
            <div className="paired-lane" key={label}>
              <div className="paired-lane-label">
                <strong>{label}</strong>
                <small>{blocks.length} possession{blocks.length === 1 ? "" : "s"}</small>
              </div>
              <div className="paired-lane-track">
                <TimelineGrid ticks={ticks} />
                {blocks.map((block) => {
                  const taskDetails = block.tasks.map((id) => taskById.get(id)).filter(Boolean);
                  const taskNames = taskDetails.map((task) => task.task_type).join(" + ");
                  const departments = [...new Set(taskDetails.map((task) => departmentLabel(task.department)))];
                  return (
                    <span
                      key={block.block_id}
                      className={`paired-block ${className} ${block.integrated ? "is-integrated" : ""}`}
                      style={rangeStyle(block.start_time, block.end_time, horizon)}
                      title={`${taskNames}: ${timeLabel(block.start_time)}–${timeLabel(block.end_time)}`}
                    >
                      {block.integrated ? departments.join(" + ") : taskNames}
                    </span>
                  );
                })}
                {blocks.length === 0 ? <em>No possession</em> : null}
              </div>
            </div>
          );
        })}
      </div>

      <div className="paired-meaning">
        <strong>{sectionLabel(territory, sectionId)}</strong>
        <span>{analysis.fairness.statement}</span>
      </div>
    </section>
  );
}
