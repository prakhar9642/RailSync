export function riskOptions(config) {
  const [train_id, section_id] = (config.target ?? "").split("|");
  const [historical_train_id, historical_station_id] = (config.profile ?? "").split("|");
  return {
    risk_mode: config.mode,
    risk_profiles: config.mode === "ML_ASSISTED" && train_id && section_id && historical_train_id && historical_station_id
      ? [{ train_id, section_id, historical_train_id, historical_station_id }] : [],
  };
}
