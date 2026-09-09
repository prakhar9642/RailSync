import { useEffect, useState } from "react";
import { getMlStatus } from "../../services/api.js";
import { trainLabel, sectionLabel } from "../../utils/planningLabels.js";
import "./risk.css";

export function RiskResult({ risk }) {
  if (!risk) return null;
  return <div className="risk-result">
    <strong>Planning mode: {risk.effective_mode === "ML_ASSISTED" ? "Experimental ML assisted" : "Static"}</strong>
    <p>{risk.message}</p>
    {risk.predictions?.map((item) => <p key={`${item.train_id}|${item.section_id}`}>
      {item.train_id} · {item.section_id}: {item.expected_delay_minutes == null
        ? "Estimate unavailable" : `${item.expected_delay_minutes.toFixed(1)} min aggregate delay estimate · ${item.risk_level.toLowerCase()} risk`}
      {" · "}Explicit synthetic forecast experiment using public profile {item.historical_train_id} / {item.historical_station_id}.
    </p>)}
  </div>;
}

export default function RiskControls({ config, onChange, trains, territory, disabled = false }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    getMlStatus({ signal: controller.signal }).then(setStatus).catch((err) => {
      if (err.name !== "AbortError") setError(err);
    });
    return () => controller.abort();
  }, []);
  const targets = [...new Map(trains.map((row) => [`${row.train_id}|${row.section_id}`, row])).entries()];
  const enabled = config.mode === "ML_ASSISTED";
  return <details className="risk-controls">
    <summary>Experimental historical risk estimate <small>{enabled ? "Optional ML preference" : "Static mode"}</small></summary>
    <p>Estimates historical train–station average delay, not an individual future train run. Hard constraints and safety margins remain authoritative.</p>
    {status?.evaluation ? <p>Route-group holdout MAE {status.evaluation.model.mae_minutes.toFixed(1)} min · RMSE {status.evaluation.model.rmse_minutes.toFixed(1)} min. Substantial error; not validated for operational use.</p> : null}
    <p>{error ? "ML status unavailable; static planning remains available." : status ? `Model ${status.model_available ? "available" : "unavailable"}` : "Loading model status…"}</p>
    <label className="risk-toggle"><input type="checkbox" checked={enabled} disabled={disabled || !status?.model_available}
      onChange={(event) => onChange({ ...config, mode: event.target.checked ? "ML_ASSISTED" : "STATIC" })} />
      Apply an experimental historical profile as a synthetic forecast scenario</label>
    {enabled ? <div className="risk-bindings">
      <label>Fixture train and section<select aria-label="Risk target train and section" value={config.target ?? ""} disabled={disabled}
        onChange={(event) => onChange({ ...config, target: event.target.value })}>
        <option value="">Choose explicitly</option>
        {targets.map(([key,row]) => <option key={key} value={key}>{trainLabel(row.train_id, territory)} · {sectionLabel(territory,row.section_id)}</option>)}
      </select></label>
      <label>Public historical profile<select aria-label="Public historical profile" value={config.profile ?? ""} disabled={disabled}
        onChange={(event) => onChange({ ...config, profile: event.target.value })}>
        <option value="">Choose explicitly</option>
        {status?.profiles?.map((row) => <option key={`${row.train_id}|${row.station_code}`} value={`${row.train_id}|${row.station_code}`}>
          {row.train_id} · {row.train_name} · {row.station_name}
        </option>)}
      </select></label>
      <p>These are separate identities. This explicit profile transfer has no demonstrated accuracy for the fictional corridor. Without both selections, planning stays static.</p>
    </div> : null}
  </details>;
}
