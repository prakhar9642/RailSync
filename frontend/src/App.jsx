import { useState } from "react";
import LandingPage from "./pages/LandingPage.jsx";
import PlanningWorkspace from "./pages/PlanningWorkspace.jsx";

function App() {
  const [view, setView] = useState("landing");

  if (view === "planner") {
    return <PlanningWorkspace onHome={() => setView("landing")} />;
  }

  return <LandingPage onLaunchPlanner={() => setView("planner")} />;
}

export default App;
