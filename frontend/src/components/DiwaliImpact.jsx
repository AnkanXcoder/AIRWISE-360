
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  CalendarDays,
  RefreshCw,
  MapPin,
  Database,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  ShieldCheck,
} from "lucide-react";

import {
  getDiwaliImpact,
  getApiErrorMessage,
} from "../services/airwiseApi";

import "./DiwaliImpact.css";

const DEFAULT_START = "2026-11-08";
const DEFAULT_END = "2026-11-08";

const PERIODS = [
  {
    key: "pre_diwali",
    title: "Pre-Diwali",
    subtitle: "7 days before event",
  },
  {
    key: "during_diwali",
    title: "During Diwali",
    subtitle: "Festival event window",
  },
  {
    key: "post_diwali",
    title: "Post-Diwali",
    subtitle: "7 days after event",
  },
];

function formatNumber(value) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "Unavailable";
  }

  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });
}

function formatPercentage(value) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "Not calculated";
  }

  const number = Number(value);

  return `${number > 0 ? "+" : ""}${number.toFixed(2)}%`;
}

function CoverageBadge({ sufficient }) {
  return sufficient ? (
    <span className="diwali-badge diwali-badge--good">
      <CheckCircle2 size={14} />
      Sufficient coverage
    </span>
  ) : (
    <span className="diwali-badge diwali-badge--warning">
      <AlertTriangle size={14} />
      Insufficient coverage
    </span>
  );
}

function PeriodCard({ period }) {
  const stats = period?.statistics;

  const metrics = [
    ["Mean", stats?.mean],
    ["Median", stats?.median],
    ["Minimum", stats?.minimum],
    ["Maximum", stats?.maximum],
  ];

  return (
    <article className="diwali-period-card">
      <div className="diwali-period-head">
        <div>
          <h3>{period.title}</h3>
          <p>{period.subtitle}</p>
        </div>

        <CoverageBadge
          sufficient={period.coverage_sufficient === true}
        />
      </div>

      <div className="diwali-period-metrics">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{formatNumber(value)}</strong>
            <small>µg/m³</small>
          </div>
        ))}
      </div>

      <div className="diwali-coverage-line">
        <span>
          {period.start_date || "—"} to {period.end_date || "—"}
        </span>

        <strong>
          {formatNumber(period.record_count ?? 0)} records ·{" "}
          {formatNumber(period.observation_days ?? 0)} observation days
        </strong>
      </div>

      {period.coverage_message && (
        <p className="diwali-coverage-message">
          {period.coverage_message}
        </p>
      )}
    </article>
  );
}

function UnavailableCity({ message }) {
  return (
    <div className="diwali-empty" role="status">
      <AlertTriangle size={22} />

      <div>
        <strong>Monitoring location unavailable</strong>

        <p>
          {message ||
            "No verified monitoring location is configured for this city."}
        </p>

        <p>
          Period comparisons cannot be generated until verified
          monitoring data becomes available.
        </p>
      </div>
    </div>
  );
}

export default function DiwaliImpact() {
  const [diwaliStart, setDiwaliStart] = useState(DEFAULT_START);
  const [diwaliEnd, setDiwaliEnd] = useState(DEFAULT_END);

  const [selectedCity, setSelectedCity] = useState("");

  const [payload, setPayload] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [lastFetched, setLastFetched] = useState(null);

  const loadReport = useCallback(async () => {
    if (!diwaliStart || !diwaliEnd) {
      setError("Select both event dates.");
      return;
    }

    if (diwaliEnd < diwaliStart) {
      setError(
        "Event end date cannot be earlier than start date."
      );
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await getDiwaliImpact({
        diwali_start: diwaliStart,
        diwali_end: diwaliEnd,
      });

      // Validate the API response before using it.
      if (
        !result ||
        !result.cities ||
        typeof result.cities !== "object" ||
        Array.isArray(result.cities)
      ) {
        throw new Error(
          "Unexpected Diwali analytics response."
        );
      }

      const cityNames = Object.keys(result.cities);

      if (cityNames.length === 0) {
        throw new Error(
          "No monitoring cities were returned by the API."
        );
      }

      setPayload(result);

      setSelectedCity((current) =>
        current && result.cities[current]
          ? current
          : cityNames[0]
      );

      setLastFetched(new Date());
    } catch (err) {
      setPayload(null);
      setError(getApiErrorMessage(err));
      setLastFetched(null);
    } finally {
      setLoading(false);
    }
  }, [diwaliStart, diwaliEnd]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const cityNames = useMemo(
    () => Object.keys(payload?.cities || {}),
    [payload]
  );

  const cityReport =
    payload?.cities?.[selectedCity] || null;

  const periods = useMemo(
    () =>
      PERIODS.map((item) => ({
        ...item,
        ...(cityReport?.periods?.[item.key] || {}),
      })),
    [cityReport]
  );

  const sufficientPeriods = periods.filter(
    (period) => period.coverage_sufficient === true
  ).length;

  const totalRecords = periods.reduce(
    (sum, period) =>
      sum + (Number(period.record_count) || 0),
    0
  );

  const comparisons = cityReport?.comparisons || {};

  const cityUnavailable =
    cityReport?.status === "unavailable";

  const reportStatus =
    cityReport?.status || "unknown";

  const selectedSensorRecords =
    cityReport?.records_for_selected_sensor;

  return (
    <div className="diwali-page">

      {/* PAGE HEADER */}

      <header className="diwali-header">
        <div>
          <span className="diwali-eyebrow">
            AIRWISE 360° · EVENT INTELLIGENCE
          </span>

          <h1>Diwali Impact Intelligence</h1>

          <p>
            Compare historical pollutant observations before,
            during and after the Diwali event window.
          </p>
        </div>

        <button
          className="diwali-refresh"
          type="button"
          onClick={loadReport}
          disabled={loading}
        >
          <RefreshCw
            size={17}
            className={loading ? "diwali-spin" : ""}
          />

          {loading ? "Loading report..." : "Refresh report"}
        </button>
      </header>

      {/* DATE AND CITY CONTROLS */}

      <section className="diwali-panel diwali-controls">

        <label>
          <span>
            <CalendarDays size={16} />
            Diwali start date
          </span>

          <input
            type="date"
            value={diwaliStart}
            onChange={(event) =>
              setDiwaliStart(event.target.value)
            }
          />
        </label>

        <label>
          <span>
            <CalendarDays size={16} />
            Diwali end date
          </span>

          <input
            type="date"
            value={diwaliEnd}
            onChange={(event) =>
              setDiwaliEnd(event.target.value)
            }
          />
        </label>

        <label>
          <span>
            <MapPin size={16} />
            Monitoring city
          </span>

          <select
            value={selectedCity}
            onChange={(event) =>
              setSelectedCity(event.target.value)
            }
            disabled={!cityNames.length}
          >
            {cityNames.length ? (
              cityNames.map((city) => (
                <option key={city} value={city}>
                  {city}
                </option>
              ))
            ) : (
              <option value="">
                No cities returned
              </option>
            )}
          </select>
        </label>

        <button
          className="diwali-apply"
          type="button"
          onClick={loadReport}
          disabled={loading}
        >
          Apply dates
        </button>

      </section>

      {/* ERROR */}

      {error && (
        <div
          className="diwali-alert diwali-alert--error"
          role="alert"
        >
          <AlertTriangle size={20} />

          <div>
            <strong>Unable to load Diwali report</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* LOADING */}

      {loading && !payload && (
        <div className="diwali-loading">
          Loading historical event analysis...
        </div>
      )}

      {/* REPORT */}

      {payload && cityReport && (
        <>

          {/* SOURCE INFORMATION */}

          <section className="diwali-source-strip">

            <span>
              <Database size={17} />

              Source:{" "}
              <strong>
                {payload.data_type ||
                  "Historical sensor observations"}
              </strong>
            </span>

            <span>
              <MapPin size={17} />

              City: <strong>{selectedCity}</strong>
            </span>

            <span>
              <CalendarDays size={17} />

              Event:{" "}
              <strong>
                {payload.event_window?.start} to{" "}
                {payload.event_window?.end}
              </strong>
            </span>

            <span>
              Pollutant:{" "}
              <strong>
                {payload.pollutant?.toUpperCase() || "PM2.5"}
              </strong>
            </span>

            <span>
              Sensor records:{" "}
              <strong>
                {selectedSensorRecords == null
                  ? "Unavailable"
                  : formatNumber(selectedSensorRecords)}
              </strong>
            </span>

          </section>

          {/* SUMMARY CARDS */}

          <section className="diwali-summary-grid">

            <article className="diwali-summary-card">
              <span>City report status</span>

              <strong className="diwali-summary-status">
                {String(reportStatus).replaceAll("_", " ")}
              </strong>

              <small>
                {selectedCity} monitoring location
              </small>
            </article>

            <article className="diwali-summary-card">
              <span>Total observations</span>

              <strong>
                {formatNumber(totalRecords)}
              </strong>

              <small>
                Across all three periods
              </small>
            </article>

            <article className="diwali-summary-card">
              <span>Periods with sufficient coverage</span>

              <strong>
                {cityUnavailable
                  ? "Unavailable"
                  : `${sufficientPeriods}/3`}
              </strong>

              <small>
                Based on backend coverage rules
              </small>
            </article>

            <article className="diwali-summary-card">
              <span>Monitoring location ID</span>

              <strong>
                {cityReport.location_id ?? "Unavailable"}
              </strong>

              <small>
                {cityReport.sensor_id
                  ? `Selected sensor ${cityReport.sensor_id}`
                  : "No configured sensor"}
              </small>
            </article>

          </section>

          {/* COVERAGE WARNING */}

          {!cityUnavailable &&
            cityReport.status !== "success" && (
              <div className="diwali-alert diwali-alert--warning">
                <AlertTriangle size={21} />

                <div>
                  <strong>
                    Insufficient historical coverage
                  </strong>

                  <p>
                    {cityReport.message ||
                      "One or more event periods do not meet the minimum record and observation-day requirements. Percentage comparisons are withheld."}
                  </p>
                </div>
              </div>
            )}

          {/* THREE-PERIOD COMPARISON */}

          <section className="diwali-panel">

            <div className="diwali-section-heading">
              <div>
                <h2>
                  Three-period pollutant comparison
                </h2>

                <p>
                  Historical {payload.pollutant || "PM2.5"}{" "}
                  observations · {payload.unit || "µg/m³"}
                </p>
              </div>

              <TrendingUp size={22} />
            </div>

            {cityUnavailable ? (
              <UnavailableCity
                message={cityReport.message}
              />
            ) : (
              <div className="diwali-period-grid">
                {periods.map((period) => (
                  <PeriodCard
                    key={period.key}
                    period={period}
                  />
                ))}
              </div>
            )}

          </section>

          {/* PERIOD COMPARISON */}

          <section className="diwali-panel">

            <div className="diwali-section-heading">
              <div>
                <h2>Period-to-period change</h2>

                <p>
                  Percentage changes are shown only when
                  the backend confirms adequate coverage.
                </p>
              </div>

              <TrendingUp size={22} />
            </div>

            {cityUnavailable ? (
              <UnavailableCity
                message={cityReport.message}
              />
            ) : (
              <>
                <div className="diwali-comparison-grid">

                  <article>
                    <span>
                      During vs pre-Diwali
                    </span>

                    <strong>
                      {formatPercentage(
                        comparisons.during_vs_pre_percent
                      )}
                    </strong>
                  </article>

                  <article>
                    <span>
                      Post vs pre-Diwali
                    </span>

                    <strong>
                      {formatPercentage(
                        comparisons.post_vs_pre_percent
                      )}
                    </strong>
                  </article>

                </div>

                <p className="diwali-explanation">
                  {cityReport.interpretation ||
                    "Period comparisons are descriptive and do not establish causation."}
                </p>
              </>
            )}

          </section>

          {/* DATA INTEGRITY */}

          <section className="diwali-integrity">

            <ShieldCheck size={21} />

            <div>
              <strong>
                Methodology and data integrity
              </strong>

              <p>
                {payload.methodology_note ||
                  "This report uses historical observations from the selected monitoring sensor. Missing periods are not estimated."}
              </p>

              <p>
                Minimum configured coverage:{" "}
                {payload.configuration
                  ?.minimum_records_per_period ?? "—"}{" "}
                records and{" "}
                {payload.configuration
                  ?.minimum_observation_days_per_period ?? "—"}{" "}
                distinct observation days per period.
              </p>

              <p>
                Results describe temporal association, not
                proof that Diwali activities caused a change
                in pollution. Insufficient periods are excluded
                from percentage comparisons.
              </p>

              {lastFetched && (
                <small>
                  Last fetched:{" "}
                  {lastFetched.toLocaleString("en-IN")}
                </small>
              )}
            </div>

          </section>

        </>
      )}

      {/* NO CITY REPORT */}

      {payload && !cityReport && (
        <div className="diwali-empty">
          <AlertTriangle size={20} />

          <div>
            <strong>City report unavailable</strong>
            <p>
              No report was returned for the selected city.
              Please select another monitoring city.
            </p>
          </div>
        </div>
      )}

    </div>
  );
}
