import { useState } from "react";
import "./App.css";

function App() {
  const [activePage, setActivePage] = useState("Command");

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
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          <div className="logo-icon">R</div>
          <div>
            <h2>RailSync</h2>
            <span>Operations</span>
          </div>
        </div>

        <nav>
          <button
            className={activePage === "Command" ? "nav-button active" : "nav-button"}
            onClick={() => setActivePage("Command")}
          >
            <span>⌂</span>
            Command
          </button>

          <button
            className={activePage === "Planning" ? "nav-button active" : "nav-button"}
            onClick={() => setActivePage("Planning")}
          >
            <span>▣</span>
            Planning
          </button>

          <button
            className={activePage === "Analysis" ? "nav-button active" : "nav-button"}
            onClick={() => setActivePage("Analysis")}
          >
            <span>◈</span>
            Analysis
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot"></span>
            System Operational
          </div>
        </div>
      </aside>

      {/* Main application */}
      <main className="main">
        <header className="topbar">
          <div>
            <p className="breadcrumb">RailSync / {activePage}</p>
            <h1>{activePage}</h1>
          </div>

          <div className="header-status">
            <span className="status-dot"></span>
            Operational
          </div>
        </header>

        <section className="content">
          {renderPage()}
        </section>
      </main>
    </div>
  );
}


/* =========================
   COMMAND CENTER
========================= */

function CommandPage() {
  return (
    <div>
      <div className="page-intro">
        <div>
          <h2>Operations Command Center</h2>
          <p>
            Monitor network status, maintenance demand and current planning state.
          </p>
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
            <strong>ENG-017</strong>
            <p>Track inspection — SEC03</p>
          </div>
          <span className="priority high">Critical</span>
        </div>

        <div className="task-row">
          <div>
            <strong>SNT-008</strong>
            <p>Signal maintenance — SEC03</p>
          </div>
          <span className="priority medium">High</span>
        </div>

        <div className="task-row">
          <div>
            <strong>TRD-004</strong>
            <p>Equipment maintenance — SEC03</p>
          </div>
          <span className="priority medium">High</span>
        </div>
      </div>
    </div>
  );
}


/* =========================
   PLANNING WORKSPACE
========================= */

function PlanningPage() {
  return (
    <div>
      <div className="page-intro">
        <div>
          <h2>Block Planning Workspace</h2>
          <p>
            Review maintenance tasks and prepare the optimization request.
          </p>
        </div>

        <button className="optimize-button">
          Run Optimizer
        </button>
      </div>

      <div className="planning-grid">

        {/* Task Queue */}
        <div className="panel task-panel">
          <div className="panel-header">
            <h3>Task Queue</h3>
            <span className="badge">48 Tasks</span>
          </div>

          <div className="task-row selected">
            <div>
              <strong>ENG-017</strong>
              <p>Track inspection</p>
              <small>SEC03 · 120 min</small>
            </div>

            <span className="priority high">9/10</span>
          </div>

          <div className="task-row">
            <div>
              <strong>SNT-008</strong>
              <p>Signal maintenance</p>
              <small>SEC03 · 45 min</small>
            </div>

            <span className="priority medium">7/10</span>
          </div>

          <div className="task-row">
            <div>
              <strong>TRD-004</strong>
              <p>Equipment maintenance</p>
              <small>SEC03 · 60 min</small>
            </div>

            <span className="priority medium">6/10</span>
          </div>
        </div>


        {/* Optimizer Controls */}
        <div className="panel">
          <div className="panel-header">
            <h3>Optimizer Controls</h3>
          </div>

          <label className="label">
            Planning Profile
          </label>

          <select className="select">
            <option>Balanced</option>
            <option>Asset Availability</option>
            <option>Operational Stability</option>
          </select>

          <label className="label">
            Planning Horizon
          </label>

          <select className="select">
            <option>Next 24 hours</option>
            <option>Next 48 hours</option>
            <option>Weekly</option>
          </select>

          <button className="primary-button">
            Optimize Plan
          </button>
        </div>
      </div>


      {/* Schedule placeholder */}
      <div className="panel schedule-panel">
        <div className="panel-header">
          <h3>Planning Result</h3>
          <span className="badge">Waiting for optimizer</span>
        </div>

        <div className="empty-state">
          <div className="empty-icon">◫</div>

          <h3>No optimized plan yet</h3>

          <p>
            Run the optimizer to generate maintenance blocks.
          </p>
        </div>
      </div>
    </div>
  );
}


/* =========================
   ANALYSIS
========================= */

function AnalysisPage() {
  return (
    <div>
      <div className="page-intro">
        <div>
          <h2>Optimization Analysis</h2>
          <p>
            Compare the baseline plan with optimized planning profiles.
          </p>
        </div>
      </div>

      <div className="comparison-grid">

        <div className="panel">
          <span className="panel-label">BASELINE</span>
          <h3>Department-by-department</h3>

          <div className="analysis-value">
            42.5
            <span> block hours</span>
          </div>

          <p>Current reference plan</p>
        </div>

        <div className="panel">
          <span className="panel-label">OPTIMIZED</span>
          <h3>RailSync</h3>

          <div className="analysis-value">
            --
            <span> block hours</span>
          </div>

          <p>Waiting for solver output</p>
        </div>

      </div>
    </div>
  );
}


/* =========================
   KPI COMPONENT
========================= */

function KpiCard({ title, value }) {
  return (
    <div className="kpi-card">
      <p>{title}</p>
      <h2>{value}</h2>
    </div>
  );
}

export default App;