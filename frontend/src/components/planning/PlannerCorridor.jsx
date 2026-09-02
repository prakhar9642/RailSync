import { plannerSections, plannerStations } from "../../data/plannerMockData.js";

const WIDTH = 1120;
const PAD = 48;
const TRACK_Y = 68;

function StationIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="m3 7 7-4 7 4M5 8v7m5-7v7m5-7v7M3 16h14" />
    </svg>
  );
}

export default function PlannerCorridor({ selectedSection, onSelectSection }) {
  const innerWidth = WIDTH - PAD * 2;
  const xAt = (index) => PAD + (innerWidth * index) / (plannerStations.length - 1);
  const sleepers = Array.from(
    { length: 32 },
    (_, index) => PAD + (innerWidth * index) / 31,
  );

  const selectWithKeyboard = (event, sectionId) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelectSection(sectionId);
    }
  };

  return (
    <section className="planner-corridor" aria-labelledby="corridor-heading">
      <div className="planner-corridor-heading">
        <div>
          <span className="planner-kicker">Prototype corridor</span>
          <h2 id="corridor-heading">Delhi–Agra</h2>
        </div>
        <p>
          Selected section <strong>{selectedSection}</strong>
        </p>
      </div>

      <div className="planner-corridor-scroll">
        <svg
          className="planner-corridor-svg"
          viewBox={`0 0 ${WIDTH} 112`}
          role="img"
          aria-label="Selectable railway sections from New Delhi to Agra Cantt"
        >
          {plannerSections.map((section, index) => {
            const x1 = xAt(index);
            const x2 = xAt(index + 1);
            const selected = selectedSection === section.id;

            return (
              <g
                key={section.id}
                className={`planner-corridor-section ${selected ? "is-selected" : ""}`}
                role="button"
                tabIndex="0"
                aria-label={`${section.id}, ${section.from} to ${section.to}`}
                aria-pressed={selected}
                onClick={() => onSelectSection(section.id)}
                onKeyDown={(event) => selectWithKeyboard(event, section.id)}
              >
                <rect
                  x={x1 + 4}
                  y="18"
                  width={x2 - x1 - 8}
                  height="72"
                  fill="transparent"
                />
                <line
                  className="planner-corridor-selection"
                  x1={x1 + 8}
                  y1={TRACK_Y + 4}
                  x2={x2 - 8}
                  y2={TRACK_Y + 4}
                />
                <text
                  x={(x1 + x2) / 2}
                  y="30"
                  textAnchor="middle"
                  className="planner-corridor-section-label"
                >
                  {section.id}
                </text>
              </g>
            );
          })}

          {sleepers.map((x) => (
            <line
              key={x}
              x1={x}
              y1={TRACK_Y - 6}
              x2={x}
              y2={TRACK_Y + 14}
              className="planner-corridor-sleeper"
            />
          ))}

          <line
            x1={PAD}
            y1={TRACK_Y}
            x2={WIDTH - PAD}
            y2={TRACK_Y}
            className="planner-corridor-rail primary"
          />
          <line
            x1={PAD}
            y1={TRACK_Y + 8}
            x2={WIDTH - PAD}
            y2={TRACK_Y + 8}
            className="planner-corridor-rail secondary"
          />

          {plannerStations.map((station, index) => (
            <g key={station.id} transform={`translate(${xAt(index)} ${TRACK_Y + 4})`}>
              <circle
                r={index === 0 || index === plannerStations.length - 1 ? 6.5 : 5}
                className="planner-corridor-node"
              />
            </g>
          ))}
        </svg>

        <div className="planner-station-list" aria-hidden="true">
          {plannerStations.map((station) => (
            <span key={station.id}>
              <StationIcon />
              {station.name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
