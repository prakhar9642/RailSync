import { useEffect, useMemo, useState } from "react";
import Navbar from "../components/layout/Navbar.jsx";
import BlockDetails from "../components/planning/BlockDetails.jsx";
import MaintenanceTaskList from "../components/planning/MaintenanceTaskList.jsx";
import MaintenanceTimeline from "../components/planning/MaintenanceTimeline.jsx";
import OptimizerControls from "../components/planning/OptimizerControls.jsx";
import PlannerCorridor from "../components/planning/PlannerCorridor.jsx";
import {
  maintenanceTasks,
  previewBlocksBySection,
  trainOccupancy,
} from "../data/plannerMockData.js";
import "./planner/planner.css";

const PREVIEW_TRANSITIONS = {
  evaluating: { next: "finding", delay: 450 },
  finding: { next: "proposed", delay: 450 },
  proposed: { next: "generated", delay: 500 },
};

export default function PlanningWorkspace({ onHome }) {
  const [selectedSection, setSelectedSection] = useState("SEC03");
  const [selectedTaskId, setSelectedTaskId] = useState("ENG017");
  const [optimizationStage, setOptimizationStage] = useState("idle");

  useEffect(() => {
    const transition = PREVIEW_TRANSITIONS[optimizationStage];
    if (!transition) return undefined;

    const id = window.setTimeout(
      () => setOptimizationStage(transition.next),
      transition.delay,
    );
    return () => window.clearTimeout(id);
  }, [optimizationStage]);

  const selectedTask = useMemo(
    () => maintenanceTasks.find((task) => task.task_id === selectedTaskId),
    [selectedTaskId],
  );

  const sectionOccupancy = useMemo(
    () => trainOccupancy.filter((train) => train.section_id === selectedSection),
    [selectedSection],
  );

  const previewBlock = previewBlocksBySection[selectedSection];
  const generatedBlock = optimizationStage === "generated" ? previewBlock : null;

  const resetPreview = () => setOptimizationStage("idle");

  const selectSection = (sectionId) => {
    const firstTask = maintenanceTasks.find((task) => task.section_id === sectionId);
    setSelectedSection(sectionId);
    setSelectedTaskId(firstTask?.task_id ?? "");
    resetPreview();
  };

  const selectTask = (task) => {
    setSelectedTaskId(task.task_id);
    setSelectedSection(task.section_id);
    resetPreview();
  };

  // Replace this state-machine entry point with POST /api/optimize in the API phase.
  const runOptimizationPreview = () => setOptimizationStage("evaluating");

  return (
    <div className="planning-workspace">
      <Navbar workspace onHome={onHome} />

      <main className="planning-workspace-main" id="planning-workspace">
        <header className="planning-workspace-intro">
          <span className="planner-kicker">Railway maintenance planning</span>
          <h1>Planning Workspace</h1>
          <p>
            Coordinate maintenance requirements with train occupancy and generate
            practical block windows.
          </p>
        </header>

        <PlannerCorridor
          selectedSection={selectedSection}
          onSelectSection={selectSection}
        />

        <div className="planning-workspace-grid">
          <MaintenanceTaskList
            tasks={maintenanceTasks}
            selectedTaskId={selectedTaskId}
            onSelectTask={selectTask}
          />

          <MaintenanceTimeline
            sectionId={selectedSection}
            occupancy={sectionOccupancy}
            selectedTask={selectedTask}
            previewBlock={previewBlock}
            optimizationStage={optimizationStage}
          />

          <aside className="planner-control-column">
            <OptimizerControls
              optimizationStage={optimizationStage}
              onOptimize={runOptimizationPreview}
            />
            <BlockDetails block={generatedBlock} />
          </aside>
        </div>
      </main>
    </div>
  );
}
