
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  RefreshCw,
  ShieldAlert,
  Waves,
} from "lucide-react";

import {
  getSpikeAnalysis,
  getFlatlineAnalysis,
  getPollutionEvents,
  getApiErrorMessage,
} from "../services/airwiseApi";

import "./PollutionSpikeDetector.css";

const POLLUTANTS = [
  { value: "pm25", label: "PM2.5" },
  { value: "pm10", label: "PM10" },
  { value: "no2", label: "NO₂" },
  { value: "so2", label: "SO₂" },
  { value: "co", label: "CO" },
  { value: "o3", label: "O₃" },
];

function formatDate(value) {
  if (!value) return "Unavailable";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(date);
}

function formatConcentration(value, unit = "µg/m³") {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "Unavailable";
  }

  return `${Number(value).toFixed(2)} ${unit}`;
}

function formatDuration(minutes) {
  if (
    minutes === null ||
    minutes === undefined ||
    !Number.isFinite(Number(minutes))
  ) {
    return "Unavailable";
  }

  const totalMinutes = Math.max(0, Math.floor(Number(minutes)));
  const hours = Math.floor(totalMinutes / 60);
  const remainingMinutes = totalMinutes % 60;

  if (hours === 0) return `${remainingMinutes} min`;
  if (remainingMinutes === 0) return `${hours}h`;

  return `${hours}h ${remainingMinutes}m`;
}

function StatusPill({ status }) {
  const normalized = String(status || "unknown").toLowerCase();

  const label =
    normalized === "success"
      ? "Analysis completed"
      : normalized.replaceAll("_", " ");

  const className =
    normalized === "success" || normalized === "resolved"
      ? "psd-status psd-status--success"
      : normalized === "insufficient_data" ||
          normalized === "data_gap"
        ? "psd-status psd-status--warning"
        : normalized === "active"
          ? "psd-status psd-status--active"
          : "psd-status psd-status--neutral";

  return <span className={className}>{label}</span>;
}

function MetricCard({ icon: Icon, label, value, detail }) {
  return (
    <article className="psd-metric-card">
      <div className="psd-metric-top">
        <span>{label}</span>
        <Icon size={20} aria-hidden="true" />
      </div>

      <strong>{value}</strong>

      {detail && <small>{detail}</small>}
    </article>
  );
}

function EventMetric({ label, value }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PollutionEvents({ data, error, loading }) {
  if (loading) {
    return (
      <p className="psd-empty">
        Loading pollution event analysis...
      </p>
    );
  }

  if (error) {
    return (
      <div className="psd-alert psd-alert--error" role="alert">
        <AlertTriangle size={20} />
        <div>
          <strong>Unable to load pollution events</strong>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <p className="psd-empty">
        Pollution event data is not available for this selection.
      </p>
    );
  }

  const events = Array.isArray(data.events) ? data.events : [];
  const unit = data.unit || "µg/m³";

  return (
    <>
      <div className="psd-event-summary">
        <MetricCard
          icon={Activity}
          label="Event candidates"
          value={data.total_events ?? 0}
          detail="Detected by the event algorithm"
        />

        <MetricCard
          icon={CheckCircle2}
          label="Resolved events"
          value={data.resolved_events ?? 0}
          detail="Recovery criteria satisfied"
        />

        <MetricCard
          icon={AlertTriangle}
          label="Unresolved events"
          value={data.unresolved_events ?? 0}
          detail="Still active or unconfirmed"
        />

        <MetricCard
          icon={Waves}
          label="Surge triggers"
          value={data.surge_triggers ?? 0}
          detail="Detector trigger count"
        />
      </div>

      <div className="psd-event-meta">
        <span>
          Station: <strong>{data.station || "Unavailable"}</strong>
        </span>

        <span>
          Sensor ID: <strong>{data.sensor_id ?? "Unavailable"}</strong>
        </span>

        <span>
          Valid readings: <strong>{data.valid_observations ?? 0}</strong>
        </span>

        <span>
          Missing readings: <strong>{data.missing_observations ?? 0}</strong>
        </span>
      </div>

      {Number(data.missing_observations) > 0 && (
        <div className="psd-alert psd-alert--warning psd-event-gap">
          <AlertTriangle size={20} />
          <div>
            <strong>Historical observation gaps detected</strong>
            <p>
              {data.missing_observations} expected readings are missing.
              Interpret event duration and recovery timing with this
              data limitation in mind.
            </p>
          </div>
        </div>
      )}

      {events.length === 0 ? (
        <p className="psd-empty">
          No pollution event candidates were returned.
        </p>
      ) : (
        <div className="psd-event-list">
          {events.map((event) => (
            <article
              className="psd-event-card"
              key={event.event_id}
            >
              <div className="psd-event-heading">
                <div>
                  <span className="psd-muted-label">
                    Event #{event.event_id}
                  </span>
                  <h3>{formatDate(event.start)}</h3>
                </div>

                <StatusPill status={event.status} />
              </div>

              <div className="psd-event-stats">
                <EventMetric
                  label="Peak PM2.5"
                  value={formatConcentration(event.peak, unit)}
                />

                <EventMetric
                  label="Baseline"
                  value={formatConcentration(event.baseline, unit)}
                />

                <EventMetric
                  label="Increase"
                  value={
                    event.percentage_increase == null
                      ? "Unavailable"
                      : `${Number(event.percentage_increase).toFixed(2)}%`
                  }
                />

                <EventMetric
                  label="Duration"
                  value={formatDuration(event.duration_minutes)}
                />
              </div>

              <div className="psd-event-timeline">
                <p>
                  <span>Peak recorded:</span>{" "}
                  {formatDate(event.peak_time)}
                </p>

                <p>
                  <span>Last observation:</span>{" "}
                  {formatDate(event.last_valid_observation)}
                </p>

                <p>
                  <span>Recovery started:</span>{" "}
                  {formatDate(event.recovery_start)}
                </p>

                <p>
                  <span>Resolved at:</span>{" "}
                  {formatDate(event.resolved_at)}
                </p>
              </div>

              <div className="psd-event-foot">
                <span>
                  {event.valid_observations ?? 0} valid readings
                </span>

                <span>
                  {event.missing_observations ?? 0} missing readings
                </span>

                <span>
                  Recovery threshold:{" "}
                  {formatConcentration(event.recovery_threshold, unit)}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}

      <div className="psd-integrity-note">
        <ShieldAlert size={20} />
        <div>
          <strong>Event interpretation</strong>
          <p>
            These are algorithmically detected sensor-event candidates,
            not verified pollution incidents. Recovery uses experimental
            criteria and four consecutive 15-minute readings. This is
            not an official CPCB AQI assessment.
          </p>
        </div>
      </div>
    </>
  );
}


export default function PollutionSpikeDetector() {
  const [stationId, setStationId] = useState("6950");
  const [pollutant, setPollutant] = useState("pm25");
  const [limit, setLimit] = useState("100");

  const [spikeData, setSpikeData] = useState(null);
  const [flatlineData, setFlatlineData] = useState(null);
  const [eventData, setEventData] = useState(null);

  const [loading, setLoading] = useState(false);
  const [eventLoading, setEventLoading] = useState(false);

  const [error, setError] = useState("");
  const [eventError, setEventError] = useState("");

  const [lastFetched, setLastFetched] = useState(null);

  const fetchAnalysis = useCallback(async () => {
    const cleanId = stationId.trim();

    if (!/^\d+$/.test(cleanId)) {
      setError("Enter a valid numeric station ID.");
      return;
    }

    const numericLimit = Number(limit);

    if (![50, 100, 250, 500].includes(numericLimit)) {
      setError("Select a valid record limit.");
      return;
    }

    setLoading(true);
    setError("");
    setEventError("");

    setSpikeData(null);
    setFlatlineData(null);
    setEventData(null);

    const supportsEvents =
      cleanId === "6950" && pollutant === "pm25";

    setEventLoading(supportsEvents);

    try {
      const [spikes, flatlines] = await Promise.all([
        getSpikeAnalysis(cleanId, pollutant, numericLimit),
        getFlatlineAnalysis(cleanId, pollutant, numericLimit),
      ]);

      if (
        !spikes ||
        !spikes.sensor_analysis ||
        typeof spikes.sensor_analysis !== "object"
      ) {
        throw new Error(
          "Spike endpoint returned an unexpected response."
        );
      }

      if (
        !flatlines ||
        !flatlines.flatline_analysis ||
        typeof flatlines.flatline_analysis !== "object"
      ) {
        throw new Error(
          "Flatline endpoint returned an unexpected response."
        );
      }

      setSpikeData(spikes);
      setFlatlineData(flatlines);
      setLastFetched(new Date());

      // Event lifecycle API currently supports Jadavpur PM2.5 only.
      if (supportsEvents) {
        try {
          const events = await getPollutionEvents(
            cleanId,
            pollutant
          );

          if (!events || !Array.isArray(events.events)) {
            throw new Error(
              "Pollution event endpoint returned an unexpected response."
            );
          }

          setEventData(events);
        } catch (eventErr) {
          setEventError(getApiErrorMessage(eventErr));
        } finally {
          setEventLoading(false);
        }
      }
    } catch (err) {
      setError(getApiErrorMessage(err));

      setSpikeData(null);
      setFlatlineData(null);
      setEventData(null);
      setLastFetched(null);
    } finally {
      setLoading(false);
      setEventLoading(false);
    }
  }, [stationId, pollutant, limit]);

  useEffect(() => {
    fetchAnalysis();
  }, [fetchAnalysis]);

  const sensors = useMemo(() => {
    const spikeSensors = spikeData?.sensor_analysis || {};
    const flatlineSensors = flatlineData?.flatline_analysis || {};

    const ids = [
      ...new Set([
        ...Object.keys(spikeSensors),
        ...Object.keys(flatlineSensors),
      ]),
    ];

    return ids.map((sensorId) => ({
      sensorId,
      spike: spikeSensors[sensorId] || null,
      flatline: flatlineSensors[sensorId] || null,
    }));
  }, [spikeData, flatlineData]);

  const totalSamples = sensors.reduce(
    (sum, sensor) =>
      sum + (Number(sensor.spike?.record_count) || 0),
    0
  );

  const confirmedAnomalies = sensors.reduce(
    (sum, sensor) =>
      sum +
      (sensor.spike?.spike_detection?.anomalies?.length || 0),
    0
  );

  const insufficientSensors = sensors.filter(
    (sensor) =>
      sensor.spike?.spike_detection?.status === "insufficient_data" ||
      sensor.flatline?.status === "insufficient_data"
  ).length;

  const allInsufficient =
    sensors.length > 0 &&
    sensors.every(
      (sensor) =>
        sensor.spike?.spike_detection?.status === "insufficient_data" &&
        sensor.flatline?.status === "insufficient_data"
    );

  const supportsEvents =
    stationId.trim() === "6950" && pollutant === "pm25";

  return (
    <div className="psd-page">
      <header className="psd-page-header">
        <div>
          <span className="psd-eyebrow">
            AIRWISE 360° · ENVIRONMENTAL INTELLIGENCE
          </span>

          <h1>Pollution Spike Detective</h1>

          <p>
            Detect unusual pollutant behaviour, sensor flatlines
            and pollution event candidates using historical observations.
          </p>
        </div>

        <button
          className="psd-primary-button"
          type="button"
          onClick={fetchAnalysis}
          disabled={loading || eventLoading}
        >
          <RefreshCw
            size={17}
            className={loading || eventLoading ? "psd-spin" : ""}
          />

          {loading || eventLoading
            ? "Analysing..."
            : "Refresh analysis"}
        </button>
      </header>

      <section className="psd-panel psd-controls">
        <label>
          <span>Station ID</span>

          <input
            value={stationId}
            onChange={(event) => setStationId(event.target.value)}
            inputMode="numeric"
            placeholder="Enter station ID"
          />
        </label>

        <label>
          <span>Pollutant</span>

          <select
            value={pollutant}
            onChange={(event) => setPollutant(event.target.value)}
          >
            {POLLUTANTS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Record limit</span>

          <select
            value={limit}
            onChange={(event) => setLimit(event.target.value)}
          >
            <option value="50">50 records</option>
            <option value="100">100 records</option>
            <option value="250">250 records</option>
            <option value="500">500 records</option>
          </select>
        </label>
      </section>

      {error && (
        <div className="psd-alert psd-alert--error" role="alert">
          <AlertTriangle size={20} />

          <div>
            <strong>Unable to load analysis</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {loading && !spikeData && (
        <div className="psd-loading">
          Loading sensor-wise analysis...
        </div>
      )}

      {spikeData && flatlineData && (
        <>
          <section className="psd-source-strip">
            <span>
              <Database size={17} />
              Stored ground-sensor observations
            </span>

            <span>
              <Activity size={17} />
              Station ID: <strong>{spikeData.location_id}</strong>
            </span>

            <span>
              <Clock3 size={17} />
              {lastFetched
                ? `Fetched ${lastFetched.toLocaleTimeString("en-IN")}`
                : "Not refreshed yet"}
            </span>
          </section>

          <section className="psd-metrics-grid">
            <MetricCard
              icon={Database}
              label="Sensors analysed"
              value={sensors.length}
              detail="Separate sensor histories"
            />

            <MetricCard
              icon={Waves}
              label="Observations returned"
              value={totalSamples}
              detail="Across listed sensors"
            />

            <MetricCard
              icon={ShieldAlert}
              label="Detected anomalies"
              value={confirmedAnomalies}
              detail="Backend statistical flags"
            />

            <MetricCard
              icon={AlertTriangle}
              label="Insufficient-data sensors"
              value={insufficientSensors}
              detail="Below detection requirements"
            />
          </section>

          {allInsufficient && (
            <div className="psd-alert psd-alert--warning">
              <AlertTriangle size={21} />

              <div>
                <strong>Insufficient historical samples</strong>

                <p>
                  The current sensor histories do not meet the backend's
                  minimum sample requirements. No statistically
                  supported spike or flatline conclusion can be made.
                </p>
              </div>
            </div>
          )}

          <section className="psd-panel">
            <div className="psd-section-heading">
              <div>
                <h2>Pollution Event Intelligence</h2>

                <p>
                  Track surge candidates, peak concentration,
                  recovery and missing observations.
                </p>
              </div>

              <Activity size={22} />
            </div>

            {supportsEvents ? (
              <PollutionEvents
                data={eventData}
                error={eventError}
                loading={eventLoading}
              />
            ) : (
              <div className="psd-alert psd-alert--warning">
                <AlertTriangle size={20} />

                <div>
                  <strong>Limited event tracking coverage</strong>

                  <p>
                    Event lifecycle analysis currently supports
                    Jadavpur station ID 6950 and PM2.5 only.
                    Spike and flatline analysis remain available
                    for other supported selections.
                  </p>
                </div>
              </div>
            )}
            </section>



          <section className="psd-panel">
            <div className="psd-section-heading">
              <div>
                <h2>Sensor-wise anomaly analysis</h2>
                <p>
                  Each sensor is evaluated independently.
                  Observations from different sensors are not merged.
                </p>
              </div>

              <Activity size={22} />
            </div>

            {sensors.length === 0 ? (
              <p className="psd-empty">
                No sensor analysis records were returned.
              </p>
            ) : (
              <div className="psd-sensor-list">
                {sensors.map((sensor) => {
                  const sensorId = sensor.sensorId;

                  const spikeResult =
                    sensor.spike?.spike_detection || {};

                  const flatlineResult =
                    sensor.flatline?.flatline_detection ||
                    sensor.flatline || {};

                  const anomalies = Array.isArray(
                    spikeResult.anomalies
                  )
                    ? spikeResult.anomalies
                    : [];

                  const potentialSpikes = anomalies.filter(
                    (item) => item.type === "potential_spike"
                  );

                  const potentialDrops = anomalies.filter(
                    (item) => item.type === "potential_drop"
                  );

                  const highestAnomaly = anomalies.reduce(
                    (highest, item) => {
                      const value = Number(
                        item.value ?? item.observed_value
                      );

                      if (!Number.isFinite(value)) return highest;

                      if (!highest || value > highest.value) {
                        return { value, item };
                      }

                      return highest;
                    },
                    null
                  );

                  const latestAnomaly = anomalies.reduce(
                    (latest, item) => {
                      const timestamp =
                        item.observed_at || item.timestamp;

                      const time = timestamp
                        ? Date.parse(timestamp)
                        : NaN;

                      if (!Number.isFinite(time)) return latest;

                      if (!latest || time > latest.time) {
                        return { time, timestamp };
                      }

                      return latest;
                    },
                    null
                  );

                  const spikeStatus =
                    spikeResult.status || "unknown";

                  const flatlineDetected =
                    flatlineResult.flatline_detected ??
                    flatlineResult.detected ??
                    false;

                  const longestFlatline =
                    flatlineResult.longest_flatline ??
                    flatlineResult.longest_sequence ??
                    0;

                  return (
                    <article
                      className="psd-sensor-card"
                      key={sensorId}
                    >
                      <div className="psd-sensor-heading">
                        <div>
                          <span className="psd-muted-label">
                            Sensor ID
                          </span>

                          <h3>{sensorId}</h3>
                        </div>

                        <StatusPill status={spikeStatus} />
                      </div>

                      <div className="psd-sensor-stats">
                        <div>
                          <span>Observations</span>
                          <strong>
                            {sensor.spike?.record_count ?? 0}
                          </strong>
                        </div>

                        <div>
                          <span>Required samples</span>
                          <strong>
                            {spikeResult.required_samples ?? "—"}
                          </strong>
                        </div>

                        <div>
                          <span>Spike status</span>
                          <strong>{spikeStatus}</strong>
                        </div>

                        <div>
                          <span>Flatline status</span>
                          <strong>
                            {flatlineResult.status || "Unavailable"}
                          </strong>
                        </div>
                      </div>

                      <div className="psd-date-range">
                        <span>
                          First:{" "}
                          {formatDate(
                            sensor.spike?.first_observation
                          )}
                        </span>

                        <span>
                          Last:{" "}
                          {formatDate(
                            sensor.spike?.last_observation
                          )}
                        </span>
                      </div>

                      {spikeStatus === "insufficient_data" ? (
                        <div className="psd-alert psd-alert--warning">
                          <AlertTriangle size={19} />
                          <div>
                            <strong>Insufficient data</strong>
                            <p>
                              This sensor does not have enough
                              observations for reliable spike analysis.
                            </p>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="psd-anomaly-summary-heading">
                            <div>
                              <h4>Anomaly Intelligence Summary</h4>
                              <p>
                                Summary of statistical flags for this
                                sensor and selected record window.
                              </p>
                            </div>
                          </div>

                          <div className="psd-anomaly-summary-grid">
                            <div className="psd-anomaly-summary-card">
                              <span>Total flags</span>
                              <strong>{anomalies.length}</strong>
                            </div>

                            <div className="psd-anomaly-summary-card">
                              <span>Potential spikes</span>
                              <strong>{potentialSpikes.length}</strong>
                            </div>

                            <div className="psd-anomaly-summary-card">
                              <span>Potential drops</span>
                              <strong>{potentialDrops.length}</strong>
                            </div>

                            <div className="psd-anomaly-summary-card">
                              <span>Highest flagged value</span>
                              <strong>
                                {highestAnomaly
                                  ? `${highestAnomaly.value.toFixed(2)} µg/m³`
                                  : "Unavailable"}
                              </strong>
                            </div>

                            <div className="psd-anomaly-summary-card">
                              <span>Latest anomaly</span>
                              <strong className="psd-anomaly-summary-date">
                                {latestAnomaly
                                  ? formatDate(latestAnomaly.timestamp)
                                  : "Unavailable"}
                              </strong>
                            </div>
                          </div>

                          {anomalies.length === 0 ? (
                            <p className="psd-empty">
                              No statistical anomaly flags were returned
                              for this sensor and record window.
                            </p>
                          ) : (
                            <div className="psd-anomaly-list">
                              <div className="psd-anomaly-header">
                                <strong>Detected anomalies</strong>
                                <span>
                                  {anomalies.length} statistical flags
                                </span>
                              </div>

                              {anomalies.map((anomaly, index) => {
                                const anomalyType = String(
                                  anomaly.type || "anomaly"
                                ).toLowerCase();

                                const isSpike =
                                  anomalyType === "potential_spike";

                                const isDrop =
                                  anomalyType === "potential_drop";

                                const rawValue =
                                  anomaly.value ??
                                  anomaly.observed_value;

                                const numericValue = Number(rawValue);

                                const displayedValue =
                                  rawValue === null ||
                                  rawValue === undefined ||
                                  !Number.isFinite(numericValue)
                                    ? "Unavailable"
                                    : numericValue.toFixed(2);

                                return (
                                  <div
                                    className="psd-anomaly-row"
                                    key={`${sensorId}-${anomaly.index ?? index}`}
                                  >
                                    <div className="psd-anomaly-info">
                                      <span className="psd-anomaly-time">
                                        {formatDate(
                                          anomaly.observed_at ||
                                          anomaly.timestamp
                                        )}
                                      </span>

                                      <span className="psd-anomaly-type">
                                        {isSpike
                                          ? "Potential spike"
                                          : isDrop
                                            ? "Potential drop"
                                            : "Statistical anomaly"}
                                      </span>
                                    </div>

                                    <div className="psd-anomaly-value">
                                      <strong>{displayedValue}</strong>

                                      {displayedValue !== "Unavailable" && (
                                        <span>µg/m³</span>
                                      )}
                                    </div>

                                    <span
                                      className={`psd-anomaly-badge ${
                                        isSpike
                                          ? "psd-anomaly-badge--spike"
                                          : isDrop
                                            ? "psd-anomaly-badge--drop"
                                            : "psd-anomaly-badge--other"
                                      }`}
                                    >
                                      {isSpike
                                        ? "Spike"
                                        : isDrop
                                          ? "Drop"
                                          : "Flag"}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </>
                      )}

                      <div className="psd-flatline-row">
                        <span>
                          Flatline detected:{" "}
                          <strong
                            className={
                              flatlineDetected
                                ? "psd-detected"
                                : "psd-not-detected"
                            }
                          >
                            {flatlineDetected ? "Yes" : "No"}
                          </strong>
                        </span>

                        <span>
                          Longest flatline:{" "}
                          <strong>{longestFlatline} readings</strong>
                        </span>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>

          <div className="psd-integrity-note">
            <ShieldAlert size={20} />

            <div>
              <strong>Statistical interpretation</strong>
              <p>
                Anomaly flags indicate unusual observations relative
                to the selected sensor's historical window. They are
                not confirmed pollution incidents or official CPCB
                AQI classifications. Missing observations can affect
                the interpretation of time-series patterns.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

