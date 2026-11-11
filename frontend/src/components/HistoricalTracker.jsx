
import { useState, useEffect, useMemo, useCallback } from "react";

import {
  getStationHistory,
  getHistoricalAnalytics,
  getApiErrorMessage,
} from "../services/airwiseApi";

import {
  Search,
  RefreshCw,
  Activity,
  Clock,
  Database,
  AlertTriangle,
  BarChart3,
  Radio,
  CalendarDays
} from "lucide-react";



const POLLUTANTS = [
  { value: "pm25", label: "PM2.5" },
  { value: "pm10", label: "PM10" },
  { value: "no2", label: "NO₂" },
  { value: "so2", label: "SO₂" },
  { value: "co", label: "CO" },
  { value: "o3", label: "O₃" }
];

const CHART = {
  width: 900,
  height: 330,
  left: 72,
  right: 30,
  top: 28,
  bottom: 58
};

function formatNumber(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "N/A";
  }

  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2
  });
}

function formatDate(timestamp) {
  if (!timestamp) return "Unavailable";

  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) return "Invalid date";

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata"
  });
}

function freshnessClass(value) {
  const status = (value || "").toLowerCase();

  if (status === "fresh") return "history-fresh";
  if (status === "delayed") return "history-delayed";
  if (status === "stale") return "history-stale";

  return "history-unknown";
}

function StatCard({ label, value, unit, icon: Icon }) {
  return (
    <div className="history-stat-card">
      <div className="history-stat-top">
        <span>{label}</span>
        <Icon size={18} />
      </div>

      <strong>{value}</strong>

      <small>{unit}</small>
    </div>
  );
}


// --------------------------------------------------
// HISTORICAL SVG CHART
// --------------------------------------------------

function HistoricalChart({ records, unit }) {
  const validRecords = useMemo(() => {
    return records
      .filter(record => {
        const value = Number(record.value);
        const time = new Date(record.observed_at).getTime();

        return (
          record.value !== null &&
          record.value !== undefined &&
          record.value !== "" &&
          Number.isFinite(value) &&
          Number.isFinite(time)
        );
      })
      .sort(
        (a, b) =>
          new Date(a.observed_at).getTime() -
          new Date(b.observed_at).getTime()
      );
  }, [records]);

  if (validRecords.length === 0) {
    return (
      <div className="history-empty-chart">
        No valid historical observations are available.
      </div>
    );
  }

  const { width, height, left, right, top, bottom } = CHART;

  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;

  const values = validRecords.map(record => Number(record.value));

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);

  const range = maxValue - minValue;
  const padding = range === 0 ? Math.max(maxValue * 0.1, 1) : range * 0.15;

  const yMin = Math.max(0, minValue - padding);
  const yMax = maxValue + padding;

  const timestamps = validRecords.map(
    record => new Date(record.observed_at).getTime()
  );

  const minTime = Math.min(...timestamps);
  const maxTime = Math.max(...timestamps);

  const timeRange = maxTime - minTime;

  const xPosition = timestamp => {
    if (timeRange === 0) return left + plotWidth / 2;

    return left + ((timestamp - minTime) / timeRange) * plotWidth;
  };

  const yPosition = value => {
    if (yMax === yMin) return top + plotHeight / 2;

    return top + ((yMax - value) / (yMax - yMin)) * plotHeight;
  };

  const sensorGroups = {};

  validRecords.forEach(record => {
    const sensor = String(record.sensor_id ?? "unknown");

    if (!sensorGroups[sensor]) {
      sensorGroups[sensor] = [];
    }

    sensorGroups[sensor].push(record);
  });

  const yTicks = Array.from({ length: 5 }, (_, index) => {
    return yMin + ((yMax - yMin) * index) / 4;
  });

  const xLabels = [
    minTime,
    minTime + timeRange / 2,
    maxTime
  ];

  return (
    <div className="history-chart-wrapper">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="history-chart-svg"
        role="img"
        aria-label="Historical pollutant observations chart"
      >
        {yTicks.map((tick, index) => {
          const y = yPosition(tick);

          return (
            <g key={index}>
              <line
                x1={left}
                y1={y}
                x2={width - right}
                y2={y}
                stroke="#e4e7ec"
                strokeDasharray="4 4"
              />

              <text
                x={left - 12}
                y={y + 4}
                textAnchor="end"
                fontSize="11"
                fill="#667085"
              >
                {formatNumber(tick)}
              </text>
            </g>
          );
        })}

        <line
          x1={left}
          y1={top}
          x2={left}
          y2={height - bottom}
          stroke="#98a2b3"
        />

        <line
          x1={left}
          y1={height - bottom}
          x2={width - right}
          y2={height - bottom}
          stroke="#98a2b3"
        />

        {Object.entries(sensorGroups).map(([sensor, sensorRecords]) => {
          const points = sensorRecords
            .map(record => {
              const x = xPosition(
                new Date(record.observed_at).getTime()
              );

              const y = yPosition(Number(record.value));

              return `${x},${y}`;
            })
            .join(" ");

          return (
            <g key={sensor}>
              {sensorRecords.length > 1 && (
                <polyline
                  points={points}
                  fill="none"
                  stroke="#2563eb"
                  strokeWidth="2.5"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              )}

              {sensorRecords.map((record, index) => {
                const x = xPosition(
                  new Date(record.observed_at).getTime()
                );

                const y = yPosition(Number(record.value));

                return (
                  <g key={`${sensor}-${index}`}>
                    <circle
                      cx={x}
                      cy={y}
                      r="6"
                      fill="#2563eb"
                      stroke="#ffffff"
                      strokeWidth="2"
                    >
                      <title>
                        Sensor: {sensor}
                        {" | "}
                        Value: {record.value} {record.unit || unit}
                        {" | "}
                        Observed: {formatDate(record.observed_at)}
                        {" | "}
                        Freshness: {record.freshness}
                      </title>
                    </circle>
                  </g>
                );
              })}
            </g>
          );
        })}

        {xLabels.map((timestamp, index) => {
          const x = xPosition(timestamp);

          return (
            <text
              key={index}
              x={x}
              y={height - bottom + 24}
              textAnchor={
                index === 0
                  ? "start"
                  : index === 2
                    ? "end"
                    : "middle"
              }
              fontSize="10"
              fill="#667085"
            >
              {new Date(timestamp).toLocaleDateString("en-IN", {
                day: "2-digit",
                month: "short",
                year: "2-digit",
                timeZone: "Asia/Kolkata"
              })}
            </text>
          );
        })}

        <text
          x={18}
          y={height / 2}
          textAnchor="middle"
          fontSize="11"
          fill="#667085"
          transform={`rotate(-90 18 ${height / 2})`}
        >
          Concentration ({unit || "unit"})
        </text>
      </svg>

      <div className="history-chart-legend">
        {Object.entries(sensorGroups).map(([sensor, sensorRecords]) => (
          <div key={sensor}>
            <span className="history-legend-dot" />
            Sensor {sensor} ({sensorRecords.length} observations)
          </div>
        ))}
      </div>

      <p className="history-chart-note">
        Only fresh and delayed observations are plotted; stale records are excluded.
        Lines connect observations only within the same sensor. Missing time periods are not interpolated.
      </p>
    </div>
  );
}


// --------------------------------------------------
// MAIN HISTORICAL TRACKER
// --------------------------------------------------

export default function HistoricalTracker() {
  const [stationId, setStationId] = useState("6950");
  const [pollutant, setPollutant] = useState("pm25");
  const [limit, setLimit] = useState("100");

  const [history, setHistory] = useState(null);
  const [analytics, setAnalytics] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [lastFetched, setLastFetched] = useState(null);

  const fetchHistory = useCallback(async () => {
    const cleanStationId = stationId.trim();

    if (!/^\d+$/.test(cleanStationId)) {
      setError("Enter a valid numeric station ID.");
      setHistory(null);
      setAnalytics(null);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const [historyData, analyticsData] = await Promise.all([
        getStationHistory(cleanStationId, pollutant, Number(limit)),
        getHistoricalAnalytics(cleanStationId, pollutant, Number(limit))
      ]);

      if (!historyData || !Array.isArray(historyData.records)) {
        throw new Error("Historical API returned an invalid records list.");
      }

      setHistory(historyData);
      setAnalytics(analyticsData);
      setLastFetched(new Date());
    } catch (err) {
      console.error("Historical tracker error:", err);
      setError(getApiErrorMessage(err));
      setHistory(null);
      setAnalytics(null);
    } finally {
      setLoading(false);
    }
  }, [stationId, pollutant, limit]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const records = history?.records || [];

  // Exclude stale observations from the chart and the non-stale summary.
  // Freshness labels are supplied by the backend's configured data-quality rules.
  const nonStaleRecords = useMemo(
    () =>
      records.filter(record =>
        ["FRESH", "DELAYED"].includes(
          String(record.freshness || "").toUpperCase()
        )
      ),
    [records]
  );

  const nonStaleStatistics = useMemo(() => {
    const values = nonStaleRecords
      .filter(
        record =>
          record.value !== null &&
          record.value !== undefined &&
          record.value !== "" &&
          Number.isFinite(Number(record.value))
      )
      .map(record => Number(record.value))
      .sort((a, b) => a - b);

    if (values.length === 0) {
      return { count: 0, average: null, minimum: null, maximum: null, median: null };
    }

    const middle = Math.floor(values.length / 2);
    const median =
      values.length % 2 === 0
        ? (values[middle - 1] + values[middle]) / 2
        : values[middle];

    return {
      count: values.length,
      average: values.reduce((sum, value) => sum + value, 0) / values.length,
      minimum: values[0],
      maximum: values[values.length - 1],
      median
    };
  }, [nonStaleRecords]);

  const statistics = analytics?.analytics?.statistics || {};

  const sensorAnalysis = analytics?.analytics?.sensor_analysis || {};

  const freshnessCounts = useMemo(() => {
    return records.reduce(
      (counts, record) => {
        const status = (record.freshness || "").toUpperCase();

        if (status === "FRESH") counts.fresh += 1;
        else if (status === "DELAYED") counts.delayed += 1;
        else if (status === "STALE") counts.stale += 1;

        return counts;
      },
      { fresh: 0, delayed: 0, stale: 0 }
    );
  }, [records]);

  const anomalyStatus = useMemo(() => {
    const sensors = Object.values(sensorAnalysis);

    if (sensors.length === 0) return "unavailable";

    if (sensors.some(sensor =>
      sensor.spike_detection?.status === "success"
    )) {
      return "available";
    }

    if (sensors.every(sensor =>
      sensor.spike_detection?.status === "insufficient_data"
    )) {
      return "insufficient";
    }

    return "unavailable";
  }, [sensorAnalysis]);

  const unit = records.find(record => record.unit)?.unit || "unit";

  const pollutantLabel =
    POLLUTANTS.find(item => item.value === pollutant)?.label || pollutant;

  return (
    <section className="historical-tracker">

      {/* HEADER */}

      <div className="history-page-header">
        <div>
          <div className="history-eyebrow">
            HISTORICAL DATA INTELLIGENCE
          </div>

          <h2>Historical Pollution Tracker</h2>

          <p>
            Analyse stored ground-sensor observations and sensor-wise
            historical patterns.
          </p>
        </div>

        <span className="history-source-badge">
          <Database size={15} />
          OpenAQ observations
        </span>
      </div>


      {/* FILTERS */}

      <div className="history-filter-panel">

        <div className="history-filter-field">
          <label htmlFor="history-station-id">Station ID</label>

          <div className="history-input-wrapper">
            <Search size={16} />

            <input
              id="history-station-id"
              value={stationId}
              onChange={event => setStationId(event.target.value)}
              placeholder="Enter station ID"
              inputMode="numeric"
            />
          </div>
        </div>


        <div className="history-filter-field">
          <label htmlFor="history-pollutant">Pollutant</label>

          <select
            id="history-pollutant"
            value={pollutant}
            onChange={event => setPollutant(event.target.value)}
          >
            {POLLUTANTS.map(item => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>


        <div className="history-filter-field">
          <label htmlFor="history-limit">Record limit</label>

          <select
            id="history-limit"
            value={limit}
            onChange={event => setLimit(event.target.value)}
          >
            <option value="50">50 records</option>
            <option value="100">100 records</option>
            <option value="250">250 records</option>
            <option value="500">500 records</option>
          </select>
        </div>


        <button
          type="button"
          className="history-refresh-button"
          onClick={fetchHistory}
          disabled={loading}
        >
          <RefreshCw
            size={16}
            className={loading ? "history-spinning" : ""}
          />

          {loading ? "Loading..." : "Refresh data"}
        </button>

      </div>


      {/* ERROR */}

      {error && (
        <div className="history-error">
          <AlertTriangle size={18} />
          <span>{error}</span>

          <button type="button" onClick={fetchHistory}>
            Retry
          </button>
        </div>
      )}


      {/* LOADING */}

      {loading && (
        <div className="history-loading">
          <RefreshCw size={20} className="history-spinning" />
          Retrieving historical observations...
        </div>
      )}


      {!loading && history && (
        <>

          {/* STATION SUMMARY */}

          <div className="history-station-card">
            <div>
              <span>Selected monitoring station</span>

              <h3>{history.station?.name || `Station ${stationId}`}</h3>

              <p>
                {history.station?.city || "City unavailable"}
                {history.station?.state
                  ? `, ${history.station.state}`
                  : ""}
              </p>
            </div>

            <div className="history-station-meta">
              <span>Station ID</span>
              <strong>{history.station_id}</strong>
              <span>{pollutantLabel} historical data</span>
            </div>
          </div>


          {/* STATISTICS */}

          <div className="history-stat-grid">

            <StatCard
              label="All-record average"
              value={formatNumber(statistics.average)}
              unit={unit}
              icon={Activity}
            />

            <StatCard
              label="All-record maximum"
              value={formatNumber(statistics.maximum)}
              unit={unit}
              icon={BarChart3}
            />

            <StatCard
              label="All-record minimum"
              value={formatNumber(statistics.minimum)}
              unit={unit}
              icon={Radio}
            />

            <StatCard
              label="All-record median"
              value={formatNumber(statistics.median)}
              unit={unit}
              icon={CalendarDays}
            />

          </div>

          {/* NON-STALE RECORD SUMMARY */}
          <div className="history-panel">
            <div className="history-panel-header">
              <div>
                <h3>Non-stale observation summary</h3>
                <p>
                  Calculated from fresh and delayed records only; stale records are excluded.
                </p>
              </div>
              <Activity size={19} />
            </div>

            {nonStaleStatistics.count === 0 ? (
              <div className="history-empty-chart">
                No fresh or delayed observations are available for this summary.
              </div>
            ) : (
              <>
                <div className="history-stat-grid">
                  <StatCard
                    label="Non-stale average"
                    value={formatNumber(nonStaleStatistics.average)}
                    unit={unit}
                    icon={Activity}
                  />
                  <StatCard
                    label="Non-stale maximum"
                    value={formatNumber(nonStaleStatistics.maximum)}
                    unit={unit}
                    icon={BarChart3}
                  />
                  <StatCard
                    label="Non-stale minimum"
                    value={formatNumber(nonStaleStatistics.minimum)}
                    unit={unit}
                    icon={Radio}
                  />
                  <StatCard
                    label="Non-stale median"
                    value={formatNumber(nonStaleStatistics.median)}
                    unit={unit}
                    icon={CalendarDays}
                  />
                </div>
                <p className="history-data-note">
                  Based on {nonStaleStatistics.count} of {records.length} returned observations.
                  These are sensor concentrations, not an official CPCB AQI.
                </p>
              </>
            )}
          </div>


          {/* HISTORICAL CHART */}

          <div className="history-panel">

            <div className="history-panel-header">
              <div>
                <h3>{pollutantLabel} historical trend</h3>

                <p>
                  {nonStaleRecords.length} non-stale observations plotted ({records.length} total stored)
                </p>
              </div>

              <span className="history-unit-label">
                {unit}
              </span>
            </div>

            <HistoricalChart
              records={nonStaleRecords}
              unit={unit}
            />

          </div>


          {/* DATA QUALITY */}

          <div className="history-panel">

            <div className="history-panel-header">
              <div>
                <h3>Observation freshness</h3>

                <p>
                  Freshness status of returned historical records
                </p>
              </div>

              <Clock size={19} />
            </div>


            <div className="history-freshness-grid">

              <div className="history-quality-card">
                <span className="history-quality-dot fresh" />
                <span>Fresh</span>
                <strong>{freshnessCounts.fresh}</strong>
              </div>

              <div className="history-quality-card">
                <span className="history-quality-dot delayed" />
                <span>Delayed</span>
                <strong>{freshnessCounts.delayed}</strong>
              </div>

              <div className="history-quality-card">
                <span className="history-quality-dot stale" />
                <span>Stale</span>
                <strong>{freshnessCounts.stale}</strong>
              </div>

            </div>

          </div>

          {/* DATA COVERAGE */}
          <div className="history-panel">
            <div className="history-panel-header">
              <div>
                <h3>Data coverage & reliability</h3>
                <p>Coverage of the observations returned for this selection.</p>
              </div>
              <Database size={19} />
            </div>

            <div className="history-freshness-grid">
              <div className="history-quality-card">
                <span>Total observations</span>
                <strong>{records.length}</strong>
              </div>
              <div className="history-quality-card">
                <span>Distinct sensors</span>
                <strong>{Object.keys(sensorAnalysis).length}</strong>
              </div>
              <div className="history-quality-card">
                <span>Stale observations</span>
                <strong>{freshnessCounts.stale}</strong>
              </div>
              <div className="history-quality-card">
                <span>Delayed observations</span>
                <strong>{freshnessCounts.delayed}</strong>
              </div>
            </div>

            <p className="history-data-note">
              Spike detection: {anomalyStatus === "insufficient"
                ? "Insufficient data"
                : anomalyStatus === "available"
                  ? "Analysis available"
                  : "Unavailable"}.
              Sensor-level detection requires the configured minimum sample count per sensor.
            </p>
          </div>


          {/* SENSOR ANALYSIS */}

          <div className="history-panel">

            <div className="history-panel-header">
              <div>
                <h3>Sensor-wise anomaly analysis</h3>

                <p>
                  Each sensor is analysed independently.
                </p>
              </div>

              <Activity size={19} />
            </div>


            {anomalyStatus === "insufficient" && (
              <div className="history-warning">
                <AlertTriangle size={18} />

                <div>
                  <strong>Insufficient historical samples</strong>

                  <p>
                    Spike detection requires at least 8 observations
                    per sensor. No statistically confirmed spike
                    is available from the current records.
                  </p>
                </div>
              </div>
            )}


            <div className="history-sensor-list">

              {Object.entries(sensorAnalysis).map(([sensorId, sensor]) => (

                <div className="history-sensor-card" key={sensorId}>

                  <div>
                    <span>Sensor ID</span>
                    <strong>{sensorId}</strong>
                  </div>

                  <div>
                    <span>Observations</span>
                    <strong>{sensor.record_count}</strong>
                  </div>

                  <div>
                    <span>Required samples</span>
                    <strong>
                      {sensor.spike_detection?.required_samples ?? "N/A"}
                    </strong>
                  </div>

                  <div>
                    <span>Detection status</span>

                    <strong className="history-sensor-status">
                      {sensor.spike_detection?.status || "Unavailable"}
                    </strong>
                  </div>

                  <div className="history-sensor-dates">
                    <span>
                      First: {formatDate(sensor.first_observation)}
                    </span>

                    <span>
                      Last: {formatDate(sensor.last_observation)}
                    </span>
                  </div>

                </div>

              ))}

            </div>

            <p className="history-data-note">
              {analytics?.analytics?.data_note ||
                "Statistics describe only the returned observations."}
            </p>

          </div>


          {/* RECORD TABLE */}

          <div className="history-panel">

            <div className="history-panel-header">
              <div>
                <h3>Historical observations</h3>

                <p>
                  Actual records stored in the AIRWISE database
                </p>
              </div>

              <Database size={19} />
            </div>


            {records.length === 0 ? (

              <div className="history-empty-chart">
                No historical observations found for this selection.
              </div>

            ) : (

              <div className="history-table-wrapper">

                <table className="history-table">

                  <thead>
                    <tr>
                      <th>Observed at (IST)</th>
                      <th>Value</th>
                      <th>Sensor ID</th>
                      <th>Freshness</th>
                      <th>Source</th>
                    </tr>
                  </thead>

                  <tbody>
                    {records.map((record, index) => (

                      <tr key={`${record.sensor_id}-${record.observed_at}-${index}`}>

                        <td>{formatDate(record.observed_at)}</td>

                        <td>
                          <strong>{formatNumber(record.value)}</strong>
                          {" "}
                          {record.unit}
                        </td>

                        <td>{record.sensor_id}</td>

                        <td>
                          <span
                            className={`history-freshness-badge ${freshnessClass(record.freshness)}`}
                          >
                            {record.freshness || "UNKNOWN"}
                          </span>
                        </td>

                        <td>{record.source || "Unknown"}</td>

                      </tr>

                    ))}
                  </tbody>

                </table>

              </div>

            )}

          </div>


          {/* FOOTER */}

          <div className="history-footer">
            <span>
              Data type: {history.data_type || "Stored observations"}
            </span>

            <span>
              Last fetched:{" "}
              {lastFetched
                ? lastFetched.toLocaleTimeString()
                : "Unavailable"}
            </span>
          </div>


          <div className="history-disclaimer">
            <strong>Data integrity:</strong>{" "}
            Historical statistics describe only the records returned
            by the API. Observations from different sensors are not
            combined for anomaly detection. Gaps in the historical
            record are not interpolated. This chart does not represent
            a continuous air-quality measurement series.
          </div>

        </>
      )}

    </section>
  );
}
