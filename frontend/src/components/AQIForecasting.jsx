
import {
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  Activity as ActivityIcon,
  AlertTriangle,
  Clock3,
  CloudSun,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Wind,
  CalendarDays,
  MapPin
} from "lucide-react";

import {
  getForecast,
  getApiErrorMessage
} from "../services/airwiseApi";

import IndiaLocationSelector from "./IndiaLocationSelector";
import "./AQIForecasting.css";


const POLLUTANTS = {
  pm2_5: { label: "PM2.5", unit: "µg/m³" },
  pm10: { label: "PM10", unit: "µg/m³" },
  nitrogen_dioxide: { label: "NO₂", unit: "µg/m³" },
  sulphur_dioxide: { label: "SO₂", unit: "µg/m³" },
  carbon_monoxide: { label: "CO", unit: "µg/m³" },
  ozone: { label: "O₃", unit: "µg/m³" }
};

function numberText(value) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number.toLocaleString("en-IN", {
        maximumFractionDigits: 1
      })
    : "Unavailable";
}

function parseLocalDate(value) {
  if (!value) return null;

  const date = new Date(value);

  return Number.isNaN(date.getTime()) ? null : date;
}

function dateLabel(
  value,
  options = {
    weekday: "short",
    day: "numeric",
    month: "short"
  }
) {
  const date = parseLocalDate(value);

  return date
    ? date.toLocaleDateString("en-IN", options)
    : value;
}

function timeLabel(value) {
  const date = parseLocalDate(value);

  return date
    ? date.toLocaleTimeString("en-IN", {
        hour: "numeric",
        minute: "2-digit"
      })
    : value;
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  tone = ""
}) {
  return (
    <article className={`forecast-stat ${tone}`}>
      <div className="forecast-stat-head">
        <span>{title}</span>
        <Icon size={19} />
      </div>

      <strong>{value}</strong>

      <small>{subtitle}</small>
    </article>
  );
}

function ForecastChart({ records, pollutant, unit }) {
  const values = records
    .map(item => Number(item.value))
    .filter(Number.isFinite);

  if (values.length < 2) {
    return (
      <div className="forecast-empty">
        Not enough valid forecast points to draw this chart.
      </div>
    );
  }

  const width = 900;
  const height = 270;

  const pad = {
    top: 18,
    right: 18,
    bottom: 36,
    left: 48
  };

  const min = Math.min(0, ...values);
  const max = Math.max(...values);
  const range = Math.max(1, max - min);

  const points = records
    .map((item, index) => {
      const value = Number(item.value);

      if (!Number.isFinite(value)) return null;

      const x =
        pad.left +
        (index / Math.max(1, records.length - 1)) *
          (width - pad.left - pad.right);

      const y =
        pad.top +
        ((max - value) / range) *
          (height - pad.top - pad.bottom);

      return `${x},${y}`;
    })
    .filter(Boolean);

  return (
    <div className="forecast-chart-wrap">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${pollutant} hourly modelled forecast chart`}
      >
        {[0, 1, 2, 3].map(step => {
          const y =
            pad.top +
            step *
              ((height - pad.top - pad.bottom) / 3);

          const label = max - step * (range / 3);

          return (
            <g key={step}>
              <line
                x1={pad.left}
                y1={y}
                x2={width - pad.right}
                y2={y}
                className="forecast-gridline"
              />

              <text
                x={pad.left - 9}
                y={y + 4}
                textAnchor="end"
                className="forecast-axis-label"
              >
                {numberText(label)}
              </text>
            </g>
          );
        })}

        {points.length > 1 && (
          <polyline
            points={points.join(" ")}
            className="forecast-line"
          />
        )}

        {records.map((item, index) => {
          const value = Number(item.value);

          if (!Number.isFinite(value)) return null;

          const x =
            pad.left +
            (index / Math.max(1, records.length - 1)) *
              (width - pad.left - pad.right);

          const y =
            pad.top +
            ((max - value) / range) *
              (height - pad.top - pad.bottom);

          return (
            <circle
              key={`${item.time}-${index}`}
              cx={x}
              cy={y}
              r="2.8"
              className="forecast-point"
            >
              <title>
                {`${item.time}: ${numberText(value)} ${unit}`}
              </title>
            </circle>
          );
        })}

        <text
          x={pad.left}
          y={height - 8}
          className="forecast-axis-label"
        >
          {timeLabel(records[0].time)}
        </text>

        <text
          x={width - pad.right}
          y={height - 8}
          textAnchor="end"
          className="forecast-axis-label"
        >
          {timeLabel(records[records.length - 1].time)}
        </text>
      </svg>

      <div className="forecast-chart-caption">
        Hourly modelled concentrations · {unit}
      </div>
    </div>
  );
}

export default function AQIForecasting() {
  const [payload, setPayload] = useState(null);

  const [pollutant, setPollutant] = useState("pm2_5");

  const [selectedDay, setSelectedDay] = useState("all");

  const [loading, setLoading] = useState(false);

  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState("");

  const [selectedStation, setSelectedStation] = useState(null);

  // Fetch forecast for the selected station.
  const loadForecast = useCallback(
    async (refresh = false) => {
      if (refresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      try {
        if (!selectedStation) {
          setPayload(null);
          setLoading(false);
          setRefreshing(false);
          return;
        }

        const latitude = Number(selectedStation.latitude);
        const longitude = Number(selectedStation.longitude);

        if (
          !Number.isFinite(latitude) ||
          !Number.isFinite(longitude) ||
          latitude < -90 || latitude > 90 ||
          longitude < -180 || longitude > 180
        ) {
          throw new Error("The selected station does not have valid coordinates. Choose another monitoring station.");
        }

        const result = await getForecast(latitude, longitude);

        if (
          !result?.forecast?.time ||
          !Array.isArray(result.forecast.time)
        ) {
          throw new Error(
            "Forecast API returned an unexpected time-series structure."
          );
        }

        setPayload(result);
      } catch (err) {
        setError(getApiErrorMessage(err));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [selectedStation]
  );

  // Reload forecast whenever the selected station changes.
  useEffect(() => {
    loadForecast();
  }, [loadForecast]);

  const allRecords = useMemo(() => {
    if (!payload?.forecast) return [];

    const times = payload.forecast.time || [];

    const values = payload.forecast[pollutant] || [];

    return times
      .map((time, index) => ({
        time,
        value: values[index] ?? null
      }))
      .filter(
        item =>
          item.value !== null &&
          Number.isFinite(Number(item.value))
      );
  }, [payload, pollutant]);

  const days = useMemo(() => {
    return [
      ...new Set(
        (payload?.forecast?.time || []).map(time =>
          time.slice(0, 10)
        )
      )
    ];
  }, [payload]);

  const futureRecords = useMemo(() => {
    const now = new Date();

    return allRecords.filter(item => {
      const forecastTime = parseLocalDate(item.time);

      return forecastTime && forecastTime > now;
    });
  }, [allRecords]);

  const visibleRecords = useMemo(() => {
    return selectedDay === "all"
      ? futureRecords
      : futureRecords.filter(item =>
          item.time.startsWith(selectedDay)
        );
  }, [futureRecords, selectedDay]);

  const peak = visibleRecords.reduce(
    (best, item) =>
      !best || Number(item.value) > Number(best.value)
        ? item
        : best,
    null
  );

  const minimum = visibleRecords.reduce(
    (best, item) =>
      !best || Number(item.value) < Number(best.value)
        ? item
        : best,
    null
  );

  const average = visibleRecords.length
    ? visibleRecords.reduce(
        (sum, item) => sum + Number(item.value),
        0
      ) / visibleRecords.length
    : null;

  const futurePm25 = useMemo(() => {
    const times = payload?.forecast?.time || [];

    const values = payload?.forecast?.pm2_5 || [];

    const now = new Date();

    return times
      .map((time, index) => ({
        time,
        value: values[index]
      }))
      .filter(item => {
        const forecastTime = parseLocalDate(item.time);

        return (
          forecastTime &&
          forecastTime >= now &&
          Number.isFinite(Number(item.value))
        );
      });
  }, [payload]);

  let bestWindow = null;

  for (let i = 0; i <= futurePm25.length - 2; i++) {
    const pair = futurePm25.slice(i, i + 2);

    if (pair.length !== 2) continue;

    const mean =
      pair.reduce(
        (sum, item) => sum + Number(item.value),
        0
      ) / 2;

    if (!bestWindow || mean < bestWindow.mean) {
      bestWindow = {
        start: pair[0].time,
        end: pair[1].time,
        mean
      };
    }
  }

  const config = POLLUTANTS[pollutant];

  // A forecast must be tied to a selected, registered station.
  // Never silently substitute Jadavpur or another hardcoded location.
  if (!selectedStation) {
    return (
      <section className="aqi-forecast-page">
        <header className="forecast-page-header">
          <div>
            <span className="forecast-eyebrow">PREDICTIVE AIR QUALITY INTELLIGENCE</span>
            <h2>Air Quality Forecasting</h2>
            <p>Choose a monitoring station to view modelled pollutant concentrations for that location.</p>
          </div>
        </header>
        <IndiaLocationSelector
          onStationChange={setSelectedStation}
          title="Choose forecast location"
          requireCoordinates
        />
        <div className="forecast-location-prompt" role="status">
          <MapPin size={22} />
          <div>
            <strong>Select a monitoring station</strong>
            <p>Choose State / UT, district and a station with valid coordinates. Forecast values will then be requested for that station.</p>
          </div>
        </div>
      </section>
    );
  }

  // Show the initial loading screen only.
  // Keep the selector mounted during subsequent forecast requests.
  if (loading && !payload) {
    return (
      <div className="forecast-loading">
        <RefreshCw className="forecast-spin" />
        Loading hourly CAMS forecast...
      </div>
    );
  }

  if (error && !payload) {
    return (
      <div className="forecast-error">
        <AlertTriangle />

        <div>
          <strong>Unable to load forecast</strong>

          <p>{error}</p>

          <button onClick={() => loadForecast()}>
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <section className="aqi-forecast-page">
      <header className="forecast-page-header">
        <div>
          <span className="forecast-eyebrow">
            PREDICTIVE AIR QUALITY INTELLIGENCE
          </span>

          <h2>Air Quality Forecasting</h2>

          <p>
            Explore hourly modelled pollutant concentrations
            for a selected monitoring location.
          </p>
        </div>

        <button
          className="forecast-refresh"
          onClick={() => loadForecast(true)}
          disabled={refreshing}
        >
          <RefreshCw
            size={16}
            className={refreshing ? "forecast-spin" : ""}
          />

          {refreshing ? "Refreshing..." : "Refresh forecast"}
        </button>
      </header>

      {error && (
        <div className="forecast-inline-error">
          <AlertTriangle size={17} />
          {error} Showing the last successful forecast.
        </div>
      )}

      <IndiaLocationSelector
        onStationChange={setSelectedStation}
        title="Choose forecast location"
        requireCoordinates
      />

      <p className="forecast-location-note">
        {`Forecast coordinates: ${selectedStation.latitude}, ${selectedStation.longitude} (${selectedStation.location_label || selectedStation.state}).`}

        {" "}Forecast values are modelled estimates, not measurements from the selected station.
      </p>

      <div className="forecast-source-strip">
        <span>
          <Wind size={17} />
          Source: <strong>{payload?.source || "Open-Meteo"}</strong>
        </span>

        <span>
          <CloudSun size={17} />
          Model: <strong>{payload?.model || "CAMS Global"}</strong>
        </span>

        <span>
          <Clock3 size={17} />
          Timezone:
          <strong>
            {payload?.location?.timezone || "Asia/Kolkata"}
          </strong>
        </span>

        <span>
          <CalendarDays size={17} />
          Forecast horizon: <strong>{days.length} days</strong>
        </span>
      </div>

      <div className="forecast-controls">
        <label>
          Pollutant

          <select
            value={pollutant}
            onChange={event =>
              setPollutant(event.target.value)
            }
          >
            {Object.entries(POLLUTANTS).map(
              ([key, item]) => (
                <option key={key} value={key}>
                  {item.label}
                </option>
              )
            )}
          </select>
        </label>

        <label>
          Forecast period

          <select
            value={selectedDay}
            onChange={event =>
              setSelectedDay(event.target.value)
            }
          >
            <option value="all">
              All available days
            </option>

            {days.map(day => (
              <option key={day} value={day}>
                {dateLabel(day, {
                  weekday: "long",
                  day: "numeric",
                  month: "short"
                })}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="forecast-stats">
        <StatCard
          title="Forecast average"
          value={
            average === null
              ? "—"
              : `${numberText(average)} ${config.unit}`
          }
          subtitle={`${visibleRecords.length} valid hourly values`}
          icon={ActivityIcon}
        />

        <StatCard
          title="Peak concentration"
          value={
            peak
              ? `${numberText(peak.value)} ${config.unit}`
              : "—"
          }
          subtitle={
            peak
              ? `${dateLabel(peak.time)} · ${timeLabel(peak.time)}`
              : "No forecast value"
          }
          icon={TrendingUp}
          tone="warning"
        />

        <StatCard
          title="Lowest concentration"
          value={
            minimum
              ? `${numberText(minimum.value)} ${config.unit}`
              : "—"
          }
          subtitle={
            minimum
              ? `${dateLabel(minimum.time)} · ${timeLabel(minimum.time)}`
              : "No forecast value"
          }
          icon={TrendingDown}
          tone="positive"
        />
      </div>

      <div className="forecast-panel">
        <div className="forecast-panel-heading">
          <div>
            <h3>{config.label} hourly forecast</h3>

            <p>
              Modelled concentration, not an official AQI reading.
            </p>
          </div>

          <span>{config.unit}</span>
        </div>

        <ForecastChart
          records={visibleRecords}
          pollutant={config.label}
          unit={config.unit}
        />
      </div>

      <div className="forecast-panel">
        <div className="forecast-panel-heading">
          <div>
            <h3>Recommended lower-PM2.5 window</h3>

            <p>
              Lowest consecutive two-hour mean among
              the available future hourly forecasts.
            </p>
          </div>

          <Clock3 color="#60a5fa" />
        </div>

        {bestWindow ? (
          <div className="forecast-window">
            <strong>
              {dateLabel(bestWindow.start)} ·
              {" "}{timeLabel(bestWindow.start)} –
              {" "}{timeLabel(bestWindow.end)}
            </strong>

            <span>
              Mean modelled PM2.5:
              {" "}{numberText(bestWindow.mean)} µg/m³
            </span>
          </div>
        ) : (
          <p className="forecast-muted">
            Not enough future PM2.5 forecast values
            to recommend a window.
          </p>
        )}

        <p className="forecast-note">
          This is a concentration-based planning aid,
          not a guarantee of safe outdoor conditions.
          Consider local conditions and personal health needs.
        </p>
      </div>

      <div className="forecast-disclaimer">
        <AlertTriangle size={18} />

        <p>
          <strong>Data and model limitations:</strong>
          {" "}Forecasts are regional model output from
          CAMS Global delivered by Open-Meteo. They are
          not direct ground-station measurements, official
          CPCB AQI forecasts, or medical advice. Model grid
          resolution and local conditions can cause
          differences from street-level exposure. Missing
          values are excluded, not treated as zero.
        </p>
      </div>
    </section>
  );
}
