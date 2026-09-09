import { useState } from "react";
import AnalysisPage from "./pages/AnalysisPage.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import PlanningWorkspace from "./pages/PlanningWorkspace.jsx";
import ScenarioLab from "./pages/ScenarioLab.jsx";

function App() {
  const [view, setView] = useState("landing");
  const [workspaceView, setWorkspaceView] = useState("planning");
  const [planningSession, setPlanningSession] = useState({
    territory: null,
    tasks: [],
    trains: [],
    plan: null,
    dataError: null,
    optimizationError: null,
    recovery: null,
    riskConfig: { mode: "STATIC", target: "", profile: "" },
  });

  if (view === "workspace") {
    if (workspaceView === "scenario") {
      return <ScenarioLab session={planningSession} setSession={setPlanningSession}
        onNavigate={setWorkspaceView} onHome={() => setView("landing")} />;
    }
    if (workspaceView === "analysis") {
      return (
        <AnalysisPage
          session={planningSession}
          onNavigate={setWorkspaceView}
          onHome={() => setView("landing")}
        />
      );
    }
    return (
      <PlanningWorkspace
        session={planningSession}
        setSession={setPlanningSession}
        onNavigate={setWorkspaceView}
        onHome={() => setView("landing")}
      />
    );
  }

  return (
    <LandingPage
      onLaunchPlanner={() => {
        setWorkspaceView("planning");
        setView("workspace");
      }}
    />
  );
}

export default App;
