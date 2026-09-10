import SectionHeading from "../components/ui/SectionHeading.jsx";

export default function IntegratedPossessionSection() {
  return (
    <section className="section integrated-possession-section" id="coordination">
      <div className="section-inner">
        <SectionHeading
          eyebrow="Integrated Possessions"
          title="Coordinate compatible work. Reduce separate possessions."
        >
          When departments share track access, RailSync synchronizes compatible
          activities into fewer, longer possessions instead of shutting the line
          down repeatedly.
        </SectionHeading>

        <div className="possession-comparison-wrap" aria-label="Comparison between separate and integrated possessions">
          {/* BEFORE */}
          <div className="possession-pane before-pane">
            <div className="pane-header">
              <span className="pane-tag">BEFORE</span>
              <strong>Separate uncoordinated closures</strong>
            </div>
            <div className="timeline-visual-rows">
              <div className="visual-row">
                <span className="row-label">Engineering</span>
                <div className="row-track">
                  <span className="block-bar separate-eng" style={{ left: "6%", width: "32%" }}>
                    120 min
                  </span>
                </div>
              </div>
              <div className="visual-row">
                <span className="row-label">S&amp;T</span>
                <div className="row-track">
                  <span className="block-bar separate-snt" style={{ left: "42%", width: "24%" }}>
                    75 min
                  </span>
                </div>
              </div>
              <div className="visual-row">
                <span className="row-label">TRD</span>
                <div className="row-track">
                  <span className="block-bar separate-trd" style={{ left: "70%", width: "25%" }}>
                    60 min
                  </span>
                </div>
              </div>
            </div>
            <p className="pane-caption">3 separate possessions · 255 min total closure</p>
          </div>

          {/* RAILSYNC */}
          <div className="possession-pane railsync-pane">
            <div className="pane-header">
              <span className="pane-tag tag-railsync">RAILSYNC</span>
              <strong>Coordinated integrated possession</strong>
            </div>
            <div className="timeline-visual-rows">
              <div className="visual-row">
                <span className="row-label">Engineering + S&amp;T</span>
                <div className="row-track">
                  <span className="block-bar coordinated-bar" style={{ left: "12%", width: "52%" }}>
                    135 min · Coordinated
                  </span>
                </div>
              </div>
              <div className="visual-row">
                <span className="row-label">TRD</span>
                <div className="row-track">
                  <span className="block-bar separate-trd" style={{ left: "68%", width: "25%" }}>
                    60 min
                  </span>
                </div>
              </div>
            </div>
            <p className="pane-caption pane-caption-saved">2 possessions · 195 min total · 60 min line closure saved</p>
          </div>
        </div>
      </div>
    </section>
  );
}
