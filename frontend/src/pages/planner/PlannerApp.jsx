import { useState } from "react";
import Navbar from "../../components/layout/Navbar.jsx";
import "./planner.css";

export default function PlannerApp({ onHome }) {
  const [activePage, setActivePage] = useState("Planning");

  const renderPage = () => {
    if (activePage === "Command") {
      return <CommandPage />;
    }

    if (activePage === "Planning") {
      return <PlanningPage />;
    }

    if (activePage === "Analysis") {
      return <AnalysisPage />;
    }

    return <PlanningPage />;
  };

  return (
    <div className="planner-app">
      <Navbar onLaunchPlanner={() => setActivePage("Planning")} onHome={onHome} />

      <div className="planner-shell">
        <aside className="planner-sidebar">
          <p className="planner-sidebar-label">Workspace</p>
          <nav>
            <button
              className={activePage === "Command" ? "nav-button active" : "nav-button"}
              onClick={() => setActivePage("Command")}
            >
              Command
            </button>
            <button
              className={activePage === "Planning" ? "nav-button active" : "nav-button"}
              onClick={() => setActivePage("Planning")}
            >
              Planning
            </button>
            <button
              className={activePage === "Analysis" ? "nav-button active" : "nav-button"}
              onClick={() => setActivePage("Analysis")}
            >
              Analysis
            </button>
          </nav>
          <p className="planner-note">Phase 1 shell. Optimizer wiring is Phase 2.</p>
        </aside>

        <main className="planner-main">
          <header className="planner-topbar">
            <div>
              <p className="breadcrumb">RailSync / {activePage}</p>
              <h1>{activePage === "Planning" ? "Planning Workspace" : activePage}</h1>
            </div>
            <div className="planner-mobile-nav">
              <button
                type="button"
                className={activePage === "Command" ? "active" : ""}
                onClick={() => setActivePage("Command")}
              >
                Command
              </button>
              <button
                type="button"
                className={activePage === "Planning" ? "active" : ""}
                onClick={() => setActivePage("Planning")}
              >
                Planning
              </button>
              <button
                type="button"
                className={activePage === "Analysis" ? "active" : ""}
                onClick={() => setActivePage("Analysis")}
              >
                Analysis
              </button>
            </div>
          </header>
          <section className="planner-content">{renderPage()}</section>
        </main>
      </div>
    </div>
  );
}

function CommandPage() {
  return (
    <div>
      <div className="page-intro">
        <div>
          <h2>Operations Command Center</h2>
          <p>Monitor network status, maintenance demand and current planning state.</p>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard title="Open Tasks" value="48" />
        <KpiCard title="Critical Tasks" value="7" />
        <KpiCard title="Planned Blocks" value="18" />
        <KpiCard title="Affected Trains" value="12" />
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Critical Maintenance Tasks</h3>
          <span className="badge">Today</span>
        </div>

        <div className="task-row">
          <div>
            <strong>ENG017</strong>
            <p>Rail Weld Inspection — SEC03</p>
          </div>
          <span className="priority high">Critical</span>
        </div>

        <div className="task-row">
          <div>
            <strong>SNT008</strong>
            <p>Signal maintenance — SEC03</p>
          </div>
          <span className="priority medium">High</span>
        </div>

        <div className="task-row">
          <div>
            <strong>TRD004</strong>
            <p>Equipment maintenance — SEC03</p>
          </div>
          <span className="priority medium">High</span>
        </div>
      </div>
    </div>
  );
}

function PlanningPage() {
  return (
    <div>
      <div className="page-intro">
        <div>
          <h2>Block Planning Workspace</h2>
          <p>Review maintenance tasks and prepare the optimization request.</p>
        </div>
        <button className="optimize-button" type="button">
          Run Optimizer
        </button>
      </div>

      <div className="planning-grid">
        <div className="panel task-panel">
          <div className="panel-header">
            <h3>Task Queue</h3>
            <span className="badge">48 Tasks</span>
          </div>

          <div className="task-row selected">
            <div>
              <strong>ENG017</strong>
              <p>Rail Weld Inspection</p>
              <small>SEC03 · 120 min</small>
            </div>
            <span className="priority high">9/10</span>
          </div>

          <div className="task-row">
            <div>
              <strong>SNT008</strong>
              <p>Signal maintenance</p>
              <small>SEC03 · 45 min</small>
            </div>
            <span className="priority medium">7/10</span>
          </div>

          <div className="task-row">
            <div>
              <strong>TRD004</strong>
              <p>Equipment maintenance</p>
              <small>SEC03 · 60 min</small>
            </div>
            <span className="priority medium">6/10</span>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>Optimizer Controls</h3>
          </div>

          <label className="label">Planning Profile</label>
          <select className="select">
            <option>Balanced</option>
            <option>Asset Availability</option>
            <option>Operational Stability</option>
          </select>

          <label className="label">Planning Horizon</label>
          <select className="select">
            <option>Next 24 hours</option>
            <option>Next 48 hours</option>
            <option>Weekly</option>
          </select>

          <button className="primary-button" type="button">
            Optimize Plan
          </button>
        </div>
      </div>

      <div className="panel schedule-panel">
        <div className="panel-header">
          <h3>Planning Result</h3>
          <span className="badge">Waiting for optimizer</span>
        </div>
        <div className="empty-state">
          <h3>No optimized plan yet</h3>
          <p>Run the optimizer to generate maintenance blocks.</p>
        </div>
      </div>
    </div>
  );
}

function AnalysisPage() {
  return (
    <div>
      <div className="page-intro">
        <div>
          <h2>Optimization Analysis</h2>
          <p>Compare the baseline plan with optimized planning profiles.</p>
        </div>
      </div>

      <div className="comparison-grid">
        <div className="panel">
          <span className="panel-label">BASELINE</span>
          <h3>Department-by-department</h3>
          <div className="analysis-value">
            —
            <span> block hours</span>
          </div>
          <p>Awaiting solver comparison in Phase 2.</p>
        </div>

        <div className="panel">
          <span className="panel-label">OPTIMIZED</span>
          <h3>RailSync</h3>
          <div className="analysis-value">
            —
            <span> block hours</span>
          </div>
          <p>Waiting for solver output.</p>
        </div>
      </div>
    </div>
  );
}

function KpiCard({ title, value }) {
  return (
    <div className="kpi-card">
      <p>{title}</p>
      <h2>{value}</h2>
    </div>
  );
}
