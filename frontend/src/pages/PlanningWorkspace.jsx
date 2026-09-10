import { useEffect, useMemo, useRef, useState } from "react";
import Navbar from "../components/layout/Navbar.jsx";
import DataAssumptions from "../components/analysis/DataAssumptions.jsx";
import RiskControls, { RiskResult } from "../components/planning/RiskControls.jsx";
import { riskOptions } from "../utils/risk.js";
import BlockDetails from "../components/planning/BlockDetails.jsx";
import MaintenanceTaskList from "../components/planning/MaintenanceTaskList.jsx";
import MaintenanceTimeline from "../components/planning/MaintenanceTimeline.jsx";
import OptimizerControls from "../components/planning/OptimizerControls.jsx";
import PlannerCorridor from "../components/planning/PlannerCorridor.jsx";
import {
  getTasks,
  getTerritory,
  getTerritories,
  getTrains,
  optimizePlan,
} from "../services/api.js";
import "./planner/planner.css";

const DEFAULT_TERRITORY_ID = "saktigarh_memari_public_demo";

function territoryChoiceLabel(territory) {
  if (territory.provenance?.includes("PUBLIC_TIMETABLE_DERIVED")) {
    return `${territory.display_name.replace(/^Public Timetable Demo · /, "")} — Historical public timetable demo`;
  }
  if (territory.provenance?.includes("TEST_FIXTURE")) {
    return `${territory.display_name.replace(/ Synthetic Test Fixture$/, "")} — Synthetic test fixture`;
  }
  return territory.display_name;
}

function initialDataState(session = {}) {
  if (session.territory) {
    return {
      status: "ready",
      error: null,
      territory: session.territory,
      tasks: session.tasks,
      trains: session.trains,
    };
  }
  return {
    status: session.dataError ? "error" : "loading",
    error: session.dataError ?? null,
    territory: null,
    tasks: [],
    trains: [],
  };
}

export default function PlanningWorkspace({ session, setSession, onNavigate, onHome }) {
  const initialSection = session.territory?.sections?.[0]?.section_id ?? "";
  const initialTask = session.tasks.find((task) => task.section_id === initialSection);
  const initialBlock = session.plan?.blocks.find(
    (block) => block.section_id === initialSection,
  );
  const [dataState, setDataState] = useState(() => initialDataState(session));
  const [territoryId, setTerritoryId] = useState(
    session.territoryId ?? session.territory?.territory_id ?? DEFAULT_TERRITORY_ID,
  );
  const [availableTerritories, setAvailableTerritories] = useState([]);
  const [loadVersion, setLoadVersion] = useState(0);
  const [selectedSection, setSelectedSection] = useState(initialSection);
  const [selectedTaskId, setSelectedTaskId] = useState(initialTask?.task_id ?? "");
  const [selectedBlockId, setSelectedBlockId] = useState(initialBlock?.block_id ?? "");
  const [optimizationStatus, setOptimizationStatus] = useState(
    session.plan ? "success" : session.optimizationError ? "error" : "idle",
  );
  const [optimizationError, setOptimizationError] = useState(session.optimizationError);
  const [plan, setPlan] = useState(session.plan);
  const optimizeRequestId = useRef(0);
  const optimizeController = useRef(null);
  const selectedSectionRef = useRef(initialSection);

  useEffect(() => {
    const controller = new AbortController();
    getTerritories({ signal: controller.signal })
      .then((response) => setAvailableTerritories(
        (response.territories ?? []).filter((item) => item.planning_ready),
      ))
      .catch((error) => {
        if (error.name !== "AbortError") setAvailableTerritories([]);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (session.territory?.territory_id === territoryId) return undefined;
    const controller = new AbortController();

    Promise.all([
      getTerritory(territoryId, { signal: controller.signal }),
      getTasks(territoryId, { signal: controller.signal }),
      getTrains(territoryId, { signal: controller.signal }),
    ])
      .then(([territory, taskResponse, trainResponse]) => {
        const territoryIds = [
          territory.territory_id,
          taskResponse.territory_id,
          trainResponse.territory_id,
        ];
        if (territoryIds.some((id) => id !== territoryId)) {
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
        setSession((current) => ({
          ...current,
          territoryId,
          territory,
          tasks,
          trains: trainResponse.trains ?? [],
          dataError: null,
        }));
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
        setSession((current) => ({ ...current, dataError: error, plan: null }));
      });

    return () => controller.abort();
  }, [loadVersion, session.territory, setSession, territoryId]);

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

  const selectedBlockDiagnostic = useMemo(
    () =>
      plan?.analysis?.block_diagnostics.find(
        (item) => item.block_id === selectedBlockId,
      ) ?? null,
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
    setSession((current) => ({
      ...current,
      plan: null,
      optimizationError: null,
      recovery: null,
    }));
    setSelectedBlockId("");

    try {
      const result = await optimizePlan(territoryId, {
        signal: controller.signal,
        ...riskOptions(session.riskConfig),
      });
      if (requestId !== optimizeRequestId.current) return;

      const firstBlockForSection = result.blocks.find(
        (block) => block.section_id === selectedSectionRef.current,
      );
      const initialBlock = firstBlockForSection ?? result.blocks[0] ?? null;
      setPlan(result);
      setSession((current) => ({
        ...current,
        plan: result,
        optimizationError: null,
      }));
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
      setSession((current) => ({
        ...current,
        plan: null,
        optimizationError: error,
      }));
    } finally {
      if (requestId === optimizeRequestId.current) optimizeController.current = null;
    }
  };

  const retryDataLoad = () => {
    setDataState(initialDataState());
    setSession((current) => ({
      ...current,
      territory: null,
      tasks: [],
      trains: [],
      plan: null,
      dataError: null,
      optimizationError: null,
    }));
    setLoadVersion((version) => version + 1);
  };
  const selectTerritory = (event) => {
    const nextId = event.target.value;
    optimizeRequestId.current += 1;
    optimizeController.current?.abort();
    setTerritoryId(nextId);
    setDataState(initialDataState());
    setSelectedSection("");
    selectedSectionRef.current = "";
    setSelectedTaskId("");
    setSelectedBlockId("");
    setPlan(null);
    setOptimizationStatus("idle");
    setOptimizationError(null);
    setSession((current) => ({
      ...current,
      territoryId: nextId,
      territory: null,
      tasks: [],
      trains: [],
      plan: null,
      recovery: null,
      dataError: null,
      optimizationError: null,
    }));
  };
  const dataReady = dataState.status === "ready";

  return (
    <div className="planning-workspace">
      <Navbar
        workspace
        activeWorkspaceView="planning"
        onNavigateWorkspace={onNavigate}
        onHome={onHome}
      />

      <main className="planning-workspace-main" id="planning-workspace">
        <header className="planning-workspace-intro">
          <span className="planner-kicker">Railway maintenance planning</span>
          <div className="planning-title-row">
            <h1>Planning Workspace</h1>
            <span className="synthetic-fixture-badge">
              {dataState.territory?.provenance?.includes("PUBLIC_TIMETABLE_DERIVED")
                ? "Historical Public Timetable"
                : "Synthetic Test Fixture"}
            </span>
          </div>
          <p>
            Coordinate maintenance requirements with train occupancy and generate
            practical block windows through the RailSync optimizer.
          </p>
          <label className="territory-selector">
            <span>Demo territory</span>
            <select value={territoryId} onChange={selectTerritory}>
              {(availableTerritories.length
                ? availableTerritories
                : [{ territory_id: territoryId, display_name: dataState.territory?.display_name ?? territoryId }]
              ).map((item) => (
                <option key={item.territory_id} value={item.territory_id}>
                  {territoryChoiceLabel(item)}
                </option>
              ))}
            </select>
          </label>
        </header>

        {dataState.status === "loading" ? (
          <div className="planner-data-state" role="status">
            Loading maintenance and train timetable data...
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

            <RiskControls config={session.riskConfig}
              onChange={(riskConfig) => setSession((current) => ({ ...current, riskConfig }))}
              trains={dataState.trains} territory={dataState.territory} disabled={optimizationStatus === "loading"} />
            <RiskResult risk={plan?.risk} />

            <div className="planning-workspace-grid">
              <MaintenanceTimeline
                sectionId={selectedSection}
                occupancy={sectionOccupancy}
                blocks={sectionBlocks}
                horizon={horizon}
                hasPlan={Boolean(plan)}
                selectedBlockId={selectedBlockId}
                onSelectBlock={setSelectedBlockId}
                territory={dataState.territory}
                tasks={dataState.tasks}
              />

              <MaintenanceTaskList
                tasks={dataState.tasks}
                sections={dataState.territory.sections}
                territory={dataState.territory}
                selectedSection={selectedSection}
                selectedTaskId={selectedTaskId}
                scheduledTaskIds={scheduledTaskIds}
                unscheduledTaskIds={unscheduledTaskIds}
                onSelectSection={selectSection}
                onSelectTask={selectTask}
              />

              <aside className="planner-control-column">
                <OptimizerControls
                  optimizationStatus={optimizationStatus}
                  optimizationError={optimizationError}
                  plan={plan}
                  horizon={horizon}
                  onOptimize={runOptimization}
                  canOptimize={dataReady}
                  tasks={dataState.tasks}
                />
              </aside>
            </div>
            <BlockDetails
              block={selectedBlock}
              diagnostic={selectedBlockDiagnostic}
              tasks={dataState.tasks}
              territory={dataState.territory}
            />
            <DataAssumptions plan={plan} territory={dataState.territory} />
          </>
        ) : null}
      </main>
    </div>
  );
}
