import {
  MapPin,
  Radio,
  Database,
  Clock,
  ShieldCheck,
  Activity
} from "lucide-react";

function formatTimestamp(timestamp) {
  if (!timestamp) return "Unavailable";

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "Unavailable";

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata"
  });
}

function isUsableValue(value) {
  return (
    value !== null &&
    value !== undefined &&
    String(value).trim() !== "" &&
    !["null", "undefined"].includes(String(value).trim().toLowerCase())
  );
}

function StationInfo({ data }) {
  if (!data) return null;

  const station = data.station || {};
  const summary = data.summary || {};

  // OpenAQ may not provide a city for every monitoring location.
  // Use the most specific available administrative labels.
  const locationParts = [
    station.locality,
    station.city,
    station.district,
    station.state
  ]
    .filter(isUsableValue)
    .map(value => String(value).trim());

  const locationLabel = [...new Set(locationParts)].length
    ? [...new Set(locationParts)].join(", ")
    : "Location details unavailable";

  const stationName =
    station.name || station.station_name || "Unnamed monitoring station";

  const coordinatesAvailable =
    isUsableValue(station.latitude) &&
    isUsableValue(station.longitude);

  const stationDetails = [
    {
      label: "Monitoring Station",
      value: stationName,
      icon: Radio
    },
    {
      label: "Location",
      value: locationLabel,
      icon: MapPin
    },
    {
      label: "Station ID",
      value: isUsableValue(data.station_id) ? data.station_id : "Unavailable",
      icon: Database
    },
    {
      label: "Data Provider",
      value: data.source || "Unavailable",
      icon: Activity
    },
    {
      label: "Coordinates",
      value: coordinatesAvailable
        ? `${station.latitude}, ${station.longitude}`
        : "Coordinates unavailable",
      icon: MapPin
    },
    {
      label: "Last Retrieved",
      value: formatTimestamp(data.retrieved_at),
      icon: Clock
    }
  ];

  const totalRecords = Number(summary.total_records);
  const hasRecordSummary = Number.isFinite(totalRecords);

  return (
    <section className="station-info-section">
      

      <div className="station-info-grid">
        {stationDetails.map(item => {
          const Icon = item.icon;

          return (
            <article className="station-info-card" key={item.label}>
              <div className="station-info-icon">
                <Icon size={19} />
              </div>

              <div>
                <span>{item.label}</span>
                <h4>{item.value ?? "Unavailable"}</h4>
              </div>
            </article>
          );
        })}
      </div>

      <div className="station-quality-summary">
        <div className="station-quality-icon">
          <ShieldCheck size={21} />
        </div>

        <div className="station-quality-content">
          <h4>Data Quality Summary</h4>
          <p>
            {summary.available_pollutants ?? 0} of{" "}
            {summary.expected_pollutants ?? 6} core pollutants available.
          </p>
          {hasRecordSummary && (
            <p>
              {totalRecords} sensor records: {summary.fresh ?? 0} fresh,{" "}
              {summary.delayed ?? 0} delayed, {summary.stale ?? 0} stale
              {Number(summary.invalid_future) > 0
                ? `, ${summary.invalid_future} with future timestamps`
                : ""}
              .
            </p>
          )}
        </div>

        <div className="station-quality-count">
          <strong>
            {summary.available_pollutants ?? 0}/
            {summary.expected_pollutants ?? 6}
          </strong>
          <span>Available</span>
        </div>
      </div>

      <p className="station-source-note">
        Measurements are supplied by {data.source || "the configured data provider"}.
        Retrieval time and observation time are different. Freshness counts
        describe the sensor records reported by the backend; they are not an
        AQI score or a measure of health risk.
      </p>
    </section>
  );
}

export default StationInfo;
