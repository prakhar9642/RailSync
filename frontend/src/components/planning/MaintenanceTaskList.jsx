import { useMemo, useState } from "react";
import { plannerSections } from "../../data/plannerMockData.js";

const departments = ["ENGINEERING", "S&T", "TRD"];
const priorities = ["Critical", "High", "Normal"];

function priorityForTask(task) {
  if (task.criticality >= 8) return "Critical";
  if (task.criticality >= 6) return "High";
  return "Normal";
}

function departmentLabel(department) {
  return department === "ENGINEERING" ? "Engineering" : department;
}

export default function MaintenanceTaskList({ tasks, selectedTaskId, onSelectTask }) {
  const [department, setDepartment] = useState("ALL");
  const [section, setSection] = useState("ALL");
  const [priority, setPriority] = useState("ALL");

  const filteredTasks = useMemo(
    () =>
      tasks.filter((task) => {
        const departmentMatch = department === "ALL" || task.department === department;
        const sectionMatch = section === "ALL" || task.section_id === section;
        const priorityMatch = priority === "ALL" || priorityForTask(task) === priority;
        return departmentMatch && sectionMatch && priorityMatch;
      }),
    [department, priority, section, tasks],
  );

  return (
    <section className="planner-task-column" aria-labelledby="maintenance-heading">
      <div className="workspace-column-heading">
        <div>
          <span className="planner-kicker">Work queue</span>
          <h2 id="maintenance-heading">Maintenance Requests</h2>
        </div>
        <span className="planner-count">{filteredTasks.length}</span>
      </div>

      <div className="planner-task-filters" aria-label="Maintenance request filters">
        <label>
          <span>Department</span>
          <select value={department} onChange={(event) => setDepartment(event.target.value)}>
            <option value="ALL">All</option>
            {departments.map((item) => (
              <option key={item} value={item}>
                {departmentLabel(item)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Section</span>
          <select value={section} onChange={(event) => setSection(event.target.value)}>
            <option value="ALL">All</option>
            {plannerSections.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Priority</span>
          <select value={priority} onChange={(event) => setPriority(event.target.value)}>
            <option value="ALL">All</option>
            {priorities.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="planner-task-table" aria-label="Maintenance requests">
        <div className="planner-task-table-head" aria-hidden="true">
          <span>Task</span>
          <span>Department</span>
          <span>Section</span>
          <span>Duration</span>
          <span>Priority</span>
        </div>

        <div className="planner-task-table-body">
          {filteredTasks.map((task) => {
            const taskPriority = priorityForTask(task);
            const selected = selectedTaskId === task.task_id;
            return (
              <button
                key={task.task_id}
                type="button"
                className={`planner-task-row ${selected ? "is-selected" : ""}`}
                aria-pressed={selected}
                onClick={() => onSelectTask(task)}
              >
                <span className="planner-task-name" data-label="Task">
                  <strong>{task.task_id}</strong>
                  <small>{task.task_type}</small>
                </span>
                <span data-label="Department">{departmentLabel(task.department)}</span>
                <span data-label="Section">{task.section_id}</span>
                <span data-label="Duration">{task.duration_minutes} min</span>
                <span
                  className={`planner-task-priority priority-${taskPriority.toLowerCase()}`}
                  data-label="Priority"
                >
                  {taskPriority}
                </span>
              </button>
            );
          })}
          {filteredTasks.length === 0 ? (
            <p className="planner-task-empty">No requests match these filters.</p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
