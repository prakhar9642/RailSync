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

export function trainLabel(trainId, territory) {
  if (!trainId) return "";
  const canonical = canonicalTrainId(trainId);
  const service = territory?.train_services?.find((item) => item.train_id === trainId);
  if (service) return `${service.service_number} · ${service.service_name}`;
  const match = canonical.match(/^TR(?:10?|0?)(\d+)$/i);
  if (match) {
    const num = match[1].padStart(2, "0");
    return `Fixture Train ${num}`;
  }
  return canonical;
}

export function trainFullLabel(trainId, territory) {
  const human = trainLabel(trainId, territory);
  const canonical = canonicalTrainId(trainId);
  return human !== canonical ? `${human} (${canonical})` : canonical;
}

export function proofLabel(proofState) {
  if (proofState === "FULLY_OPTIMAL") return "Optimal solution";
  if (proofState === "FEASIBLE_BOUNDED") return "Valid bounded plan";
  return proofState ? proofState.replaceAll("_", " ").toLowerCase() : "Unavailable";
}

export function resourceStateLabel(state) {
  if (state === "PASSED") return "Passed";
  if (state === "FAILED") return "Failed";
  if (state === "UNKNOWN") return "Unconfirmed";
  if (state === "NOT_EVALUATED") return "Not evaluated";
  return "Unavailable";
}
export function territoryLabel(territory) {
  const names = {
    saktigarh_memari_public_demo: "Eastern · Saktigarh → Memari",
    western_hdn: "Western · Virar → Dahanu Road",
    delhi_agra: "Northern · Hazrat Nizamuddin → Palwal",
  };
  return names[territory?.territory_id] ?? territory?.display_name ?? "Corridor";
}
