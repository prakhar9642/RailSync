import Navbar from "../components/layout/Navbar.jsx";
import ComparisonSummary, { ComparisonDetails } from "../components/analysis/ComparisonSummary.jsx";
import DataAssumptions from "../components/analysis/DataAssumptions.jsx";
import IntegrationGains from "../components/analysis/IntegrationGains.jsx";
import OutstandingWork from "../components/analysis/OutstandingWork.jsx";
import PairedPossessionTimeline from "../components/analysis/PairedPossessionTimeline.jsx";
import Button from "../components/ui/Button.jsx";
import { RiskResult } from "../components/planning/RiskControls.jsx";
import "./analysis/analysis.css";

export default function AnalysisPage({ session, onNavigate, onHome }) {
  const { plan, territory, tasks, dataError, optimizationError } = session;
  const error = optimizationError ?? dataError;
  const horizon = plan
    ? {
        start_time: plan.planning_context.horizon_start,
        end_time: plan.planning_context.horizon_end,
      }
    : territory?.planning_horizon;

  return (
    <div className="analysis-page">
      <Navbar
        workspace
        activeWorkspaceView="analysis"
        onNavigateWorkspace={onNavigate}
        onHome={onHome}
      />
      <main className="analysis-main">
        <header className="analysis-hero">
          <span>Plan analysis</span>
          <h1>How coordination changed the plan</h1>
          <p>
            A factual comparison with the non-integrated CP-SAT ablation using the same inputs, constraints, priorities, and runtime budget.
          </p>
        </header>

        {!plan ? (
          <section className="analysis-empty" aria-labelledby="analysis-empty-heading">
            <span>Analysis awaits a real solver result</span>
            <h2 id="analysis-empty-heading">Generate a plan in Planning to view comparison.</h2>
            {error ? <p role="alert">{error.message}</p> : <p>No result has been generated in this session.</p>}
            <Button onClick={() => onNavigate("planning")}>Open Planning</Button>
          </section>
        ) : null}

        {plan?.analysis ? (
          <>
            <ComparisonSummary analysis={plan.analysis} />
            <RiskResult risk={plan.risk} />
            <PairedPossessionTimeline
              analysis={plan.analysis}
              territory={territory}
              tasks={tasks}
              horizon={horizon}
            />
            <ComparisonDetails analysis={plan.analysis} />
            <IntegrationGains
              gains={plan.analysis.integrated_blocks}
              territory={territory}
              tasks={tasks}
            />
            <OutstandingWork
              items={plan.analysis.unscheduled_tasks}
              territory={territory}
            />
          </>
        ) : null}

        {plan && !plan.analysis ? (
          <section className="analysis-empty">
            <h2>Comparison diagnostics are unavailable.</h2>
            <p>The result is preserved, but missing fields are not replaced with estimates.</p>
          </section>
        ) : null}

        <DataAssumptions plan={plan} territory={session.territory} />
      </main>
    </div>
  );
}
