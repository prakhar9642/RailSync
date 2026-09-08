export function timestampValue(timestamp) {
  return new Date(timestamp).getTime();
}

export function timeLabel(timestamp) {
  return timestamp?.split("T")[1]?.slice(0, 5) ?? "";
}

export function dateLabel(timestamp) {
  if (!timestamp) return "Planning horizon";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(timestamp));
}

export function durationMinutes(startTime, endTime) {
  return Math.round((timestampValue(endTime) - timestampValue(startTime)) / 60_000);
}

export function buildTicks(horizon) {
  if (!horizon) return [];
  const start = timestampValue(horizon.start_time);
  const end = timestampValue(horizon.end_time);
  const hours = Math.max(1, Math.round((end - start) / 3_600_000));
  return Array.from({ length: hours + 1 }, (_, index) => {
    const timestamp = new Date(start + ((end - start) * index) / hours);
    return {
      key: timestamp.toISOString(),
      label: timestamp.toTimeString().slice(0, 5),
      left: `${(index / hours) * 100}%`,
    };
  });
}

export function rangeStyle(startTime, endTime, horizon) {
  const horizonStart = timestampValue(horizon.start_time);
  const horizonEnd = timestampValue(horizon.end_time);
  const duration = horizonEnd - horizonStart;
  const start = Math.max(horizonStart, timestampValue(startTime));
  const end = Math.min(horizonEnd, timestampValue(endTime));
  return {
    left: `${((start - horizonStart) / duration) * 100}%`,
    width: `${(Math.max(0, end - start) / duration) * 100}%`,
  };
}
