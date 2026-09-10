import "./dataAssumptions.css";

export default function DataAssumptions({ defaultOpen = false, territory = null }) {
  const publicTimetable = territory?.provenance?.includes("PUBLIC_TIMETABLE_DERIVED");
  return (
    <details className="data-assumptions" open={defaultOpen}>
      <summary>
        <span>Data &amp; Assumptions</span>
        <small>Provenance and prototype limits</small>
      </summary>
      <dl>
        <div><dt>Territory</dt><dd>{publicTimetable ? "Historical public timetable subset" : "Synthetic Test Fixture (Eastern HDN topology)"}</dd></div>
        <div><dt>Train occupancy</dt><dd>{publicTimetable ? "Official public timetable-derived occupancy; published validity 1 Nov 2017–30 Jun 2018" : "Synthetic timetable fixture"}</dd></div>
        <div><dt>Maintenance</dt><dd>Synthetic work orders and demands</dd></div>
        <div>
          <dt>Crew, machine, power</dt>
          <dd>Synthetic prototype resource inputs</dd>
        </div>
        <div><dt>Solver</dt><dd>Real OR-Tools CP-SAT constraint optimization engine</dd></div>
        <div><dt>Baseline</dt><dd>Independent non-integrated CP-SAT comparison</dd></div>
        <div><dt>Safety margins</dt><dd>Configurable prototype policy</dd></div>
        <div><dt>Setup and release</dt><dd>Configurable prototype policy</dd></div>
        <div><dt>Compatibility</dt><dd>Prototype policy; requires domain validation</dd></div>
        <div><dt>Historical risk model</dt><dd>Experimental public aggregate-delay estimate; substantial error, not individual-run forecasting</dd></div>
        <div><dt>Scenario inputs</dt><dd>Synthetic forecast experiment; explicit train delay or public-profile transfer</dd></div>
        <div>
          <dt>Boundary slack</dt>
          <dd>Deterministic resilience heuristic; not a probability of successful execution</dd>
        </div>
      </dl>
      <p>{territory?.description} No live Indian Railways operational feed is connected. Optimization and recovery computations run live via OR-Tools CP-SAT.</p>
    </details>
  );
}
