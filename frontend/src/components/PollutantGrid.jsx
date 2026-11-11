import {
  Wind,
  Activity,
  Cloud,
  Flame,
  Droplets,
  Sun
} from "lucide-react";

const pollutants = [
  { key: "pm25", name: "PM2.5", description: "Fine particulate matter", icon: Wind },
  { key: "pm10", name: "PM10", description: "Coarse particulate matter", icon: Activity },
  { key: "no2", name: "NO₂", description: "Nitrogen dioxide", icon: Cloud },
  { key: "so2", name: "SO₂", description: "Sulphur dioxide", icon: Flame },
  { key: "co", name: "CO", description: "Carbon monoxide", icon: Droplets },
  { key: "o3", name: "O₃", description: "Ground-level ozone", icon: Sun }
];

function formatTimestamp(timestamp) {
  if (!timestamp) return "Time unavailable";

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "Time unavailable";

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata"
  });
}

function normalizeFreshness(status) {
  if (!status || typeof status !== "string") return "UNKNOWN";

  const normalized = status.trim().toUpperCase().replace(/[\s-]+/g, "_");

  const labels = {
    FRESH: "FRESH",
    DELAYED: "DELAYED",
    STALE: "STALE",
    INVALID_FUTURE: "INVALID FUTURE",
    UNKNOWN: "STATUS UNKNOWN"
  };

  return labels[normalized] || "STATUS UNKNOWN";
}

function getLocationLabel(station = {}) {
  const parts = [
    station.locality,
    station.city,
    station.district,
    station.state
  ]
    .filter(value =>
      value !== null &&
      value !== undefined &&
      String(value).trim() !== "" &&
      !["null", "undefined"].includes(String(value).trim().toLowerCase())
    )
    .map(value => String(value).trim());

  return [...new Set(parts)].join(", ") || "Location details unavailable";
}

function PollutantGrid({ data, loading, error }) {
  const selectedPollutants = data?.pollutants || {};
  const station = data?.station || {};

  // Only the six displayed core pollutant readings are used for this
  // card-level breakdown. Backend freshness labels remain authoritative.
  const availableRecords = pollutants
    .map(pollutant => selectedPollutants[pollutant.key])
    .filter(Boolean);

  const freshnessCounts = availableRecords.reduce((counts, record) => {
    const status = normalizeFreshness(record?.freshness);
    counts[status] = (counts[status] || 0) + 1;
    return counts;
  }, {});

  const distinctStatuses = Object.keys(freshnessCounts);

  const overallStatus =
    availableRecords.length === 0
      ? "DATA UNAVAILABLE"
      : distinctStatuses.length > 1
        ? "MIXED SENSOR DATA"
        : distinctStatuses[0] === "UNKNOWN"
          ? "FRESHNESS UNKNOWN"
          : `${distinctStatuses[0]} SENSOR DATA`;

  return (
    <section className="pollutant-section">
      <div className="section-header">
        <div>
          <h3>Pollutant Intelligence</h3>
          <p>Atmospheric pollutant monitoring indicators</p>
        </div>
        <span className="data-status">
          {loading ? "FETCHING DATA" : error ? "API ERROR" : overallStatus}
        </span>
      </div>

      {error && (
        <div className="data-notice" role="alert">
          <p>Unable to load station measurements: {error}</p>
        </div>
      )}

      <div className="pollutant-grid">
        {pollutants.map(pollutant => {
          const Icon = pollutant.icon;
          const record = selectedPollutants[pollutant.key];
          const numericValue =
            record?.value !== null &&
            record?.value !== undefined &&
            Number.isFinite(Number(record.value));

          const freshness = record
            ? normalizeFreshness(record.freshness)
            : "UNAVAILABLE";

          return (
            <article className="pollutant-card" key={pollutant.key}>
              <div className="pollutant-card-top">
                <div className="pollutant-icon">
                  <Icon size={20} />
                </div>
                <span className="pollutant-indicator">
                  {loading ? "LOADING" : freshness}
                </span>
              </div>

              <h3>{pollutant.name}</h3>
              <p>{pollutant.description}</p>

              <div className="pollutant-value">
                {loading
                  ? "..."
                  : numericValue
                    ? Number(record.value).toLocaleString("en-IN", {
                        maximumFractionDigits: 2
                      })
                    : "--"}
                <span>{record?.unit || ""}</span>
              </div>

              <div className="pollutant-footer">
                {record
                  ? `Observed: ${formatTimestamp(record.timestamp)}`
                  : loading
                    ? "Fetching measurement..."
                    : "Measurement unavailable"}
              </div>
            </article>
          );
        })}
      </div>

      {data && (
        <div className="data-notice">
          <p>
            <strong>Core pollutant reading status:</strong>{" "}
            {Object.entries(freshnessCounts).length > 0
              ? Object.entries(freshnessCounts)
                  .map(([status, count]) => `${status}: ${count}`)
                  .join(" · ")
              : "No freshness labels supplied by the source"}
          </p>
          <p>
            Source: {data.source || "Source unavailable"} | Station:{" "}
            {station.name || "Station name unavailable"} | Location:{" "}
            {getLocationLabel(station)} | Data type:{" "}
            {data.data_type || "Ground sensor observations"}. Values retain
            their original measurement units. A missing freshness label is
            shown as unknown, not assumed to be fresh or delayed.
          </p>
        </div>
      )}
    </section>
  );
}

export default PollutantGrid;
