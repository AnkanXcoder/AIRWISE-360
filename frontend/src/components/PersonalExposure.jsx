
import { useState } from "react";
import {
  getExposureRecommendation,
  getApiErrorMessage,
} from "../services/airwiseApi";
import "./PersonalExposure.css";

const initialForm = {
  activity: "walking",
  duration_minutes: 30,
  pollutant: "pm25",
  window_hours: 6,
  sensitive_group: false,
};

const formatDateTime = (value) => {
  if (!value) return "Not available";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(date);
};

const formatNumber = (value, digits = 2) => {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "N/A";
  }

  return Number(value).toFixed(digits);
};

function PersonalExposure() {
  const [form, setForm] = useState(initialForm);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const updateForm = (field, value) => {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setLoading(true);
    setError("");
    setReport(null);

    try {
      const result = await getExposureRecommendation({
        activity: form.activity,
        duration_minutes: Number(form.duration_minutes),
        pollutant: form.pollutant,
        window_hours: Number(form.window_hours),
        sensitive_group: form.sensitive_group,
      });

      if (result.status !== "success") {
        throw new Error(result.message || "Unable to generate recommendation.");
      }

      setReport(result);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const recommendedWindow = report?.recommended_window;
  const hourlyValues = recommendedWindow?.hourly_values || [];

  return (
    <div className="exposure-page">
      <div className="exposure-header">
        <div>
          <span className="exposure-eyebrow">
            AIRWISE 360° / PERSONAL INTELLIGENCE
          </span>

          <h1>Personal Exposure Intelligence</h1>

          <p>
            Find comparatively lower-pollution forecast windows
            for your outdoor activities.
          </p>
        </div>

        <div className="exposure-header-icon">
          <i className="fas fa-person-walking"></i>
        </div>
      </div>

      <form className="exposure-form" onSubmit={handleSubmit}>
        <div className="exposure-section-heading">
          <div>
            <h2>Activity Configuration</h2>
            <p>Configure your activity and forecast preferences.</p>
          </div>
          <span className="exposure-step">01 / CONFIGURE</span>
        </div>

        <div className="exposure-form-grid">
          <div className="exposure-field">
            <label htmlFor="exposure-activity">Outdoor activity</label>
            <select
              id="exposure-activity"
              value={form.activity}
              onChange={(e) => updateForm("activity", e.target.value)}
            >
              <option value="walking">Walking</option>
              <option value="running">Running</option>
              <option value="cycling">Cycling</option>
              <option value="exercise">Outdoor exercise</option>
              <option value="commuting">Commuting</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div className="exposure-field">
            <label htmlFor="exposure-duration">Activity duration</label>
            <select
              id="exposure-duration"
              value={form.duration_minutes}
              onChange={(e) =>
                updateForm("duration_minutes", Number(e.target.value))
              }
            >
              <option value={15}>15 minutes</option>
              <option value={30}>30 minutes</option>
              <option value={45}>45 minutes</option>
              <option value={60}>1 hour</option>
              <option value={90}>90 minutes</option>
              <option value={120}>2 hours</option>
              <option value={180}>3 hours</option>
            </select>
          </div>

          <div className="exposure-field">
            <label htmlFor="exposure-pollutant">Pollutant</label>
            <select
              id="exposure-pollutant"
              value={form.pollutant}
              onChange={(e) => updateForm("pollutant", e.target.value)}
            >
              <option value="pm25">PM2.5</option>
              <option value="pm10">PM10</option>
            </select>
          </div>

          <div className="exposure-field">
            <label htmlFor="exposure-window">Forecast search window</label>
            <select
              id="exposure-window"
              value={form.window_hours}
              onChange={(e) =>
                updateForm("window_hours", Number(e.target.value))
              }
            >
              <option value={1}>Next 1 hour</option>
              <option value={3}>Next 3 hours</option>
              <option value={6}>Next 6 hours</option>
              <option value={9}>Next 9 hours</option>
              <option value={12}>Next 12 hours</option>
            </select>
          </div>
        </div>

        <label className="exposure-sensitive-option">
          <input
            type="checkbox"
            checked={form.sensitive_group}
            onChange={(e) =>
              updateForm("sensitive_group", e.target.checked)
            }
          />
          <span>
            <strong>Sensitive group consideration</strong>
            <small>
              Consider additional caution for children, older adults,
              or people with respiratory or heart conditions.
            </small>
          </span>
        </label>

        <button
          type="submit"
          className="exposure-submit-button"
          disabled={loading}
        >
          {loading ? (
            <>
              <i className="fas fa-spinner fa-spin"></i>
              Analyzing forecast...
            </>
          ) : (
            <>
              <i className="fas fa-magnifying-glass-chart"></i>
              Find Better Outdoor Window
            </>
          )}
        </button>
      </form>

      {error && (
        <div className="exposure-error" role="alert">
          <i className="fas fa-circle-exclamation"></i>
          <span>{error}</span>
        </div>
      )}

      {report && (
        <div className="exposure-results">
          <div className="exposure-section-heading">
            <div>
              <h2>Exposure Analysis</h2>
              <p>
                Forecast-based recommendation for your selected activity.
              </p>
            </div>
            <span className="exposure-status">
              <i className="fas fa-check-circle"></i> Analysis complete
            </span>
          </div>

          <div className="exposure-result-grid">
            <div className="exposure-result-card recommended-card">
              <span className="exposure-card-label">
                RECOMMENDED FORECAST WINDOW
              </span>

              <h3>
                {recommendedWindow
                  ? `${formatDateTime(recommendedWindow.start_time)}`
                  : "No suitable window"}
              </h3>

              {recommendedWindow && (
                <p>
                  Until {formatDateTime(recommendedWindow.end_time)}
                </p>
              )}

              <div className="exposure-card-footer">
                <i className="fas fa-calendar-check"></i>
                {recommendedWindow
                  ? "Comparatively lower concentration"
                  : "No recommendation available"}
              </div>
            </div>

            <div className="exposure-result-card">
              <span className="exposure-card-label">
                AVERAGE CONCENTRATION
              </span>

              <h3>
                {formatNumber(recommendedWindow?.average_concentration)}
              </h3>

              <p>{report.unit || "µg/m³"}</p>

              <div className="exposure-card-footer">
                Selected pollutant: {report.pollutant?.toUpperCase()}
              </div>
            </div>

            <div className="exposure-result-card">
              <span className="exposure-card-label">
                EXPOSURE PROXY
              </span>

              <h3>
                {formatNumber(report.exposure_proxy?.value)}
              </h3>

              <p>{report.exposure_proxy?.unit || "µg·h/m³"}</p>

              <div className="exposure-card-footer">
                Concentration × activity duration
              </div>
            </div>

            <div className="exposure-result-card">
              <span className="exposure-card-label">
                FORECAST COVERAGE
              </span>

              <h3>{report.forecast_hours_available ?? "N/A"}</h3>

              <p>Available forecast hours</p>

              <div className="exposure-card-footer">
                {report.candidate_windows ?? 0} candidate windows evaluated
              </div>
            </div>
          </div>

          {hourlyValues.length > 0 && (
            <div className="exposure-hourly-panel">
              <div className="exposure-section-heading">
                <div>
                  <h2>Hourly Forecast Breakdown</h2>
                  <p>Concentration values within the recommended window.</p>
                </div>
              </div>

              <div className="exposure-hourly-list">
                {hourlyValues.map((item, index) => (
                  <div className="exposure-hourly-row" key={`${item.timestamp}-${index}`}>
                    <div className="exposure-hourly-time">
                      <i className="fas fa-clock"></i>
                      {formatDateTime(item.timestamp)}
                    </div>

                    <div className="exposure-hourly-track">
                      <div
                        className="exposure-hourly-fill"
                        style={{
                          width: `${
                            Math.min(
                              100,
                              (Number(item.concentration) /
                                Math.max(
                                  1,
                                  ...hourlyValues.map((v) =>
                                    Number(v.concentration) || 0
                                  )
                                )) *
                                100
                            )
                          }%`,
                        }}
                      ></div>
                    </div>

                    <strong>
                      {formatNumber(item.concentration)} µg/m³
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="exposure-recommendation">
            <i className="fas fa-lightbulb"></i>
            <div>
              <h3>Recommendation</h3>
              <p>{report.recommendation}</p>
            </div>
          </div>

          {report.sensitive_group && (
            <div className="exposure-sensitive-notice">
              <i className="fas fa-heart-pulse"></i>
              <div>
                <strong>Sensitive-group consideration enabled</strong>
                <p>
                  Follow official local air-quality advisories and
                  consult a healthcare professional for individual advice.
                </p>
              </div>
            </div>
          )}

          <div className="exposure-methodology">
            <h3>
              <i className="fas fa-flask"></i> Methodology & Data Transparency
            </h3>

            <div className="exposure-method-grid">
              <div>
                <span>Data source</span>
                <strong>{report.source || "Not available"}</strong>
              </div>

              <div>
                <span>Forecast model</span>
                <strong>{report.model || "Not available"}</strong>
              </div>

              <div>
                <span>Data type</span>
                <strong>Modelled forecast</strong>
              </div>

              <div>
                <span>Location timezone</span>
                <strong>{report.timezone || "Not available"}</strong>
              </div>
            </div>

            <p className="exposure-disclaimer">
              {report.disclaimer}
            </p>

            {report.exposure_proxy?.warning && (
              <p className="exposure-disclaimer">
                {report.exposure_proxy.warning}
              </p>
            )}
          </div>
        </div>
      )}

      {!report && !loading && !error && (
        <div className="exposure-empty-state">
          <i className="fas fa-wind"></i>
          <h3>Ready to analyze your exposure?</h3>
          <p>
            Configure your activity above and generate a forecast-based
            recommendation.
          </p>
        </div>
      )}
    </div>
  );
}

export default PersonalExposure;
