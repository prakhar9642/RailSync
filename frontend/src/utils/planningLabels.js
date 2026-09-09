export function departmentLabel(department) {
  return department === "ENGINEERING" ? "Engineering" : department;
}

export function priorityLabel(task) {
  if (task.criticality >= 8) return "Critical";
  if (task.criticality >= 6) return "High";
  return "Normal";
}

export function sectionLabel(territory, sectionId) {
  const section = territory?.sections?.find((item) => item.section_id === sectionId);
  if (!section) return sectionId;
  const stationNames = new Map(
    territory.stations.map((station) => [station.station_id, station.station_name]),
  );
  return `${stationNames.get(section.from_station) ?? section.from_station} → ${
    stationNames.get(section.to_station) ?? section.to_station
  }`;
}

export function canonicalTrainId(trainId) {
  if (!trainId) return "";
  return trainId.replace(/^EHDN_/, "");
}

export function trainLabel(trainId, _territory) {
  if (!trainId) return "";
  const canonical = canonicalTrainId(trainId);
  const match = canonical.match(/^TR(?:10?|0?)(\d+)$/i);
  if (match) {
    const num = match[1].padStart(2, "0");
    return `Fixture Train ${num}`;
  }
  return canonical;
}

export function trainFullLabel(trainId, _territory) {
  const human = trainLabel(trainId, _territory);
  const canonical = canonicalTrainId(trainId);
  return human !== canonical ? `${human} (${canonical})` : canonical;
}

export function proofLabel(proofState) {
  if (proofState === "FULLY_OPTIMAL") return "Optimal plan proven";
  if (proofState === "FEASIBLE_BOUNDED") return "Valid bounded plan";
  return proofState ? proofState.replaceAll("_", " ").toLowerCase() : "Unavailable";
}

export function resourceStateLabel(state) {
  if (state === "PASSED") return "Passed";
  if (state === "FAILED") return "Failed";
  if (state === "UNKNOWN") return "Unknown";
  if (state === "NOT_EVALUATED") return "Not evaluated";
  return "Unavailable";
}
