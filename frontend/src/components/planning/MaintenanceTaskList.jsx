import { useMemo, useState } from "react";
import {
  departmentLabel,
  priorityLabel,
  sectionLabel,
} from "../../utils/planningLabels.js";

const departments = ["ENGINEERING", "S&T", "TRD"];
const priorities = ["Critical", "High", "Normal"];

export default function MaintenanceTaskList({
  tasks,
  sections,
  territory,
  selectedSection,
  selectedTaskId,
  scheduledTaskIds,
  unscheduledTaskIds,
  onSelectSection,
  onSelectTask,
}) {
  const [department, setDepartment] = useState("ALL");
  const [priority, setPriority] = useState("ALL");

  const filteredTasks = useMemo(
    () =>
      tasks.filter((task) => {
        const departmentMatch = department === "ALL" || task.department === department;
        const priorityMatch = priority === "ALL" || priorityLabel(task) === priority;
        const sectionMatch = (task.section_ids?.length ? task.section_ids : [task.section_id]).includes(selectedSection);
        return sectionMatch && departmentMatch && priorityMatch;
      }),
    [department, priority, selectedSection, tasks],
  );

  return (
    <section className="planner-task-column" aria-labelledby="maintenance-heading">
      <div className="workspace-column-heading">
        <div>
          <span className="planner-kicker">Work queue · selected section</span>
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
              <option key={item} value={item}>{departmentLabel(item)}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Section</span>
          <select value={selectedSection} onChange={(event) => onSelectSection(event.target.value)}>
            {sections.map((item) => (
              <option key={item.section_id} value={item.section_id}>
                {sectionLabel(territory, item.section_id)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Priority</span>
          <select value={priority} onChange={(event) => setPriority(event.target.value)}>
            <option value="ALL">All</option>
            {priorities.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
      </div>

      <div className="planner-task-table" aria-label="Maintenance requests">
        <div className="planner-task-table-body">
          {filteredTasks.map((task) => {
            const taskPriority = priorityLabel(task);
            const selected = selectedTaskId === task.task_id;
            const unscheduled = unscheduledTaskIds.has(task.task_id);
            const scheduled = scheduledTaskIds.has(task.task_id);
            return (
              <button
                key={task.task_id}
                type="button"
                className={`planner-task-row ${selected ? "is-selected" : ""}`}
                aria-pressed={selected}
                onClick={() => onSelectTask(task)}
              >
                <span className="planner-task-name" data-label="Task">
                  <span className="planner-task-title-row">
                    <strong>{task.task_type}</strong>
                    {unscheduled ? <em className="task-plan-state is-unscheduled">Unscheduled</em> : null}
                    {scheduled ? <em className="task-plan-state is-scheduled">Scheduled</em> : null}
                  </span>
                  <small>{(task.section_ids?.length ? task.section_ids : [task.section_id]).map((id) => sectionLabel(territory, id)).join(" + ")} · {task.task_id}</small>
                </span>
                <span className="planner-task-meta" data-label="Department">{departmentLabel(task.department)}</span>
                <span className="planner-task-meta" data-label="Duration">{task.duration_minutes} min</span>
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
            <p className="planner-task-empty">No requests match this section and filter selection.</p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
