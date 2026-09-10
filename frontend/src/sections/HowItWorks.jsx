export default function HowItWorks() {
  return <section className="section rescue-decides" id="how-it-works">
    <div className="section-inner">
      <span className="section-eyebrow">How RailSync decides</span>
      <h2>Constraint-aware optimization</h2>
      <p>Find the window. Coordinate the work. Keep the railway moving.</p>
      <div className="decision-flow" aria-label="Train traffic, maintenance demand and resources feed CP-SAT to produce an integrated block plan">
        <div className="decision-inputs"><span>Train Traffic</span><b>+</b><span>Maintenance Demand</span><b>+</b><span>Resources &amp; Capacity</span></div>
        <span aria-hidden="true">↓</span><strong>CP-SAT</strong><span aria-hidden="true">↓</span><strong className="decision-output">Integrated Block Plan</strong>
      </div>
      <div className="integrated-story"><div><span className="section-eyebrow">Integrated possession</span><h3>Coordinate compatible work.<br />Reduce separate possessions.</h3><p>Illustrative coordination pattern</p></div>
        <div className="possession-example"><span>Before</span><div className="example-before"><i>Engineering</i><i>S&amp;T</i><i>TRD</i></div><span>RailSync</span><div className="example-after"><i>Engineering + S&amp;T</i><i>TRD</i></div></div>
      </div>
    </div>
  </section>;
}
