import { useState } from "react";
import LandingPage from "./pages/LandingPage.jsx";
import PlannerApp from "./pages/planner/PlannerApp.jsx";

function App() {
  const [view, setView] = useState("landing");

  if (view === "planner") {
    return <PlannerApp onHome={() => setView("landing")} />;
  }

  return <LandingPage onLaunchPlanner={() => setView("planner")} />;
}

export default App;
