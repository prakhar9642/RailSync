import { useEffect, useMemo, useRef, useState } from "react";
import Navbar from "../components/layout/Navbar.jsx";
import BlockDetails from "../components/planning/BlockDetails.jsx";
import MaintenanceTaskList from "../components/planning/MaintenanceTaskList.jsx";
import MaintenanceTimeline from "../components/planning/MaintenanceTimeline.jsx";
import OptimizerControls from "../components/planning/OptimizerControls.jsx";
import PlannerCorridor from "../components/planning/PlannerCorridor.jsx";
import {
  getTasks,
  getTerritory,
  getTrains,
  optimizePlan,
} from "../services/api.js";
import "./planner/planner.css";

const DEMO_TERRITORY_ID = "eastern_hdn_test_fixture";

function initialDataState() {
  return {
    status: "loading",
    error: null,
    territory: null,
    tasks: [],
    trains: [],
  };
}

export default function PlanningWorkspace({ onHome }) {
  const [dataState, setDataState] = useState(initialDataState);
  const [loadVersion, setLoadVersion] = useState(0);
  const [selectedSection, setSelectedSection] = useState("");
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [selectedBlockId, setSelectedBlockId] = useState("");
  const [optimizationStatus, setOptimizationStatus] = useState("idle");
  const [optimizationError, setOptimizationError] = useState(null);
  const [plan, setPlan] = useState(null);
  const optimizeRequestId = useRef(0);
  const optimizeController = useRef(null);
  const selectedSectionRef = useRef("");

  useEffect(() => {
    const controller = new AbortController();

    Promise.all([
      getTerritory(DEMO_TERRITORY_ID, { signal: controller.signal }),
      getTasks(DEMO_TERRITORY_ID, { signal: controller.signal }),
      getTrains(DEMO_TERRITORY_ID, { signal: controller.signal }),
    ])
      .then(([territory, taskResponse, trainResponse]) => {
        const territoryIds = [
          territory.territory_id,
          taskResponse.territory_id,
          trainResponse.territory_id,
        ];
        if (territoryIds.some((id) => id !== DEMO_TERRITORY_ID)) {
          throw new Error("Backend returned inconsistent territory data.");
        }

        const tasks = taskResponse.tasks ?? [];
        const sections = territory.sections ?? [];
        const firstSection = sections[0]?.section_id ?? tasks[0]?.section_id ?? "";
        const firstTask = tasks.find((task) => task.section_id === firstSection);

        setDataState({
          status: "ready",
          error: null,
          territory,
          tasks,
          trains: trainResponse.trains ?? [],
        });
        selectedSectionRef.current = firstSection;
        setSelectedSection(firstSection);
        setSelectedTaskId(firstTask?.task_id ?? "");
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setDataState({
          ...initialDataState(),
          status: "error",
          error,
        });
      });

    return () => controller.abort();
  }, [loadVersion]);

  useEffect(
    () => () => {
      optimizeRequestId.current += 1;
      optimizeController.current?.abort();
    },
    [],
  );

  const selectedBlock = useMemo(
    () => plan?.blocks.find((block) => block.block_id === selectedBlockId) ?? null,
    [plan, selectedBlockId],
  );

  const sectionOccupancy = useMemo(
    () => dataState.trains.filter((train) => train.section_id === selectedSection),
    [dataState.trains, selectedSection],
  );

  const sectionBlocks = useMemo(
    () => plan?.blocks.filter((block) => block.section_id === selectedSection) ?? [],
    [plan, selectedSection],
  );

  const scheduledTaskIds = useMemo(
    () => new Set(plan?.blocks.flatMap((block) => block.tasks) ?? []),
    [plan],
  );
  const unscheduledTaskIds = useMemo(
    () => new Set(plan?.unscheduled_tasks ?? []),
    [plan],
  );

  const horizon = useMemo(() => {
    if (plan?.planning_context) {
      return {
        start_time: plan.planning_context.horizon_start,
        end_time: plan.planning_context.horizon_end,
      };
    }
    return dataState.territory?.planning_horizon ?? null;
  }, [dataState.territory, plan]);

  const selectSection = (sectionId) => {
    const firstTask = dataState.tasks.find((task) => task.section_id === sectionId);
    const firstBlock = plan?.blocks.find((block) => block.section_id === sectionId);
    selectedSectionRef.current = sectionId;
    setSelectedSection(sectionId);
    setSelectedTaskId(firstTask?.task_id ?? "");
    setSelectedBlockId(firstBlock?.block_id ?? "");
  };

  const selectTask = (task) => {
    const firstBlock = plan?.blocks.find((block) => block.section_id === task.section_id);
    selectedSectionRef.current = task.section_id;
    setSelectedTaskId(task.task_id);
    setSelectedSection(task.section_id);
    setSelectedBlockId(firstBlock?.block_id ?? "");
  };

  const runOptimization = async () => {
    optimizeController.current?.abort();
    const controller = new AbortController();
    const requestId = optimizeRequestId.current + 1;
    optimizeRequestId.current = requestId;
    optimizeController.current = controller;

    setOptimizationStatus("loading");
    setOptimizationError(null);
    setPlan(null);
    setSelectedBlockId("");

    try {
      const result = await optimizePlan(DEMO_TERRITORY_ID, {
        signal: controller.signal,
      });
      if (requestId !== optimizeRequestId.current) return;

      const firstBlockForSection = result.blocks.find(
        (block) => block.section_id === selectedSectionRef.current,
      );
      const initialBlock = firstBlockForSection ?? result.blocks[0] ?? null;
      setPlan(result);
      setSelectedBlockId(initialBlock?.block_id ?? "");
      if (!selectedSectionRef.current && initialBlock) {
        selectedSectionRef.current = initialBlock.section_id;
        setSelectedSection(initialBlock.section_id);
      }
      setOptimizationStatus("success");
    } catch (error) {
      if (error.name === "AbortError" || requestId !== optimizeRequestId.current) return;
      setPlan(null);
      setOptimizationError(error);
      setOptimizationStatus("error");
    } finally {
      if (requestId === optimizeRequestId.current) optimizeController.current = null;
    }
  };

  const retryDataLoad = () => {
    setDataState(initialDataState());
    setLoadVersion((version) => version + 1);
  };
  const dataReady = dataState.status === "ready";

  return (
    <div className="planning-workspace">
      <Navbar workspace onHome={onHome} />

      <main className="planning-workspace-main" id="planning-workspace">
        <header className="planning-workspace-intro">
          <span className="planner-kicker">Railway maintenance planning</span>
          <div className="planning-title-row">
            <h1>Planning Workspace</h1>
            <span className="synthetic-fixture-badge">Synthetic Test Fixture</span>
          </div>
          <p>
            Coordinate maintenance requirements with train occupancy and generate
            practical block windows through the RailSync optimizer.
          </p>
        </header>

        {dataState.status === "loading" ? (
          <div className="planner-data-state" role="status">
            Loading maintenance and train data from FastAPI...
          </div>
        ) : null}
        {dataState.status === "error" ? (
          <div className="planner-data-state is-error" role="alert">
            <div>
              <strong>Planning data could not be loaded.</strong>
              <span>{dataState.error?.message}</span>
            </div>
            <button type="button" onClick={retryDataLoad}>Retry</button>
          </div>
        ) : null}

        {dataReady ? (
          <>
            <PlannerCorridor
              territory={dataState.territory}
              selectedSection={selectedSection}
              onSelectSection={selectSection}
            />

            <div className="planning-workspace-grid">
              <MaintenanceTaskList
                tasks={dataState.tasks}
                sections={dataState.territory.sections}
                selectedSection={selectedSection}
                selectedTaskId={selectedTaskId}
                scheduledTaskIds={scheduledTaskIds}
                unscheduledTaskIds={unscheduledTaskIds}
                onSelectSection={selectSection}
                onSelectTask={selectTask}
              />

              <MaintenanceTimeline
                sectionId={selectedSection}
                occupancy={sectionOccupancy}
                blocks={sectionBlocks}
                horizon={horizon}
                hasPlan={Boolean(plan)}
                selectedBlockId={selectedBlockId}
                onSelectBlock={setSelectedBlockId}
              />

              <aside className="planner-control-column">
                <OptimizerControls
                  optimizationStatus={optimizationStatus}
                  optimizationError={optimizationError}
                  plan={plan}
                  horizon={horizon}
                  onOptimize={runOptimization}
                  canOptimize={dataReady}
                />
                <BlockDetails block={selectedBlock} tasks={dataState.tasks} />
              </aside>
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
