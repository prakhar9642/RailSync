export function isPublicTerritory(territory) {
  if (!territory) return false;
  if (territory.territory_id === "saktigarh_memari_public_demo") return true;
  if (Array.isArray(territory.provenance)) {
    return territory.provenance.some(
      (p) => (typeof p === "string" ? p : p?.label) === "PUBLIC_TIMETABLE_DERIVED"
    );
  }
  return false;
}

export function findExactProfileMatches(trains = [], profiles = []) {
  if (!trains?.length || !profiles?.length) return [];
  const trainIds = new Set(trains.map((t) => String(t.train_id)));
  return profiles.filter((p) => trainIds.has(String(p.train_id)));
}

export function effectiveRiskStatus(config, territory, exactMatches = []) {
  if (isPublicTerritory(territory)) {
    if (!exactMatches.length) return "Unavailable";
    const [train_id, section_id] = (config?.target ?? "").split("|");
    const [historical_train_id, historical_station_id] = (config?.profile ?? "").split("|");
    const hasComplete = Boolean(
      config?.mode === "ML_ASSISTED" && train_id && section_id && historical_train_id && historical_station_id
    );
    return hasComplete ? "Experimental" : "Off";
  }

  // Synthetic test fixture
  const [train_id, section_id] = (config?.target ?? "").split("|");
  const [historical_train_id, historical_station_id] = (config?.profile ?? "").split("|");
  const hasComplete = Boolean(
    config?.mode === "ML_ASSISTED" && train_id && section_id && historical_train_id && historical_station_id
  );
  return hasComplete ? "Experimental" : "Off";
}

export function riskOptions(config, territory) {
  if (territory && isPublicTerritory(territory)) {
    return {
      risk_mode: "STATIC",
      risk_profiles: [],
    };
  }
  const [train_id, section_id] = (config?.target ?? "").split("|");
  const [historical_train_id, historical_station_id] = (config?.profile ?? "").split("|");
  return {
    risk_mode: config?.mode ?? "STATIC",
    risk_profiles: config?.mode === "ML_ASSISTED" && train_id && section_id && historical_train_id && historical_station_id
      ? [{ train_id, section_id, historical_train_id, historical_station_id }] : [],
  };
}
