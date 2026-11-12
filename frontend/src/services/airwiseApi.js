
import axios from "axios";

// ------------------------------------
// API CONFIGURATION
// ------------------------------------

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ------------------------------------
// LIVE STATION DATA (LEGACY)
// ------------------------------------

export const getStationMeasurements = async (stationId) => {
  const { data } = await api.get(
    `/api/stations/${stationId}/measurements`
  );

  return data;
};

export const getStationQuality = async (stationId) => {
  const { data } = await api.get(
    `/api/stations/${stationId}/quality`
  );

  return data;
};

export const collectStationData = async (stationId) => {
  const { data } = await api.post(
    `/api/stations/${stationId}/collect`
  );

  return data;
};

// ------------------------------------
// HISTORICAL DATA (LEGACY)
// Keep until dependent components migrate.
// ------------------------------------

export const getStationHistory = async (
  stationId,
  pollutant = "pm25",
  limit = 100
) => {
  const { data } = await api.get(
    `/api/stations/${stationId}/history`,
    {
      params: { pollutant, limit },
    }
  );

  return data;
};

export const getHistoricalAnalytics = async (
  stationId,
  pollutant = "pm25",
  limit = 100
) => {
  const { data } = await api.get(
    `/api/analytics/${stationId}/history`,
    {
      params: { pollutant, limit },
    }
  );

  return data;
};

// ------------------------------------
// INDIA STATION REGISTRY
// ------------------------------------

export const getIndiaOverview = async () => {
  const { data } = await api.get("/api/india/overview");

  return data;
};

export const getIndiaStations = async (params = {}) => {
  const { data } = await api.get("/api/india/stations", {
    params,
  });

  return data;
};

export const getIndiaFilters = async () => {
  const { data } = await api.get("/api/india/filters");

  return data;
};

export const getIndiaMap = async (limit = 1000) => {
  const { data } = await api.get("/api/india/map", {
    params: { limit },
  });

  return data;
};

// ------------------------------------
// INDIA STATION LIVE MEASUREMENTS
// ------------------------------------

export const getIndiaStationMeasurements = async (
  source,
  sourceLocationId
) => {
  const { data } = await api.get(
    `/api/india/stations/${encodeURIComponent(source)}/${sourceLocationId}/measurements`
  );

  return data;
};

// ------------------------------------
// INDIA STATION HISTORICAL INGESTION
// ------------------------------------

export const ingestIndiaStationHistory = async (
  source,
  sourceLocationId,
  hours = 36
) => {
  const { data } = await api.post(
    `/api/india/stations/${encodeURIComponent(source)}/${sourceLocationId}/ingest`,
    null,
    {
      params: { hours },
    }
  );

  return data;
};

// ------------------------------------
// INDIA STATION CPCB-METHODOLOGY AQI
// ------------------------------------

export const getIndiaStationAqi = async (
  source,
  sourceLocationId
) => {
  const { data } = await api.get(
    `/api/india/stations/${encodeURIComponent(source)}/${sourceLocationId}/aqi`
  );

  return data;
};

// ------------------------------------
// CITY COMPARISON
// ------------------------------------

export const compareCities = async () => {
  const { data } = await api.get("/api/cities/compare");

  return data;
};

// ------------------------------------
// AIR QUALITY FORECAST
// ------------------------------------

export const getForecast = async (
  latitude = 22.49929,
  longitude = 88.36917
) => {
  const { data } = await api.get("/api/forecast", {
    params: { latitude, longitude },
  });

  return data;
};

// ------------------------------------
// HEALTH GUIDANCE
// ------------------------------------

export const getHealthGuidance = async ({
  officialAqi,
  sourceType = "unknown",
  sensitiveGroup = false,
  symptoms = false,
} = {}) => {
  const params = {
    source_type: sourceType,
    sensitive_group: sensitiveGroup,
    symptoms,
  };

  if (officialAqi !== undefined && officialAqi !== null) {
    params.official_aqi = officialAqi;
  }

  const { data } = await api.get("/api/health/guidance", {
    params,
  });

  return data;
};

// ------------------------------------
// SPIKE DETECTION (LEGACY)
// ------------------------------------

export const getSpikeAnalysis = async (
  stationId,
  pollutant = "pm25",
  limit = 100
) => {
  const { data } = await api.get(
    `/api/analytics/${stationId}/spikes`,
    {
      params: { pollutant, limit },
    }
  );

  return data;
};

// ------------------------------------
// FLATLINE DETECTION (LEGACY)
// ------------------------------------

export const getFlatlineAnalysis = async (
  stationId,
  pollutant = "pm25",
  limit = 100
) => {
  const { data } = await api.get(
    `/api/analytics/${stationId}/flatlines`,
    {
      params: { pollutant, limit },
    }
  );

  return data;
};

// ------------------------------------
// POLLUTION EVENT INTELLIGENCE (LEGACY)
// ------------------------------------

export const getPollutionEvents = async (
  stationId,
  pollutant = "pm25"
) => {
  const { data } = await api.get(
    `/api/analytics/${stationId}/events`,
    {
      params: { pollutant },
    }
  );

  return data;
};

// ------------------------------------
// DIWALI IMPACT ANALYSIS
// ------------------------------------

export const getDiwaliImpact = async (params = {}) => {
  const { data } = await api.get("/api/analytics/diwali", {
    params,
  });

  return data;
};

// ------------------------------------
// PERSONAL EXPOSURE
// ------------------------------------

export const getExposureRecommendation = async (params = {}) => {
  const { data } = await api.get("/api/exposure/recommend", {
    params,
  });

  return data;
};

// ------------------------------------
// ML DATA READINESS
// ------------------------------------

export const getMLReadiness = async (
  stationId,
  pollutant = "pm25",
  limit = 10000
) => {
  const { data } = await api.get(
    `/api/ml/readiness/${stationId}`,
    {
      params: { pollutant, limit },
    }
  );

  return data;
};

// ------------------------------------
// ML DATASET HEALTH
// ------------------------------------

export const getDatasetHealth = async (stationId) => {
  const { data } = await api.get(
    `/api/ml/dataset-health/${stationId}`
  );

  return data;
};

// ------------------------------------
// API STATUS
// ------------------------------------

export const getApiStatus = async () => {
  const { data } = await api.get("/");

  return data;
};

// ------------------------------------
// ERROR HANDLING
// ------------------------------------

export const getApiErrorMessage = (error) => {
  return (
    error.response?.data?.detail ||
    error.message ||
    "Unable to connect to AIRWISE API."
  );
};

// ------------------------------------
// DEFAULT EXPORT
// ------------------------------------

export default api;
