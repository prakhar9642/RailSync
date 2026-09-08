import "./dataAssumptions.css";

export default function DataAssumptions({ defaultOpen = false }) {
  return (
    <details className="data-assumptions" open={defaultOpen}>
      <summary>
        <span>Data &amp; Assumptions</span>
        <small>Provenance and prototype limits</small>
      </summary>
      <dl>
        <div><dt>Territory</dt><dd>Synthetic Test Fixture</dd></div>
        <div><dt>Train occupancy</dt><dd>Synthetic fixture</dd></div>
        <div><dt>Maintenance</dt><dd>Synthetic prototype</dd></div>
        <div>
          <dt>Crew, machine, power</dt>
          <dd>Synthetic fixture</dd>
        </div>
        <div><dt>Solver</dt><dd>OR-Tools CP-SAT constraint optimization</dd></div>
        <div><dt>Baseline</dt><dd>Non-integrated CP-SAT comparison</dd></div>
        <div><dt>Safety margins</dt><dd>Configurable prototype assumption</dd></div>
        <div><dt>Setup and release</dt><dd>Configurable prototype assumption</dd></div>
        <div><dt>Compatibility</dt><dd>Prototype policy; requires domain validation</dd></div>
        <div>
          <dt>Boundary slack</dt>
          <dd>Deterministic resilience heuristic; not a probability of successful execution</dd>
        </div>
      </dl>
      <p>No live Indian Railways operational feed is connected.</p>
    </details>
  );
}
