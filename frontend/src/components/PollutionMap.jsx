
import { useState, useEffect, useMemo, useCallback } from "react";

import {
  MapContainer,
  TileLayer,
  LayersControl,
  ZoomControl,
  Marker,
  Tooltip,
  useMap
} from "react-leaflet";

import MarkerClusterGroup from "react-leaflet-cluster";
import { divIcon } from "leaflet";

import {
  Maximize,
  RotateCcw,
  MapPin,
  Search,
  RefreshCw,
  MapPinned,
  Activity,
  Radio,
  AlertCircle,
  Clock,
  Wind,
  LoaderCircle
} from "lucide-react";

import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

// --------------------------------------------------
// CONFIGURATION
// --------------------------------------------------

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const INDIA_CENTER = [22.5, 79];

const INDIA_BOUNDS = [
  [5.0, 67.0],
  [37.5, 98.5]
];

const CACHE_DURATION = 5 * 60 * 1000;

// Cache measurement responses for five minutes.
const measurementCache = new Map();
const measurementRequests = new Map();

const POLLUTANT_INFO = [
  { key: "pm25", label: "PM2.5" },
  { key: "pm10", label: "PM10" },
  { key: "no2", label: "NO₂" },
  { key: "so2", label: "SO₂" },
  { key: "co", label: "CO" },
  { key: "o3", label: "O₃" }
];

// --------------------------------------------------
// HELPERS
// --------------------------------------------------

function isMonitor(station) {
  return (
    station.is_monitor === 1 ||
    station.is_monitor === true ||
    station.is_monitor === "1"
  );
}

function formatTimestamp(timestamp) {
  if (!timestamp) return "Unavailable";

  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) {
    return "Invalid timestamp";
  }

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata"
  });
}

function formatAge(hours) {
  if (hours === null || hours === undefined) {
    return "Age unavailable";
  }

  const age = Number(hours);

  if (!Number.isFinite(age) || age < 0) {
    return "Age unavailable";
  }

  if (age < 1) {
    return `${Math.round(age * 60)} minutes ago`;
  }

  if (age < 24) {
    return `${age.toFixed(1)} hours ago`;
  }

  return `${(age / 24).toFixed(1)} days ago`;
}

function getFreshnessClass(freshness) {
  switch ((freshness || "").toUpperCase()) {
    case "FRESH":
      return "fresh";

    case "DELAYED":
      return "delayed";

    case "STALE":
      return "stale";

    default:
      return "unknown";
  }
}

// Classify the station using its available core pollutant readings.
// The worst available freshness status is used so a mixture of
// fresh and delayed readings is not misleadingly shown as all fresh.
function getStationFreshness(measurementData) {
  if (!measurementData?.pollutants) {
    return "unknown";
  }

  const readings = POLLUTANT_INFO
    .map(item => measurementData.pollutants[item.key])
    .filter(
      reading =>
        reading &&
        reading.value !== null &&
        reading.value !== undefined &&
        Number.isFinite(Number(reading.value))
    );

  if (readings.length === 0) {
    return "unknown";
  }

  const statuses = readings.map(reading =>
    getFreshnessClass(reading.freshness)
  );

  if (statuses.includes("stale")) return "stale";
  if (statuses.includes("delayed")) return "delayed";
  if (statuses.every(status => status === "fresh")) return "fresh";

  return "unknown";
}

// --------------------------------------------------
// FETCH STATION MEASUREMENTS
// --------------------------------------------------

async function fetchStationMeasurements(source, locationId) {
  const id = `${String(source || "openaq").toLowerCase()}:${String(locationId)}`;

  const cached = measurementCache.get(id);

  if (
    cached &&
    Date.now() - cached.cachedAt < CACHE_DURATION
  ) {
    return cached.data;
  }

  // Prevent duplicate simultaneous requests.
  if (measurementRequests.has(id)) {
    return measurementRequests.get(id);
  }

  const request = (async () => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/india/stations/${encodeURIComponent(source || "openaq")}/${encodeURIComponent(locationId)}/measurements`
      );

      if (!response.ok) {
        throw new Error(
          `Measurement API returned HTTP ${response.status}`
        );
      }

      const data = await response.json();

      if (
        !data ||
        !data.pollutants ||
        typeof data.pollutants !== "object"
      ) {
        throw new Error("Invalid measurement response.");
      }

      measurementCache.set(id, {
        data,
        cachedAt: Date.now()
      });

      return data;
    } finally {
      measurementRequests.delete(id);
    }
  })();

  measurementRequests.set(id, request);

  return request;
}

// --------------------------------------------------
// CUSTOM STATION ICON
// --------------------------------------------------

function createStationIcon(monitor, freshness = "unknown") {
  return divIcon({
    className: "airwise-station-icon",
    html: `
      <span class="airwise-marker-dot ${freshness}-marker ${
        monitor ? "monitor-marker" : "other-marker"
      }"></span>
    `,
    iconSize: [16, 16],
    iconAnchor: [8, 8]
  });
}

// --------------------------------------------------
// MAP ACTIONS
// --------------------------------------------------

function MapActions() {
  const map = useMap();

  return (
    <div className="map-actions">
      <button
        type="button"
        onClick={() => map.fitBounds(INDIA_BOUNDS)}
        title="Reset India view"
      >
        <RotateCcw size={16} />
        <span>Reset view</span>
      </button>

      <button
        type="button"
        onClick={() => map.setView(INDIA_CENTER, 5)}
        title="Center map on India"
      >
        <MapPin size={16} />
        <span>India</span>
      </button>

      <button
        type="button"
        onClick={() => {
          const container = map.getContainer();

          if (container.requestFullscreen) {
            container.requestFullscreen();
          }
        }}
        title="Fullscreen map"
      >
        <Maximize size={16} />
        <span>Fullscreen</span>
      </button>
    </div>
  );
}

// --------------------------------------------------
// POLLUTANT READING ROW
// --------------------------------------------------

function PollutantReading({ label, reading }) {
  if (!reading) {
    return (
      <div className="live-pollutant-row">
        <div className="live-pollutant-name">{label}</div>
        <div className="live-pollutant-unavailable">
          Not available
        </div>
      </div>
    );
  }

  const freshness = getFreshnessClass(reading.freshness);

  const validValue =
    reading.value !== null &&
    reading.value !== undefined &&
    Number.isFinite(Number(reading.value));

  return (
    <div className="live-pollutant-row">
      <div className="live-pollutant-name">{label}</div>

      <div className="live-pollutant-value">
        <strong>
          {validValue
            ? Number(reading.value).toLocaleString("en-IN", {
                maximumFractionDigits: 2
              })
            : "Unavailable"}
        </strong>

        <span>{reading.unit || ""}</span>
      </div>

      <span className={`live-freshness-badge ${freshness}`}>
        {reading.freshness || "UNKNOWN"}
      </span>
    </div>
  );
}

// --------------------------------------------------
// INDIVIDUAL STATION MARKER
// --------------------------------------------------

function StationMarker({ station }) {
  const [measurementData, setMeasurementData] = useState(null);
  const [measurementLoading, setMeasurementLoading] = useState(false);
  const [measurementError, setMeasurementError] = useState("");

  const latitude = Number(station.latitude);
  const longitude = Number(station.longitude);

  const monitor = isMonitor(station);
  const locationId = station.source_location_id;

  const loadMeasurements = useCallback(async () => {
    if (
      locationId === null ||
      locationId === undefined ||
      locationId === ""
    ) {
      setMeasurementError("Station location ID is unavailable.");
      return;
    }

    if (measurementData || measurementLoading) {
      return;
    }

    setMeasurementLoading(true);
    setMeasurementError("");

    try {
      const data = await fetchStationMeasurements(station.source, locationId);
      setMeasurementData(data);
    } catch (error) {
      console.error(
        `Measurement fetch failed for station ${locationId}:`,
        error
      );

      setMeasurementError(
        error.message || "Unable to load measurements."
      );
    } finally {
      setMeasurementLoading(false);
    }
  }, [locationId, station.source, measurementData, measurementLoading]);

  if (
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude)
  ) {
    return null;
  }

  const freshness = getStationFreshness(measurementData);

  return (
    <Marker
      position={[latitude, longitude]}
      icon={createStationIcon(monitor, freshness)}
      eventHandlers={{
        mouseover: loadMeasurements
      }}
    >
      <Tooltip
        direction="auto"
        offset={[0, 12]}
        opacity={1}
        sticky
        permanent={false}
        interactive={false}
        className="station-hover-tooltip"
      >
        <div className="station-popup">

          {/* Station header */}

          <div className="station-tooltip-header">
            <strong>
              {station.station_name || "Unnamed location"}
            </strong>

            <span
              className={
                monitor
                  ? "station-type monitor"
                  : "station-type other"
              }
            >
              {monitor ? "Monitor" : "Registered"}
            </span>
          </div>

          <div className="station-tooltip-divider" />

          {/* Station information */}

          <div className="live-station-location">
            <p>
              <b>Source</b>
              <span>{station.source || "OpenAQ"}</span>
            </p>

            <p>
              <b>Location ID</b>
              <span>{locationId ?? "Unavailable"}</span>
            </p>

            <p>
              <b>City</b>
              <span>{station.city || "Not verified"}</span>
            </p>

            <p>
              <b>District</b>
              <span>{station.district || "Not available"}</span>
            </p>

            <p>
              <b>State / UT</b>
              <span>{station.state || "Not available"}</span>
            </p>

            {!station.city && (station.district || station.state) && (
              <p>
                <b>Display location</b>
                <span>{station.location_label || [station.district, station.state].filter(Boolean).join(", ")}</span>
              </p>
            )}
          </div>

          <div className="station-tooltip-divider" />

          {/* Measurement heading */}

          <div className="live-measurement-heading">
            <div>
              <Activity size={14} />
              <strong>Latest measurements</strong>
            </div>

            {measurementLoading && (
              <LoaderCircle
                size={15}
                className="map-spinning"
              />
            )}
          </div>

          {measurementLoading && !measurementData && (
            <div className="live-measurement-message">
              <LoaderCircle
                size={16}
                className="map-spinning"
              />
              Fetching station observations...
            </div>
          )}

          {measurementError && (
            <div className="live-measurement-error">
              <AlertCircle size={14} />
              <span>{measurementError}</span>
            </div>
          )}

          {measurementData && (
            <>
              <div className="live-pollutant-list">
                {POLLUTANT_INFO.map(item => (
                  <PollutantReading
                    key={item.key}
                    label={item.label}
                    reading={measurementData.pollutants[item.key]}
                  />
                ))}
              </div>

              {/* Data quality summary */}

              <div className="live-data-summary">
                <div className="live-summary-item">
                  <span>Fresh</span>
                  <strong>
                    {measurementData.summary?.fresh ?? 0}
                  </strong>
                </div>

                <div className="live-summary-item">
                  <span>Delayed</span>
                  <strong>
                    {measurementData.summary?.delayed ?? 0}
                  </strong>
                </div>

                <div className="live-summary-item">
                  <span>Stale</span>
                  <strong>
                    {measurementData.summary?.stale ?? 0}
                  </strong>
                </div>
              </div>

              <div className="live-observation-time">
                <Clock size={12} />
                <span>
                  Retrieved:{" "}
                  {formatTimestamp(measurementData.retrieved_at)}
                </span>
              </div>

              <div className="live-observation-time">
                <Wind size={12} />
                <span>
                  Source: {measurementData.source || "OpenAQ"}
                </span>
              </div>
            </>
          )}

          {!measurementLoading &&
            !measurementData &&
            !measurementError && (
              <div className="live-measurement-message">
                Hover over this station to load its readings.
              </div>
            )}

          <div className="station-tooltip-disclaimer">
            Ground sensor observations. Marker colour represents
            measurement freshness, not pollution severity or AQI.
            Freshness is evaluated separately for each pollutant.
          </div>
        </div>
      </Tooltip>
    </Marker>
  );
}

// --------------------------------------------------
// STATION MARKERS WITH CLUSTERING
// --------------------------------------------------

function StationMarkers({ stations }) {
  return (
    <MarkerClusterGroup
      chunkedLoading
      showCoverageOnHover={false}
      zoomToBoundsOnClick
      spiderfyOnMaxZoom
      removeOutsideVisibleBounds
      animate
    >
      {stations.map(station => (
        <StationMarker
          key={`${station.source}-${station.source_location_id}`}
          station={station}
        />
      ))}
    </MarkerClusterGroup>
  );
}

// --------------------------------------------------
// MAIN POLLUTION MAP
// --------------------------------------------------

function PollutionMap() {
  const [stations, setStations] = useState([]);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [districtFilter, setDistrictFilter] = useState("");
  const [monitorOnly, setMonitorOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mapReady, setMapReady] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  // ----------------------------------------------
  // FETCH NATIONAL STATION REGISTRY
  // ----------------------------------------------

  const fetchStations = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/india/map?limit=10000`
      );

      if (!response.ok) {
        throw new Error(
          `Server returned HTTP ${response.status}`
        );
      }

      const data = await response.json();

      if (
        data.status !== "success" ||
        !Array.isArray(data.stations)
      ) {
        throw new Error("Invalid station registry response.");
      }

      const validStations = data.stations.filter(station => {
        const latitude = Number(station.latitude);
        const longitude = Number(station.longitude);

        return (
          Number.isFinite(latitude) &&
          Number.isFinite(longitude) &&
          latitude >= 5 &&
          latitude <= 37.5 &&
          longitude >= 67 &&
          longitude <= 98.5
        );
      });

      setStations(validStations);
      setLastUpdated(new Date());

    } catch (err) {
      console.error("India map API error:", err);

      setError(
        err.message ||
        "Unable to load Indian monitoring locations."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStations();
  }, [fetchStations]);

  // ----------------------------------------------
  // SEARCH AND FILTER
  // ----------------------------------------------

  const filteredStations = useMemo(() => {
    const query = search.trim().toLowerCase();

    return stations.filter(station => {
      const matchesSearch =
        !query ||
        (station.station_name || "")
          .toLowerCase()
          .includes(query) ||
        (station.city || "")
          .toLowerCase()
          .includes(query) ||
        (station.district || "")
          .toLowerCase()
          .includes(query) ||
        (station.location_label || "")
          .toLowerCase()
          .includes(query) ||
        (station.state || "")
          .toLowerCase()
          .includes(query);

      const matchesState =
        !stateFilter || (station.state || "") === stateFilter;
      const matchesDistrict =
        !districtFilter || (station.district || "") === districtFilter;
      const matchesMonitor =
        !monitorOnly || isMonitor(station);

      return matchesSearch && matchesState && matchesDistrict && matchesMonitor;
    });
  }, [stations, search, stateFilter, districtFilter, monitorOnly]);

  const stateOptions = useMemo(
    () => [...new Set(stations.map(item => item.state).filter(Boolean))].sort((a, b) => a.localeCompare(b)),
    [stations]
  );

  const districtOptions = useMemo(
    () => [...new Set(stations.filter(item => !stateFilter || item.state === stateFilter).map(item => item.district).filter(Boolean))].sort((a, b) => a.localeCompare(b)),
    [stations, stateFilter]
  );

  // ----------------------------------------------
  // STATISTICS
  // ----------------------------------------------

  const monitorCount = useMemo(
    () => stations.filter(isMonitor).length,
    [stations]
  );

  // ----------------------------------------------
  // RENDER
  // ----------------------------------------------

  return (
    <section className="pollution-map-section">

      {/* Header */}

      <div className="map-page-header">
        <div>
          <div className="map-eyebrow">
            GEOSPATIAL INTELLIGENCE
          </div>

          <h2>India Air Quality Map</h2>

          <p>
            Explore registered air-quality monitoring
            locations across India.
          </p>
        </div>

        <span className="map-live-status">
          <span className="status-dot" />
          National registry connected
        </span>
      </div>

      {/* Statistics */}

      <div className="map-statistics">
        <div className="map-stat-card">
          <MapPinned size={20} />
          <div>
            <strong>{stations.length}</strong>
            <span>Registered locations</span>
          </div>
        </div>

        <div className="map-stat-card">
          <Radio size={20} />
          <div>
            <strong>{monitorCount}</strong>
            <span>Marked as monitors</span>
          </div>
        </div>

        <div className="map-stat-card">
          <Activity size={20} />
          <div>
            <strong>{filteredStations.length}</strong>
            <span>Locations displayed</span>
          </div>
        </div>
      </div>

      {/* Toolbar */}

      <div className="map-toolbar">
        <div>
          <strong>India monitoring network</strong>
          <span>OpenAQ registered locations</span>
        </div>

        <button
          type="button"
          className="map-refresh-button"
          onClick={fetchStations}
          disabled={loading}
        >
          <RefreshCw
            size={16}
            className={loading ? "map-spinning" : ""}
          />

          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {/* Search and filters */}

      <div className="map-controls">
        <div className="map-search">
          <Search size={17} />

          <input
            type="search"
            placeholder="Search station, city, district or state..."
            value={search}
            onChange={event => setSearch(event.target.value)}
          />
        </div>

        <select
          className="map-location-select"
          value={stateFilter}
          onChange={event => {
            setStateFilter(event.target.value);
            setDistrictFilter("");
          }}
          aria-label="Filter by state or union territory"
        >
          <option value="">All states / UTs</option>
          {stateOptions.map(state => <option key={state} value={state}>{state}</option>)}
        </select>

        <select
          className="map-location-select"
          value={districtFilter}
          onChange={event => setDistrictFilter(event.target.value)}
          aria-label="Filter by district"
        >
          <option value="">All districts</option>
          {districtOptions.map(district => <option key={district} value={district}>{district}</option>)}
        </select>

        <label className="map-monitor-filter">
          <input
            type="checkbox"
            checked={monitorOnly}
            onChange={event =>
              setMonitorOnly(event.target.checked)
            }
          />

          Show monitor locations only
        </label>
      </div>

      {/* Error */}

      {error && (
        <div className="map-error">
          <AlertCircle size={18} />
          <span>{error}</span>

          <button
            type="button"
            onClick={fetchStations}
          >
            Retry
          </button>
        </div>
      )}

      {/* Map */}

      <div className="pollution-map-container">

        <MapContainer
          center={INDIA_CENTER}
          zoom={5}
          minZoom={4}
          maxZoom={14}
          maxBounds={INDIA_BOUNDS}
          maxBoundsViscosity={0.8}
          scrollWheelZoom
          zoomControl={false}
          className="india-map"
          whenReady={() => setMapReady(true)}
        >
          <LayersControl position="topright">

            <LayersControl.BaseLayer
              checked
              name="OpenStreetMap Standard"
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                maxZoom={19}
              />
            </LayersControl.BaseLayer>

            <LayersControl.BaseLayer
              name="Esri World Street Map"
            >
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
                attribution="Tiles &copy; Esri and its contributors"
                maxZoom={19}
              />
            </LayersControl.BaseLayer>

          </LayersControl>

          <StationMarkers stations={filteredStations} />

          <ZoomControl position="topleft" />

          <MapActions />
        </MapContainer>

        {!mapReady && (
          <div className="map-loading">
            Loading geographical map...
          </div>
        )}

        {loading && stations.length === 0 && (
          <div className="map-loading">
            Fetching national station registry...
          </div>
        )}

        {!loading && stations.length === 0 && !error && (
          <div className="map-loading">
            No registered locations found.
          </div>
        )}

        {!loading &&
          stations.length > 0 &&
          filteredStations.length === 0 && (
            <div className="map-information">
              <strong>No matching locations</strong>
              <p>
                Change your search or monitor filter.
              </p>
            </div>
          )}
      </div>

      {/* Freshness legend */}

      <div className="map-legend">
        <div>
          <span
            className="legend-dot"
            style={{ background: "#16a34a" }}
          />
          Fresh observations
        </div>

        <div>
          <span
            className="legend-dot"
            style={{ background: "#eab308" }}
          />
          Delayed observations
        </div>

        <div>
          <span
            className="legend-dot"
            style={{ background: "#667085" }}
          />
          Stale observations
        </div>

        <div>
          <span
            className="legend-dot"
            style={{ background: "#2E90FA" }}
          />
          Not yet verified
        </div>
      </div>

      {/* Footer */}

      <div className="map-footer">
        <span>
          Map tiles © OpenStreetMap contributors / Esri.
        </span>

        <span>Source: OpenAQ</span>

        <span>
          Last fetched:{" "}
          {lastUpdated
            ? lastUpdated.toLocaleTimeString("en-IN")
            : "Not available"}
        </span>
      </div>

      {/* Disclaimer */}

      <div className="map-disclaimer">
        <strong>Data interpretation:</strong>{" "}
        Markers represent registered OpenAQ locations.
        Marker colours represent measurement freshness,
        not pollution severity or official AQI.
        Pollutant readings are ground sensor observations.
        Freshness is evaluated separately for each reading.
      </div>

    </section>
  );
}

export default PollutionMap;
