import { departmentLabel, sectionLabel } from "../../utils/planningLabels.js";

export default function IntegrationGains({ gains, territory, tasks }) {
  const taskById = new Map(tasks.map((task) => [task.task_id, task]));
  return (
    <section className="integration-analysis" aria-labelledby="integration-heading">
      <div className="analysis-section-heading">
        <span>Where the improvement came from</span>
        <h2 id="integration-heading">Shared cross-department possessions</h2>
        <p>Coordination gain compares individual setup/work/release reservations with the shared possession.</p>
      </div>
      <div className="integration-gain-list">
        {gains.map((gain) => (
          <article key={gain.block_id}>
            <div className="gain-heading">
              <div>
                <span>{gain.block_id}</span>
                <h3>{gain.departments.map(departmentLabel).join(" + ")}</h3>
              </div>
              <strong>{gain.coordination_gain_minutes} min coordinated</strong>
            </div>
            <p>{sectionLabel(territory, gain.section_id)} <small>{gain.section_id}</small></p>
            <ul>
              {gain.task_ids.map((taskId) => {
                const task = taskById.get(taskId);
                return <li key={taskId}><strong>{task?.task_type ?? taskId}</strong><span>{departmentLabel(task?.department)} · {taskId}</span></li>;
              })}
            </ul>
            <dl>
              <div><dt>Individual reservation total</dt><dd>{gain.individual_reservation_minutes} min</dd></div>
              <div><dt>Shared possession</dt><dd>{gain.shared_possession_minutes} min</dd></div>
              <div><dt>Coordination gain</dt><dd>{gain.coordination_gain_minutes} min</dd></div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}
