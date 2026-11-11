
import { useCallback, useEffect, useState } from "react";

import {
  Activity,
  Database,
  ShieldCheck,
  BrainCircuit,
  RefreshCw,
  AlertTriangle,
  Clock,
  BarChart3,
  CheckCircle2,
  XCircle
} from "lucide-react";

import {
  getMLReadiness,
  getDatasetHealth,
  getApiErrorMessage
} from "../services/airwiseApi";

import "./MLDataIntelligence.css";

const STATION_ID = 6950;

function formatNumber(value, digits = 0) {
  if (value === null || value === undefined) return "N/A";

  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  });
}

function StatusBadge({ status }) {
  const normalized = String(status || "unknown").toLowerCase();

  const labels = {
    review_required: "Review Required",
    insufficient_data: "Insufficient Data",
    experimental: "Experimental",
    ready: "Ready",
    failed: "Failed"
  };

  return (
    <span className={`ml-status ml-status-${normalized}`}>
      {labels[normalized] || normalized.replaceAll("_", " ")}
    </span>
  );
}

function MetricCard({ title, value, description, icon: Icon }) {
  return (
    <article className="ml-metric-card">
      <div className="ml-metric-top">
        <span>{title}</span>
        <Icon size={20} />
      </div>

      <h2>{value}</h2>

      <p>{description}</p>
    </article>
  );
}

function TrendBar({ label, count, total }) {
  const percentage = total > 0 ? (count / total) * 100 : 0;

  return (
    <div className="ml-trend-item">
      <div className="ml-trend-label">
        <span>{label}</span>
        <strong>{formatNumber(count)} ({percentage.toFixed(1)}%)</strong>
      </div>

      <div className="ml-trend-track">
        <div
          className="ml-trend-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function MLDataIntelligence() {
  const [health, setHealth] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const fetchDashboardData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError("");

    try {
      const [healthResult, readinessResult] = await Promise.all([
        getDatasetHealth(STATION_ID),
        getMLReadiness(STATION_ID)
      ]);

      setHealth(healthResult);
      setReadiness(readinessResult);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  if (loading) {
    return (
      <section className="ml-page">
        <div className="ml-loading">
          <RefreshCw className="ml-spin" size={28} />
          <h3>Loading ML Intelligence</h3>
          <p>Retrieving dataset health and model readiness.</p>
        </div>
      </section>
    );
  }

  if (error && (!health || !readiness)) {
    return (
      <section className="ml-page">
        <div className="ml-error">
          <AlertTriangle size={30} />
          <h2>Unable to load intelligence data</h2>
          <p>{error}</p>

          <button
            type="button"
            onClick={() => fetchDashboardData()}
          >
            Retry
          </button>
        </div>
      </section>
    );
  }

  const quality = health?.data_quality || {};
  const statistics = health?.concentration_statistics || {};
  const dataset = health?.forecasting_dataset || {};
  const trends = health?.pollution_trends || {};

  const historical = readiness?.historical_readiness || readiness || {};
  const forecasting = readiness?.forecasting_readiness || {};

  const trainTrends = trends.training || {};
  const validationTrends = trends.validation || {};
  const testTrends = trends.test || {};

  const trendCategories = [
    { key: "rapidly_rising", label: "Rapidly Rising" },
    { key: "relatively_stable", label: "Relatively Stable" },
    { key: "rapidly_falling", label: "Rapidly Falling" }
  ];

  return (
    <main className="ml-page">

      {/* PAGE HEADER */}

      <header className="ml-page-header">
        <div>
          <span className="ml-eyebrow">
            AIRWISE 360° / MACHINE LEARNING
          </span>

          <h1>ML & Data Intelligence</h1>

          <p>
            Monitor dataset reliability, evaluate forecasting readiness
            and understand the limitations of environmental data.
          </p>
        </div>

        <button
          type="button"
          className="ml-refresh-button"
          onClick={() => fetchDashboardData(true)}
          disabled={refreshing}
        >
          <RefreshCw
            size={17}
            className={refreshing ? "ml-spin" : ""}
          />
          {refreshing ? "Refreshing..." : "Refresh Data"}
        </button>
      </header>

      {error && (
        <div className="ml-inline-error">
          <AlertTriangle size={17} />
          {error}. Showing the last successfully retrieved data.
        </div>
      )}

      {/* MONITORING STATUS */}

      <section className="ml-status-panel">
        <div className="ml-status-icon">
          <ShieldCheck size={25} />
        </div>

        <div className="ml-status-content">
          <span>DATASET MONITORING STATUS</span>

          <h2>
            {health?.monitoring_status === "review_required"
              ? "Dataset requires review"
              : "Dataset monitoring result"}
          </h2>

          <p>
            The monitoring system identified temporal coverage gaps.
            Review data completeness before relying on forecasting results.
          </p>
        </div>

        <StatusBadge status={health?.monitoring_status} />
      </section>

      {/* KEY METRICS */}

      <section className="ml-section">
        <div className="ml-section-heading">
          <div>
            <span className="ml-section-kicker">01 / DATASET OVERVIEW</span>
            <h2>Dataset Health</h2>
          </div>
        </div>

        <div className="ml-metrics-grid">

          <MetricCard
            title="Raw Observations"
            value={formatNumber(quality.raw_observations)}
            description="Historical sensor records"
            icon={Database}
          />

          <MetricCard
            title="Temporal Coverage"
            value={`${formatNumber(quality.coverage_percentage, 2)}%`}
            description="Observed versus expected intervals"
            icon={Activity}
          />

          <MetricCard
            title="Missing Intervals"
            value={formatNumber(quality.missing_intervals)}
            description="Missing 15-minute observations"
            icon={AlertTriangle}
          />

          <MetricCard
            title="Longest Data Gap"
            value={`${formatNumber(quality.longest_gap_hours, 1)} hrs`}
            description="Longest continuous observation gap"
            icon={Clock}
          />

        </div>
      </section>

      {/* DATA QUALITY */}

      <section className="ml-section">
        <div className="ml-section-heading">
          <div>
            <span className="ml-section-kicker">02 / QUALITY CONTROL</span>
            <h2>Data Quality Diagnostics</h2>
          </div>
        </div>

        <div className="ml-panel-grid">

          <article className="ml-panel">
            <h3>Observation Integrity</h3>

            <div className="ml-detail-row">
              <span>Expected intervals</span>
              <strong>{formatNumber(quality.expected_intervals)}</strong>
            </div>

            <div className="ml-detail-row">
              <span>Observed intervals</span>
              <strong>{formatNumber(quality.observed_intervals)}</strong>
            </div>

            <div className="ml-detail-row">
              <span>Separate data gaps</span>
              <strong>{formatNumber(quality.separate_gaps)}</strong>
            </div>

            <div className="ml-detail-row">
              <span>Gaps over 1 hour</span>
              <strong>{formatNumber(quality.gaps_over_1_hour)}</strong>
            </div>

            <div className="ml-detail-row">
              <span>Gaps over 6 hours</span>
              <strong>{formatNumber(quality.gaps_over_6_hours)}</strong>
            </div>

            <div className="ml-detail-row">
              <span>Gaps over 24 hours</span>
              <strong>{formatNumber(quality.gaps_over_24_hours)}</strong>
            </div>

            <div className="ml-detail-row">
              <span>Observation days</span>
              <strong>{formatNumber(quality.observation_days)}</strong>
            </div>
          </article>

          <article className="ml-panel">
            <h3>PM2.5 Concentration Statistics</h3>

            <div className="ml-detail-row">
              <span>Mean</span>
              <strong>{formatNumber(statistics.mean, 3)} µg/m³</strong>
            </div>

            <div className="ml-detail-row">
              <span>Median</span>
              <strong>{formatNumber(statistics.median, 3)} µg/m³</strong>
            </div>

            <div className="ml-detail-row">
              <span>Minimum</span>
              <strong>{formatNumber(statistics.minimum, 2)} µg/m³</strong>
            </div>

            <div className="ml-detail-row">
              <span>Maximum</span>
              <strong>{formatNumber(statistics.maximum, 2)} µg/m³</strong>
            </div>

            <div className="ml-detail-row">
              <span>Negative values</span>
              <strong>{formatNumber(statistics.negative_values)}</strong>
            </div>

            <div className="ml-detail-row">
              <span>Non-finite values</span>
              <strong>{formatNumber(statistics.non_finite_values)}</strong>
            </div>
          </article>

        </div>
      </section>

      {/* FORECASTING DATASET */}

      <section className="ml-section">
        <div className="ml-section-heading">
          <div>
            <span className="ml-section-kicker">03 / FEATURE ENGINEERING</span>
            <h2>Forecasting Dataset</h2>
          </div>
          <StatusBadge status={forecasting.status} />
        </div>

        <div className="ml-metrics-grid">

          <MetricCard
            title="Usable Samples"
            value={formatNumber(dataset.total_samples)}
            description="Samples available for forecasting"
            icon={BarChart3}
          />

          <MetricCard
            title="Feature Count"
            value={formatNumber(dataset.feature_count)}
            description="Engineered model input features"
            icon={BrainCircuit}
          />

          <MetricCard
            title="Forecast Horizon"
            value={health?.methodology?.forecast_horizon || "N/A"}
            description="Next-hour PM2.5 average"
            icon={Clock}
          />

          <MetricCard
            title="Sampling Frequency"
            value={health?.methodology?.frequency || "N/A"}
            description="Expected observation frequency"
            icon={Activity}
          />

        </div>

        <article className="ml-panel ml-split-panel">
          <h3>Chronological Data Split</h3>

          <div className="ml-split-bar">
            <div
              className="ml-split-train"
              style={{
                width: `${dataset.total_samples
                  ? dataset.training_samples / dataset.total_samples * 100
                  : 0}%`
              }}
            />

            <div
              className="ml-split-validation"
              style={{
                width: `${dataset.total_samples
                  ? dataset.validation_samples / dataset.total_samples * 100
                  : 0}%`
              }}
            />

            <div
              className="ml-split-test"
              style={{
                width: `${dataset.total_samples
                  ? dataset.test_samples / dataset.total_samples * 100
                  : 0}%`
              }}
            />
          </div>

          <div className="ml-split-legend">
            <span>
              <i className="ml-dot ml-dot-train" />
              Training: {formatNumber(dataset.training_samples)}
            </span>

            <span>
              <i className="ml-dot ml-dot-validation" />
              Validation: {formatNumber(dataset.validation_samples)}
            </span>

            <span>
              <i className="ml-dot ml-dot-test" />
              Test: {formatNumber(dataset.test_samples)}
            </span>
          </div>

          <div className="ml-detail-row">
            <span>Chronological ordering</span>
            <strong>
              {dataset.chronological_ordering ? "Verified" : "Not verified"}
            </strong>
          </div>

          <div className="ml-detail-row">
            <span>Missing feature values</span>
            <strong>{formatNumber(dataset.missing_feature_values)}</strong>
          </div>

          <div className="ml-detail-row">
            <span>Missing target values</span>
            <strong>{formatNumber(dataset.missing_target_values)}</strong>
          </div>
        </article>
      </section>

      {/* POLLUTION TRENDS */}

      <section className="ml-section">
        <div className="ml-section-heading">
          <div>
            <span className="ml-section-kicker">04 / TEMPORAL PATTERNS</span>
            <h2>Pollution Trend Distribution</h2>
            <p>
              Experimental classification based on 30-minute PM2.5 changes.
            </p>
          </div>
        </div>

        <div className="ml-panel-grid">

          {[
            { name: "Training", data: trainTrends },
            { name: "Validation", data: validationTrends },
            { name: "Test", data: testTrends }
          ].map((partition) => (

            <article className="ml-panel" key={partition.name}>
              <h3>{partition.name} Dataset</h3>

              <p className="ml-panel-subtitle">
                {formatNumber(partition.data.total)} samples
              </p>

              {trendCategories.map((category) => (
                <TrendBar
                  key={category.key}
                  label={category.label}
                  count={partition.data[category.key] || 0}
                  total={partition.data.total || 0}
                />
              ))}

            </article>

          ))}

        </div>

        <div className="ml-methodology-note">
          <AlertTriangle size={19} />

          <p>
            The ±{formatNumber(health?.methodology?.rapid_change_threshold)}
            {" "}µg/m³ over 30 minutes threshold is experimental.
            It is not an official AQI or health classification threshold.
          </p>
        </div>
      </section>

      {/* MODEL READINESS */}

      <section className="ml-section">
        <div className="ml-section-heading">
          <div>
            <span className="ml-section-kicker">05 / MODEL GOVERNANCE</span>
            <h2>Model Readiness Assessment</h2>
          </div>
        </div>

        <div className="ml-panel-grid">

          <article className="ml-panel">
            <div className="ml-readiness-heading">
              <h3>Historical Data Readiness</h3>
              <StatusBadge status={historical.status} />
            </div>

            <p>{historical.message}</p>

            <div className="ml-detail-row">
              <span>Required history</span>
              <strong>
                {historical.thresholds?.minimum_history_days || 30} days
              </strong>
            </div>

            <div className="ml-detail-row">
              <span>Available date range</span>
              <strong>
                {formatNumber(historical.date_range_days, 2)} days
              </strong>
            </div>

            <div className="ml-detail-row">
              <span>Historical readiness</span>
              <strong>
                {historical.ready ? "Passed" : "Not passed"}
              </strong>
            </div>
          </article>

          <article className="ml-panel">
            <div className="ml-readiness-heading">
              <h3>Forecasting Readiness</h3>
              <StatusBadge status={forecasting.status} />
            </div>

            <p>{forecasting.message}</p>

            <div className="ml-detail-row">
              <span>Experimental evaluation</span>
              <strong>
                {forecasting.ready ? "Eligible" : "Not eligible"}
              </strong>
            </div>

            <div className="ml-detail-row">
              <span>Production deployment</span>
              <strong>
                {forecasting.production_ready ? "Approved" : "Not approved"}
              </strong>
            </div>

            <div className="ml-detail-row">
              <span>Baseline</span>
              <strong>
                {forecasting.model_evaluation?.baseline || "N/A"}
              </strong>
            </div>
          </article>

        </div>
      </section>

      {/* DATA GOVERNANCE */}

      <section className="ml-section">
        <div className="ml-section-heading">
          <div>
            <span className="ml-section-kicker">06 / TRANSPARENCY</span>
            <h2>Data Trust & Limitations</h2>
          </div>
        </div>

        <article className="ml-panel ml-governance-panel">

          <div className="ml-governance-item">
            <CheckCircle2 size={19} />
            <div>
              <strong>Chronological split</strong>
              <p>Training, validation and test partitions preserve time order.</p>
            </div>
          </div>

          <div className="ml-governance-item">
            <CheckCircle2 size={19} />
            <div>
              <strong>No missing feature or target values</strong>
              <p>
                The prepared forecasting dataset reports zero missing
                feature and target values.
              </p>
            </div>
          </div>

          <div className="ml-governance-item">
            <AlertTriangle size={19} />
            <div>
              <strong>Temporal coverage requires improvement</strong>
              <p>
                {formatNumber(quality.missing_intervals)} expected intervals
                are missing. The longest gap is
                {" "}{formatNumber(quality.longest_gap_hours, 1)} hours.
              </p>
            </div>
          </div>

          <div className="ml-governance-item">
            <XCircle size={19} />
            <div>
              <strong>Production forecasting is not approved</strong>
              <p>
                Experimental readiness does not establish predictive
                superiority or production reliability.
              </p>
            </div>
          </div>

          <div className="ml-governance-item">
            <AlertTriangle size={19} />
            <div>
              <strong>Test partition limitation</strong>
              <p>
                The current test partition has already been used in
                exploratory error analysis. It should not be described
                as an untouched final holdout.
              </p>
            </div>
          </div>

        </article>
      </section>

      {/* SOURCE FOOTER */}

      <footer className="ml-source-footer">
        <div>
          <Database size={17} />
          <span>
            Source: {health?.data_source || "AIRWISE historical database"}
          </span>
        </div>

        <span>
          Sensor ID: {health?.sensor_id || "N/A"} | Location ID: {STATION_ID}
        </span>

        <span>
          Pollutant: PM2.5 | Units: µg/m³
        </span>
      </footer>

    </main>
  );
}

export default MLDataIntelligence;
