import { useEffect, useState, useMemo } from "react";
import { getMlStatus } from "../../services/api.js";
import { trainLabel, trainFullLabel, sectionLabel } from "../../utils/planningLabels.js";
import { isPublicTerritory, findExactProfileMatches, effectiveRiskStatus } from "../../utils/risk.js";
import "./risk.css";

export function RiskResult({ risk }) {
  if (!risk) return null;
  const isMl = risk.effective_mode === "ML_ASSISTED";
  return (
    <div className="risk-result">
      <div className="risk-result-header">
        <strong>Risk assistance: {isMl ? "Experimental" : "Off"}</strong>
      </div>
      <p>{risk.message}</p>
      {risk.predictions?.map((item) => (
        <p key={`${item.train_id}|${item.section_id}`}>
          {trainLabel(item.train_id)} · {item.section_id}: {item.expected_delay_minutes == null
            ? "Estimate unavailable" : `${item.expected_delay_minutes.toFixed(1)} min aggregate delay estimate · ${item.risk_level.toLowerCase()} risk`}
          {" · "}Explicit synthetic forecast experiment using public profile {item.historical_train_id} / {item.historical_station_id}.
        </p>
      ))}
    </div>
  );
}

export default function RiskControls({ config, onChange, trains, territory, disabled = false }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    getMlStatus({ signal: controller.signal })
      .then(setStatus)
      .catch((err) => {
        if (err.name !== "AbortError") setError(err);
      });
    return () => controller.abort();
  }, []);

  const isPublic = isPublicTerritory(territory);
  const exactMatches = useMemo(
    () => findExactProfileMatches(trains, status?.profiles ?? []),
    [trains, status?.profiles],
  );
  const statusValue = effectiveRiskStatus(config, territory, exactMatches);

  useEffect(() => {
    if (isPublic && exactMatches.length === 0 && config?.mode !== "STATIC") {
      onChange({ mode: "STATIC", target: "", profile: "" });
    }
  }, [isPublic, exactMatches.length, config?.mode, onChange]);

  const targets = useMemo(
    () => [...new Map(trains.map((row) => [`${row.train_id}|${row.section_id}`, row])).entries()],
    [trains],
  );
  const enabled = config?.mode === "ML_ASSISTED";

  const statusClass = statusValue === "Experimental"
    ? "is-experimental"
    : statusValue === "Unavailable"
    ? "is-unavailable"
    : "is-off";

  return (
    <div className="risk-section-wrapper">
      <div className="risk-status-indicator">
        <div className="risk-status-pill">
          <span className="risk-status-label">Risk assistance:</span>
          <strong className={`risk-status-value ${statusClass}`}>
            {statusValue}
          </strong>
        </div>
        <p className="risk-status-info">
          {statusValue === "Unavailable"
            ? "No matching historical profile is available for the services in this territory."
            : isPublic && exactMatches.length > 0
            ? `Historical risk profile available for ${exactMatches.map((m) => `Service ${m.train_id}`).join(", ")}.`
            : "Experimental historical aggregate-delay estimates may influence robustness preference. Hard feasibility constraints remain unchanged."}
        </p>
      </div>

      <details className="risk-controls" aria-label="Experimental ML configuration">
        <summary>
          <span>Advanced</span>
          <small>→ Experimental ML configuration</small>
        </summary>
        <div className="risk-advanced-body">
          <p>Estimates historical train–station average delay, not an individual future train run. Hard constraints and safety margins remain authoritative.</p>
          {status?.evaluation ? (
            <p className="risk-evaluation-note">
              Route-group holdout MAE {status.evaluation.model.mae_minutes.toFixed(1)} min · RMSE {status.evaluation.model.rmse_minutes.toFixed(1)} min
              {status.evaluation.mean_baseline
                ? ` (training-mean baseline: MAE ${status.evaluation.mean_baseline.mae_minutes.toFixed(1)} min · RMSE ${status.evaluation.mean_baseline.rmse_minutes.toFixed(1)} min)`
                : ""}. Substantial error; not validated for operational use.
            </p>
          ) : null}
          <p className="risk-model-status">
            {error ? "ML status unavailable; static planning remains available." : status ? `Model ${status.model_available ? "available" : "unavailable"}` : "Loading model status…"}
          </p>

          {isPublic ? (
            exactMatches.length === 0 ? (
              <div className="risk-public-status">
                <p>No matching historical profile is available for the services in this territory.</p>
              </div>
            ) : (
              <div className="risk-public-matches">
                <h4 className="risk-subsection-title">Historical risk profile</h4>
                <p className="risk-exact-match-note">
                  Historical risk profile available for {exactMatches.map((m) => `Service ${m.train_id} (${m.train_name})`).join(", ")}.
                </p>
                <label className="risk-toggle">
                  <input
                    type="checkbox"
                    checked={enabled}
                    disabled={disabled || !status?.model_available}
                    onChange={(event) => onChange({ ...config, mode: event.target.checked ? "ML_ASSISTED" : "STATIC" })}
                  />
                  Apply historical risk profile to matched services
                </label>
                {enabled ? (
                  <div className="risk-bindings">
                    <label>
                      Public service and section
                      <select
                        aria-label="Risk target train and section"
                        value={config?.target ?? ""}
                        disabled={disabled}
                        onChange={(event) => onChange({ ...config, target: event.target.value })}
                      >
                        <option value="">Choose explicitly</option>
                        {targets
                          .filter(([, row]) => exactMatches.some((m) => m.train_id === row.train_id))
                          .map(([key, row]) => (
                            <option key={key} value={key}>
                              {trainFullLabel(row.train_id, territory)} · {sectionLabel(territory, row.section_id)}
                            </option>
                          ))}
                      </select>
                    </label>
                    <label>
                      Historical delay profile
                      <select
                        aria-label="Public historical profile"
                        value={config?.profile ?? ""}
                        disabled={disabled}
                        onChange={(event) => onChange({ ...config, profile: event.target.value })}
                      >
                        <option value="">Choose explicitly</option>
                        {exactMatches.map((row) => (
                          <option key={`${row.train_id}|${row.station_code}`} value={`${row.train_id}|${row.station_code}`}>
                            {row.train_id} · {row.train_name} · {row.station_name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                ) : null}
              </div>
            )
          ) : (
            <div className="risk-fixture-section">
              <h4 className="risk-subsection-title">Experimental profile transfer</h4>
              <p className="risk-transfer-note">
                Transfers a public historical delay profile onto a synthetic train-section for scenario testing. The identities are unrelated and are never matched automatically.
              </p>
              <label className="risk-toggle">
                <input
                  type="checkbox"
                  checked={enabled}
                  disabled={disabled || !status?.model_available}
                  onChange={(event) => onChange({ ...config, mode: event.target.checked ? "ML_ASSISTED" : "STATIC" })}
                />
                Apply an experimental historical profile as a synthetic forecast scenario
              </label>
              {enabled ? (
                <div className="risk-bindings">
                  <label>
                    Synthetic train and section
                    <select
                      aria-label="Risk target train and section"
                      value={config?.target ?? ""}
                      disabled={disabled}
                      onChange={(event) => onChange({ ...config, target: event.target.value })}
                    >
                      <option value="">Choose explicitly</option>
                      {targets.map(([key, row]) => (
                        <option key={key} value={key}>
                          {trainFullLabel(row.train_id, territory)} · {sectionLabel(territory, row.section_id)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Historical delay profile
                    <select
                      aria-label="Public historical profile"
                      value={config?.profile ?? ""}
                      disabled={disabled}
                      onChange={(event) => onChange({ ...config, profile: event.target.value })}
                    >
                      <option value="">Choose explicitly</option>
                      {status?.profiles?.map((row) => (
                        <option key={`${row.train_id}|${row.station_code}`} value={`${row.train_id}|${row.station_code}`}>
                          {row.train_id} · {row.train_name} · {row.station_name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <p>These are separate identities. This explicit profile transfer has no demonstrated accuracy for the fictional corridor. Without both selections, planning stays static.</p>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </details>
    </div>
  );
}
