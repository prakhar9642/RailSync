import { useMemo, useState } from "react";
import { trainLabel } from "../../utils/planningLabels.js";
import { timeLabel } from "../../utils/timeline.js";

const WIDTH = 1000;
const LEFT = 170;
const RIGHT = 24;
const TOP = 44;
const ROW = 42;

function minutesFrom(value, origin) {
  return (new Date(value).getTime() - new Date(origin).getTime()) / 60000;
}

export default function TimeDistanceDiagram({ territory, occupancy, blocks, horizon, selectedSection, selectedBlockId, onSelectBlock }) {
  const [selectedTrain, setSelectedTrain] = useState(null);
  const model = useMemo(() => {
    if (!territory || !horizon) return null;
    const stations = [...territory.stations].sort((a, b) => a.order - b.order);
    const stationById = new Map(stations.map((station, index) => [station.station_id, { ...station, index }]));
    const sectionById = new Map(territory.sections.map((section) => [section.section_id, section]));
    const serviceById = new Map((territory.train_services ?? []).map((service) => [service.train_id, service]));
    const total = Math.max(1, minutesFrom(horizon.end_time, horizon.start_time));
    const x = (value) => LEFT + Math.max(0, Math.min(total, minutesFrom(value, horizon.start_time))) / total * (WIDTH - LEFT - RIGHT);
    const y = (stationId) => TOP + (stationById.get(stationId)?.index ?? 0) * ROW;
    const paths = [];
    const byTrain = new Map();
    occupancy.forEach((row) => byTrain.set(row.train_id, [...(byTrain.get(row.train_id) ?? []), row]));
    byTrain.forEach((rows, trainId) => {
      const service = serviceById.get(trainId);
      const sequence = service?.station_sequence ?? [];
      const points = [];
      rows.sort((a, b) => new Date(a.entry_time) - new Date(b.entry_time)).forEach((row) => {
        const section = sectionById.get(row.section_id);
        if (!section) return;
        const fromIndex = sequence.indexOf(section.from_station);
        const toIndex = sequence.indexOf(section.to_station);
        const forward = fromIndex < 0 || toIndex < 0 ? true : fromIndex < toIndex;
        const entryStation = forward ? section.from_station : section.to_station;
        const exitStation = forward ? section.to_station : section.from_station;
        points.push([x(row.entry_time), y(entryStation)], [x(row.exit_time), y(exitStation)]);
      });
      paths.push({ trainId, label: trainLabel(trainId, territory), points });
    });
    const blockRects = blocks.map((block) => {
      const sectionIds = block.section_ids?.length ? block.section_ids : [block.section_id];
      const stationIndexes = sectionIds.flatMap((id) => {
        const section = sectionById.get(id);
        return section ? [stationById.get(section.from_station)?.index, stationById.get(section.to_station)?.index] : [];
      }).filter(Number.isFinite);
      const min = Math.min(...stationIndexes);
      const max = Math.max(...stationIndexes);
      return { ...block, x: x(block.start_time), width: Math.max(5, x(block.end_time) - x(block.start_time)), y: TOP + min * ROW - 11, height: Math.max(22, (max - min) * ROW + 22) };
    });
    const ticks = Array.from({ length: 7 }, (_, index) => {
      const date = new Date(new Date(horizon.start_time).getTime() + total * index / 6 * 60000);
      return { x: LEFT + (WIDTH - LEFT - RIGHT) * index / 6, label: timeLabel(date.toISOString()) };
    });
    return { stations, paths, blockRects, ticks, y, height: TOP * 2 + Math.max(1, stations.length - 1) * ROW };
  }, [territory, occupancy, blocks, horizon]);

  if (!model) return null;
  return <section className="time-distance-card" aria-labelledby="time-distance-heading">
    <div className="workspace-column-heading time-distance-heading">
      <div><span className="planner-kicker">Route-wide operating picture</span><h2 id="time-distance-heading">Time–distance possession diagram</h2></div>
      <p>Time runs left to right; stations run top to bottom. Train paths and multi-section possessions share the same capacity view.</p>
    </div>
    <div className="time-distance-legend"><span><i className="td-train" /> Public train path</span><span><i className="td-block" /> Solver possession</span><span><i className="td-selected" /> Selected</span></div>
    <div className="time-distance-scroll">
      <svg className="time-distance-svg" viewBox={`0 0 ${WIDTH} ${model.height}`} role="img" aria-label="Time-distance chart of route stations, public train movements, and maintenance possessions">
        {model.ticks.map((tick) => <g key={tick.label + tick.x}><line x1={tick.x} y1={TOP - 20} x2={tick.x} y2={model.height - 24} className="td-grid-time" /><text x={tick.x} y={16} textAnchor="middle" className="td-time-label">{tick.label}</text></g>)}
        {model.stations.map((station) => <g key={station.station_id}><line x1={LEFT} y1={model.y(station.station_id)} x2={WIDTH - RIGHT} y2={model.y(station.station_id)} className="td-grid-station" /><text x={LEFT - 12} y={model.y(station.station_id) + 4} textAnchor="end" className="td-station-label">{station.station_name}</text></g>)}
        {model.paths.map((train) => train.points.length > 1 ? <polyline key={train.trainId} points={train.points.map((point) => point.join(",")).join(" ")} className={`td-train-path ${selectedTrain === train.trainId ? "is-selected" : ""}`} role="button" tabIndex="0" aria-label={train.label} onClick={() => setSelectedTrain(train.trainId)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelectedTrain(train.trainId); } }}><title>{train.label}</title></polyline> : null)}
        {model.blockRects.map((block) => <g key={block.block_id} className={`td-possession ${selectedBlockId === block.block_id ? "is-selected" : ""}`} onClick={() => onSelectBlock(block.block_id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelectBlock(block.block_id); } }} role="button" tabIndex="0" aria-label={`Select possession ${block.block_id}`}>
          <rect x={block.x} y={block.y} width={block.width} height={block.height} rx="4"><title>{block.block_id}: {block.tasks.join(", ")} · {timeLabel(block.start_time)}–{timeLabel(block.end_time)}</title></rect>
          {block.width > 54 ? <text x={block.x + 6} y={block.y + 15}>{block.block_id}</text> : null}
        </g>)}
        {selectedSection ? <text x={WIDTH - RIGHT} y={model.height - 7} textAnchor="end" className="td-scope-label">Focused section: {selectedSection}</text> : null}
      </svg>
    </div>
    {selectedTrain ? <p className="selected-route-train">Selected train: {trainLabel(selectedTrain, territory)}</p> : null}
    {!blocks.length ? <p className="timeline-empty">Run the CP-SAT optimizer to overlay maintenance possessions.</p> : null}
  </section>;
}
