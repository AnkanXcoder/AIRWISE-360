import { useCallback, useEffect, useMemo, useState } from "react";
import "./CityComparison.css";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Clock3,
  MapPin,
  RefreshCw,
  Wind
} from "lucide-react";
import { compareCities, getApiErrorMessage } from "../services/airwiseApi";

const POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"];

const POLLUTANT_LABELS = {
  "PM2.5": "PM2.5",
  PM10: "PM10",
  NO2: "NO₂",
  SO2: "SO₂",
  CO: "CO",
  O3: "O₃"
};

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "Unavailable";
  const number = Number(value);
  if (!Number.isFinite(number)) return "Unavailable";
  return number.toLocaleString("en-IN", { maximumFractionDigits: 1 });
}

function formatForecastTime(value, timezone = "Asia/Kolkata") {
  if (!value) return "Timestamp unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: timezone
  });
}

function MetricCard({ label, value, detail, icon: Icon, tone = "default" }) {
  return (
    <article className={`city-metric-card city-metric-${tone}`}>
      <div className="city-metric-heading">
        <span>{label}</span>
        <Icon size={19} />
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function ComparisonBars({ rows, unit }) {
  const numericRows = rows.filter(row => Number.isFinite(Number(row.value)));
  const maximum = Math.max(0, ...numericRows.map(row => Number(row.value)));

  if (numericRows.length === 0) {
    return <div className="city-empty-state">No numeric values are available for this pollutant.</div>;
  }

  return (
    <div className="city-bars" role="img" aria-label="Pollutant concentration comparison by city">
      {numericRows.map((row, index) => {
        const value = Number(row.value);
        const width = maximum > 0 ? (value / maximum) * 100 : 0;
        return (
          <div className="city-bar-row" key={row.city}>
            <div className="city-bar-label">
              <span>{index + 1}. {row.city}</span>
              <strong>{formatValue(value)} <small>{unit}</small></strong>
            </div>
            <div className="city-bar-track">
              <div className="city-bar-fill" style={{ width: `${width}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function CityComparison() {
  const [comparison, setComparison] = useState(null);
  const [selectedPollutant, setSelectedPollutant] = useState("PM2.5");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadComparison = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    setError("");
    try {
      const response = await compareCities();
      if (!response || typeof response.city_data !== "object" || !response.city_data) {
        throw new Error("City comparison API returned an unexpected response.");
      }
      setComparison(response);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadComparison();
  }, [loadComparison]);

  const cities = comparison?.cities_compared || Object.keys(comparison?.city_data || {});
  const cityData = comparison?.city_data || {};
  const rankings = comparison?.pollutant_rankings || {};
  const unit = comparison?.unit || "µg/m³";
  const selectedRanking = rankings[selectedPollutant];
  const rankingRows = useMemo(() => {
    if (Array.isArray(selectedRanking?.cities_ranked)) {
      return selectedRanking.cities_ranked;
    }

    return cities
      .filter(city => cityData[city]?.pollutants)
      .map(city => ({
        city,
        value: cityData[city].pollutants[selectedPollutant]
      }))
      .filter(row => row.value !== null && row.value !== undefined && Number.isFinite(Number(row.value)))
      .sort((a, b) => Number(a.value) - Number(b.value));
  }, [cities, cityData, selectedPollutant, selectedRanking]);

  const availableCityCount = cities.filter(city => cityData[city]).length;
  const lowest = selectedRanking?.lowest;
  const highest = selectedRanking?.highest;
  const pm25Ranking = rankings["PM2.5"];
  const pm25Highest = pm25Ranking?.highest;
  const pm25Lowest = pm25Ranking?.lowest;

  if (loading) {
    return (
      <section className="city-comparison-page">
        <div className="city-loading">
          <RefreshCw className="city-spin" size={22} />
          Loading modelled city comparison...
        </div>
      </section>
    );
  }

  if (error && !comparison) {
    return (
      <section className="city-comparison-page">
        <div className="city-error">
          <AlertTriangle size={20} />
          <div>
            <strong>Unable to load city comparison</strong>
            <p>{error}</p>
            <button type="button" onClick={() => loadComparison()}>Try again</button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="city-comparison-page">
      <header className="city-page-header">
        <div>
          <span className="city-eyebrow">MULTI-CITY POLLUTION INTELLIGENCE</span>
          <h2>City Comparison</h2>
          <p>Compare modelled pollutant concentrations across major Indian cities.</p>
        </div>
        <button
          type="button"
          className="city-refresh-button"
          onClick={() => loadComparison(true)}
          disabled={refreshing}
        >
          <RefreshCw size={16} className={refreshing ? "city-spin" : ""} />
          {refreshing ? "Refreshing..." : "Refresh comparison"}
        </button>
      </header>

      {error && (
        <div className="city-inline-error">
          <AlertTriangle size={17} />
          <span>Refresh failed. Showing the last successfully retrieved comparison. {error}</span>
        </div>
      )}

      <div className="city-source-strip">
        <div><Wind size={17} /><span>Source: <strong>{comparison?.source || "Open-Meteo"}</strong></span></div>
        <div><Activity size={17} /><span>Model: <strong>{comparison?.model || "CAMS Global"}</strong></span></div>
        <div><Clock3 size={17} /><span>Forecast time: <strong>{formatForecastTime(comparison?.forecast_timestamp, comparison?.timezone)}</strong></span></div>
        <div><MapPin size={17} /><span>Coverage: <strong>{availableCityCount} of {comparison?.city_count ?? cities.length} cities</strong></span></div>
      </div>

      <div className="city-metric-grid">
        <MetricCard
          label="Cities compared"
          value={availableCityCount}
          detail="Modelled city locations"
          icon={MapPin}
        />
        <MetricCard
          label="Pollutants tracked"
          value={POLLUTANTS.length}
          detail="Six pollutant variables"
          icon={Wind}
        />
        <MetricCard
          label="Lowest PM2.5"
          value={pm25Lowest ? `${formatValue(pm25Lowest.value)} ${unit}` : "Unavailable"}
          detail={pm25Lowest?.city || "No ranking available"}
          icon={ArrowDownRight}
          tone="positive"
        />
        <MetricCard
          label="Highest PM2.5"
          value={pm25Highest ? `${formatValue(pm25Highest.value)} ${unit}` : "Unavailable"}
          detail={pm25Highest?.city || "No ranking available"}
          icon={ArrowUpRight}
          tone="warning"
        />
      </div>

      <div className="city-panel">
        <div className="city-panel-header">
          <div>
            <h3>Pollutant comparison</h3>
            <p>Concentration values by city. Select a pollutant to update the ranking.</p>
          </div>
          <select
            value={selectedPollutant}
            onChange={event => setSelectedPollutant(event.target.value)}
            aria-label="Select pollutant to compare"
          >
            {POLLUTANTS.map(pollutant => (
              <option key={pollutant} value={pollutant}>{POLLUTANT_LABELS[pollutant]}</option>
            ))}
          </select>
        </div>

        <ComparisonBars rows={rankingRows} unit={unit} />

        <div className="city-ranking-summary">
          <div>
            <span>Lowest modelled concentration</span>
            <strong>{lowest?.city || "Unavailable"}</strong>
            <small>{lowest ? `${formatValue(lowest.value)} ${unit}` : "No value"}</small>
          </div>
          <div>
            <span>Highest modelled concentration</span>
            <strong>{highest?.city || "Unavailable"}</strong>
            <small>{highest ? `${formatValue(highest.value)} ${unit}` : "No value"}</small>
          </div>
        </div>
      </div>

      <div className="city-panel">
        <div className="city-panel-header">
          <div>
            <h3>City pollutant matrix</h3>
            <p>Modelled concentrations at the returned forecast timestamp.</p>
          </div>
          <BarChart3 size={20} />
        </div>
        <div className="city-table-wrap">
          <table className="city-table">
            <thead>
              <tr>
                <th>City</th>
                {POLLUTANTS.map(pollutant => (
                  <th key={pollutant}>{POLLUTANT_LABELS[pollutant]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cities.map(city => (
                <tr key={city}>
                  <td>
                    <strong>{city}</strong>
                    <small>
                      {cityData[city]?.coordinates
                        ? `${formatValue(cityData[city].coordinates.latitude)}, ${formatValue(cityData[city].coordinates.longitude)}`
                        : "Coordinates unavailable"}
                    </small>
                  </td>
                  {POLLUTANTS.map(pollutant => {
                    const value = cityData[city]?.pollutants?.[pollutant];
                    return (
                      <td key={pollutant}>
                        {value === null || value === undefined ? "—" : formatValue(value)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="city-unit-note">All pollutant values are reported in {unit}. Missing values are shown as unavailable, not zero.</p>
      </div>

      <div className="city-disclaimer">
        <AlertTriangle size={18} />
        <p>
          <strong>Model and data limitations:</strong> These are modelled regional forecast concentrations
          from CAMS Global via Open-Meteo, not direct ground-station observations or official CPCB AQI.
          The city ranking compares the selected pollutant's concentration only; it is not an overall
          health or city-safety ranking. Model grid values may not represent conditions at a specific street or station.
        </p>
      </div>
    </section>
  );
}
