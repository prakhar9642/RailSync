import { useState } from "react";
import { buildTicks, rangeStyle, timeLabel } from "../../utils/timeline.js";
import { sectionLabel, trainLabel } from "../../utils/planningLabels.js";

export default function RecoveryTimeline({ result, territory, tasks, originalTrains }) {
  const [selected, setSelected] = useState("");
  const preferred = result.invalidated_blocks[0]?.block_id;
  const sectionId = selected || result.base_plan.blocks.find((b) => b.block_id === preferred)?.section_id || result.affected_sections[0] || territory.sections[0]?.section_id;
  const horizon = { start_time: result.horizon_start, end_time: result.horizon_end };
  const ticks = buildTicks(horizon);
  const names = new Map(tasks.map((t) => [t.task_id, t.task_type]));
  const lanes = [
    { label: "Original trains", rows: originalTrains, train: true },
    { label: "Disrupted trains", rows: result.train_occupancy, train: true, changed: true },
    { label: "Before", rows: result.base_plan.blocks },
    { label: "Recovered", rows: result.recovered_plan.blocks, changed: true },
  ];
  return <section className="recovery-timeline" aria-labelledby="recovery-timeline-heading">
    <div className="scenario-section-heading">
      <div><span>Same section · same time axis</span><h2 id="recovery-timeline-heading">What changed on the railway?</h2></div>
      <label>Section<select aria-label="Recovery timeline section" value={sectionId} onChange={(event) => setSelected(event.target.value)}>
        {territory.sections.map((s) => <option key={s.section_id} value={s.section_id}>{sectionLabel(territory,s.section_id)} · {s.section_id}</option>)}
      </select></label>
    </div>
    <div className="recovery-timeline-scroll"><div className="recovery-axis"><span />
      <div>{ticks.map((tick) => <time key={tick.key}>{tick.label}</time>)}</div></div>
      {lanes.map((lane) => <div className="recovery-lane" key={lane.label}>
        <strong>{lane.label}</strong><div className="recovery-track">
          {ticks.map((tick) => <i key={tick.key} style={{ left: tick.left }} />)}
          {lane.rows.filter((row) => row.section_id === sectionId).map((row,index) => {
            const change = !lane.train && result.block_changes.find((item) => (lane.changed ? item.after_block_id : item.before_block_id) === row.block_id);
            const state = lane.train ? lane.changed && row.train_id === result.disruption.train_id ? "DISRUPTED" : "TRAIN" : change?.state ?? "UNKNOWN";
            const start = row.entry_time ?? row.start_time, end = row.exit_time ?? row.end_time;
            const label = lane.train ? trainLabel(row.train_id,territory) : row.tasks.map((id) => names.get(id) ?? id).join(" + ");
            return <span key={`${row.train_id ?? row.block_id}-${index}`} className={`recovery-bar state-${state.toLowerCase()}`}
              style={rangeStyle(start,end,horizon)} title={`${label}: ${start} – ${end} · ${state}`}>
              {lane.train ? label : `${state === "RETAINED" ? "Unchanged" : state.toLowerCase()} · ${label}`}
            </span>;
          })}
        </div>
      </div>)}
    </div>
    <p className="recovery-legend"><span className="retained">Unchanged</span><span className="shifted">Shifted</span><span className="new">New group</span><span className="cancelled">Cancelled group</span><span className="disrupted">Delayed train</span></p>
    <p className="scenario-note">Train intervals shift by {result.disruption.delay_minutes} minutes; their duration is preserved. Possessions include setup, work and release. Safety buffers are enforced but are not drawn as occupancy.</p>
    <div className="recovery-change-list">
      {result.block_changes.filter((item) => item.section_id === sectionId).map((item,index) => {
        const before = result.base_plan.blocks.find((b) => b.block_id === item.before_block_id);
        const after = result.recovered_plan.blocks.find((b) => b.block_id === item.after_block_id);
        return <div key={index}><strong>{item.task_ids.map((id) => names.get(id) ?? id).join(" + ")}</strong>
          <span>{item.state === "RETAINED" ? "Unchanged" : item.state.toLowerCase()} · {before ? `${timeLabel(before.start_time)}–${timeLabel(before.end_time)}` : "No previous group"} → {after ? `${timeLabel(after.start_time)}–${timeLabel(after.end_time)}` : "Group dissolved"}</span>
        </div>;
      })}
    </div>
  </section>;
}
