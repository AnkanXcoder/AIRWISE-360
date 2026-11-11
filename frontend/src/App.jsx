
import { Component, useEffect, useState, lazy, Suspense } from "react";

import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import useStationData from "./hooks/useStationData";

import {
  getIndiaFilters,
  getIndiaStations
} from "./services/airwiseApi";

import {
  Activity,
  Map,
  TrendingUp,
  HeartPulse,
  CloudSun,
  ShieldCheck
} from "lucide-react";

import "./App.css";

class PageErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message || "This module could not be displayed." };
  }
  componentDidCatch(error) {
    console.error("AIRWISE page rendering error:", error);
  }
  render() {
    if (this.state.hasError) {
      return (
        <section className="page-placeholder" role="alert">
          <h2>This AIRWISE module could not load</h2>
          <p>{this.state.message}</p>
          <button type="button" onClick={() => this.setState({ hasError: false, message: "" })}>Try again</button>
        </section>
      );
    }
    return this.props.children;
  }
}

// --------------------------------------------------
// LAZY-LOADED DASHBOARD COMPONENTS
// --------------------------------------------------

const PollutantGrid = lazy(() =>
  import("./components/PollutantGrid")
);

const PollutionMap = lazy(() =>
  import("./components/PollutionMap")
);

const HistoricalTracker = lazy(() =>
  import("./components/HistoricalTracker")
);

const CityComparison = lazy(() =>
  import("./components/CityComparison")
);

const StationInfo = lazy(() =>
  import("./components/StationInfo")
);

const AQIForecasting = lazy(() =>
  import("./components/AQIForecasting")
);

const HealthSafety = lazy(() =>
  import("./components/HealthSafety")
);

const PollutionSpikeDetector = lazy(() =>
  import("./components/PollutionSpikeDetector")
);

const DiwaliImpact = lazy(() =>
  import("./components/DiwaliImpact")
);

const PersonalExposure = lazy(() =>
  import("./components/PersonalExposure")
);

const MLDataIntelligence = lazy(() =>
  import("./components/MLDataIntelligence")
);

const AirQualityGuide = lazy(() =>
  import("./components/AirQualityGuide")
);


// --------------------------------------------------
// MODULE INFORMATION
// --------------------------------------------------

const modules = [
  {
    title: "Live AQI Intelligence",
    description: "Monitor air quality and pollutant measurements.",
    icon: Activity
  },
  {
    title: "Pollution Map",
    description: "Explore monitoring stations across India.",
    icon: Map
  },
  {
    title: "Historical Tracker",
    description: "Understand pollution trends over time.",
    icon: TrendingUp
  },
  {
    title: "Health & Safety",
    description: "Explore health guidance and exposure risks.",
    icon: HeartPulse
  },
  {
    title: "AQI Forecasting",
    description: "Explore modelled future air-quality conditions.",
    icon: CloudSun
  },
  {
    title: "Data Trust Engine",
    description: "Monitor data quality and source reliability.",
    icon: ShieldCheck
  }
];


// --------------------------------------------------
// OVERVIEW PAGE
// --------------------------------------------------

function Overview({ onNavigate, mode = "Overview" }) {

  // ----------------------------------------------
  // LOCATION AND STATION STATES
  // ----------------------------------------------

  const [filters, setFilters] = useState(null);

  const [selectedState, setSelectedState] = useState("");
  const [selectedLocation, setSelectedLocation] = useState("");
  const [selectedStationId, setSelectedStationId] = useState("");

  const [stations, setStations] = useState([]);

  const [filtersLoading, setFiltersLoading] = useState(true);
  const [stationsLoading, setStationsLoading] = useState(false);

  const [filtersError, setFiltersError] = useState("");
  const [stationsError, setStationsError] = useState("");


  // ----------------------------------------------
  // LOAD INDIA LOCATION FILTERS
  // ----------------------------------------------

  useEffect(() => {

    let cancelled = false;

    async function loadFilters() {

      try {

        setFiltersLoading(true);
        setFiltersError("");

        const result = await getIndiaFilters();

        if (!cancelled) {
          setFilters(result);
        }

      } catch (error) {

        if (!cancelled) {

          setFiltersError(
            error.response?.data?.detail ||
            error.message ||
            "Unable to load location filters."
          );

        }

      } finally {

        if (!cancelled) {
          setFiltersLoading(false);
        }

      }

    }

    loadFilters();

    return () => {
      cancelled = true;
    };

  }, []);


  // ----------------------------------------------
  // FILTER LOCATIONS BY SELECTED STATE
  // ----------------------------------------------

  const locationOptions = (
    filters?.location_options || []
  ).filter(
    (option) => option.state === selectedState
  );


  const selectedLocationOption = locationOptions.find(
    (option) => option.district === selectedLocation
  );


  // ----------------------------------------------
  // LOAD STATIONS BY STATE AND DISTRICT
  // ----------------------------------------------

  useEffect(() => {

    let cancelled = false;

    async function loadStations() {

      if (!selectedState || !selectedLocation) {

        setStations([]);
        setStationsError("");
        return;

      }

      try {

        setStationsLoading(true);
        setStationsError("");

        setStations([]);
        setSelectedStationId("");

        const result = await getIndiaStations({

          state: selectedState,
          district: selectedLocation,
          page: 1,
          limit: 1000

        });

        if (!cancelled) {

          setStations(result.stations || []);

        }

      } catch (error) {

        if (!cancelled) {

          setStations([]);

          setStationsError(
            error.response?.data?.detail ||
            error.message ||
            "Unable to load monitoring stations."
          );

        }

      } finally {

        if (!cancelled) {
          setStationsLoading(false);
        }

      }

    }

    loadStations();

    return () => {
      cancelled = true;
    };

  }, [selectedState, selectedLocation]);


  // ----------------------------------------------
  // GET SELECTED STATION
  // ----------------------------------------------

  const selectedStation = stations.find(
    (station) =>
      `${station.source}:${station.source_location_id}` ===
      selectedStationId
  );


  // ----------------------------------------------
  // FETCH SELECTED STATION MEASUREMENTS
  // ----------------------------------------------

  const {
    data,
    loading,
    refreshing,
    error,
    lastUpdated,
    refresh
  } = useStationData(
    selectedStation?.source,
    selectedStation?.source_location_id
  );


  // ----------------------------------------------
  // HANDLE DUPLICATE LOCATION LABELS
  // ----------------------------------------------

  const duplicateLabels = locationOptions.reduce(
    (counts, option) => {

      counts[option.label] =
        (counts[option.label] || 0) + 1;

      return counts;

    },
    {}
  );


  function getLocationLabel(option) {

    if (
      option.location_level === "city" &&
      duplicateLabels[option.label] > 1
    ) {

      return `${option.label} (${option.district})`;

    }

    return option.label;

  }


  // ----------------------------------------------
  // FILTER MONITORING STATIONS
  // ----------------------------------------------

  const monitoringStations = stations.filter(
    (station) => Number(station.is_monitor) === 1
  );


  // ----------------------------------------------
  // SELECTED STATION INFORMATION
  // ----------------------------------------------

  const stationName =
    selectedStation?.station_name || "No station selected";

  const locationName =
    selectedStation?.location_label || "No location selected";


  // ----------------------------------------------
  // DEDICATED LIVE AQI INTELLIGENCE PAGE
  // The same component instance owns the selectors and
  // station state on both pages, so navigation preserves
  // the selected station and its measurements.
  // ----------------------------------------------

  if (mode === "Live AQI Intelligence") {
    return (
      <div className="dashboard-content">

        <section className="welcome-section">
          <div>
            <span className="welcome-label">REAL-TIME SENSOR MONITORING</span>
            <h1>Live AQI Intelligence</h1>
            <p>
              Inspect verified ground-sensor observations, pollutant
              freshness and station-level data quality across India.
            </p>
          </div>
          <div className="welcome-icon">
            <Activity size={43} />
          </div>
        </section>

        <div className="section-header">
          <div>
            <h3>India Monitoring Network</h3>
            <p>Select a state, district and monitoring station.</p>
          </div>
        </div>

        <section className="overview-grid">

          <div className="overview-card">
            <span>STATE / UNION TERRITORY</span>
            <select
              value={selectedState}
              onChange={(event) => {
                setSelectedState(event.target.value);
                setSelectedLocation("");
                setSelectedStationId("");
                setStations([]);
                setStationsError("");
              }}
              disabled={filtersLoading || !filters}
            >
              <option value="">
                {filtersLoading ? "Loading states..." : "Select state"}
              </option>
              {(filters?.states || []).map((state) => (
                <option key={state} value={state}>{state}</option>
              ))}
            </select>
          </div>

          <div className="overview-card">
            <span>CITY / DISTRICT</span>
            <select
              value={selectedLocation}
              onChange={(event) => {
                setSelectedLocation(event.target.value);
                setSelectedStationId("");
                setStationsError("");
              }}
              disabled={!selectedState || filtersLoading}
            >
              <option value="">Select location</option>
              {locationOptions.map((option) => (
                <option
                  key={`${option.state}:${option.district}`}
                  value={option.district}
                >
                  {getLocationLabel(option)}
                </option>
              ))}
            </select>
          </div>

          <div className="overview-card">
            <span>MONITORING STATION</span>
            <select
              value={selectedStationId}
              onChange={(event) => setSelectedStationId(event.target.value)}
              disabled={
                !selectedLocation ||
                stationsLoading ||
                monitoringStations.length === 0
              }
            >
              <option value="">
                {stationsLoading ? "Loading stations..." : "Select monitoring station"}
              </option>
              {monitoringStations.map((station) => (
                <option
                  key={`${station.source}:${station.source_location_id}`}
                  value={`${station.source}:${station.source_location_id}`}
                >
                  {station.station_name}
                </option>
              ))}
            </select>
          </div>

        </section>

        {filtersError && (
          <p className="error-message">Location API error: {filtersError}</p>
        )}
        {stationsError && (
          <p className="error-message">Station API error: {stationsError}</p>
        )}

        {selectedLocationOption && (
          <div className="data-notice">
            <ShieldCheck size={19} />
            <p>
              Location level: {selectedLocationOption.location_level}.
              {" "}Registered locations: {selectedLocationOption.station_count}.
            </p>
          </div>
        )}

        <div className="section-header">
          <div>
            <h3>Live Monitoring Status</h3>
            <p>Connection and retrieval status for the selected ground station.</p>
          </div>
          {selectedStation && (
            <button
              type="button"
              onClick={refresh}
              disabled={loading || refreshing}
            >
              {refreshing ? "Refreshing..." : "Refresh measurements"}
            </button>
          )}
        </div>

        <section className="overview-grid">
          <div className="overview-card">
            <span>SELECTED STATION</span>
            <h2>{selectedStation ? stationName : "No station selected"}</h2>
            <p>{selectedStation ? locationName : "Choose a station above to load observations."}</p>
          </div>

          <div className="overview-card">
            <span>SENSOR DATA STATUS</span>
            <h2>
              {!selectedStation
                ? "Waiting for selection"
                : loading
                  ? "Loading measurements..."
                  : error
                    ? "Data unavailable"
                    : data
                      ? "Station connected"
                      : "No measurement data"}
            </h2>
            <p>
              {data?.source
                ? `Source: ${data.source}`
                : "Sensor observations are loaded from the selected station."}
            </p>
          </div>

          <div className="overview-card">
            <span>OFFICIAL AQI</span>
            <h2>Not calculated</h2>
            <p>
              Ground-sensor pollutant readings are not an official AQI.
              CPCB-compatible AQI calculation is not connected yet.
            </p>
          </div>
        </section>

        {selectedStation ? (
          <>
            {lastUpdated && (
              <p className="data-meta">Last retrieved: {lastUpdated}</p>
            )}

            <div className="section-header">
              <div>
                <h3>Monitoring Station Information</h3>
                <p>Station identity, provider, coordinates and data quality.</p>
              </div>
            </div>

            <StationInfo data={data} />

            <div className="section-header">
              <div>
                <h3>Pollutant Intelligence</h3>
                <p>Individual sensor observations with their original units and freshness.</p>
              </div>
            </div>

            <PollutantGrid
              data={data}
              loading={loading}
              error={error}
            />

            <div className="data-notice">
              <ShieldCheck size={19} />
              <p>
                Data transparency: values retain their source measurement units.
                Delayed or stale readings are identified separately and are not
                presented as fresh observations.
              </p>
            </div>
          </>
        ) : (
          <div className="data-notice">
            <ShieldCheck size={19} />
            <p>
              Select a monitoring station to view its sensor measurements.
              AIRWISE does not automatically select a station.
            </p>
          </div>
        )}

      </div>
    );
  }


  // ----------------------------------------------
  // OVERVIEW UI
  // ----------------------------------------------

  return (

    <div className="dashboard-content">

      {/* WELCOME SECTION */}

      <section className="welcome-section">

        <div>

          <span className="welcome-label">
            ENVIRONMENTAL INTELLIGENCE PLATFORM
          </span>

          <h1>Welcome to AIRWISE 360°</h1>

          <p>
            Understand air quality. Discover pollution patterns.
            Make informed environmental decisions.
          </p>

        </div>

        <div className="welcome-icon">
          <Activity size={43} />
        </div>

      </section>


      {/* LOCATION AND STATION SELECTORS */}

      <div className="section-header">

        <div>
          <h3>India Monitoring Network</h3>

          <p>
            Select a state, location and monitoring station.
          </p>
        </div>

      </div>


      <section className="overview-grid">

        {/* STATE SELECTOR */}

        <div className="overview-card">

          <span>STATE / UNION TERRITORY</span>

          <select
            value={selectedState}
            onChange={(event) => {

              setSelectedState(event.target.value);

              setSelectedLocation("");
              setSelectedStationId("");

              setStations([]);
              setStationsError("");

            }}
            disabled={filtersLoading || !filters}
          >

            <option value="">
              {filtersLoading
                ? "Loading states..."
                : "Select state"}
            </option>

            {(filters?.states || []).map((state) => (

              <option key={state} value={state}>
                {state}
              </option>

            ))}

          </select>

        </div>


        {/* LOCATION SELECTOR */}

        <div className="overview-card">

          <span>CITY / DISTRICT</span>

          <select
            value={selectedLocation}
            onChange={(event) => {

              setSelectedLocation(event.target.value);
              setSelectedStationId("");

              setStationsError("");

            }}
            disabled={!selectedState || filtersLoading}
          >

            <option value="">
              Select location
            </option>

            {locationOptions.map((option) => (

              <option
                key={`${option.state}:${option.district}`}
                value={option.district}
              >

                {getLocationLabel(option)}

              </option>

            ))}

          </select>

        </div>


        {/* MONITORING STATION SELECTOR */}

        <div className="overview-card">

          <span>MONITORING STATION</span>

          <select
            value={selectedStationId}
            onChange={(event) =>
              setSelectedStationId(event.target.value)
            }
            disabled={
              !selectedLocation ||
              stationsLoading ||
              monitoringStations.length === 0
            }
          >

            <option value="">

              {stationsLoading
                ? "Loading stations..."
                : "Select monitoring station"}

            </option>

            {monitoringStations.map((station) => (

              <option
                key={`${station.source}:${station.source_location_id}`}
                value={`${station.source}:${station.source_location_id}`}
              >

                {station.station_name}

              </option>

            ))}

          </select>

        </div>

      </section>


      {/* LOCATION AND API STATUS */}

      {filtersError && (
        <p className="error-message">
          Location API error: {filtersError}
        </p>
      )}

      {stationsError && (
        <p className="error-message">
          Station API error: {stationsError}
        </p>
      )}

      {selectedLocationOption && (

        <div className="data-notice">

          <ShieldCheck size={19} />

          <p>

            Location level: {selectedLocationOption.location_level}.
            Registered locations: {selectedLocationOption.station_count}.

          </p>

        </div>

      )}

      {selectedLocation && !stationsLoading &&
        !stationsError && monitoringStations.length === 0 && (

          <p>
            No monitoring stations are currently listed for this location.
          </p>

        )}


      {/* MONITORING OVERVIEW */}

      <div className="section-header">

        <div>

          <h3>Monitoring Overview</h3>

          <p>
            Current selected station connection status
          </p>

        </div>

      </div>


      <section className="overview-grid">

        {/* LIVE AQI */}

        <div className="overview-card">

          <span>LIVE AQI</span>

          <h2>Not calculated</h2>

          <p>
            Ground sensor measurements are available when a
            station is selected. Official CPCB AQI calculation
            is not connected yet.
          </p>

        </div>


        {/* MONITORING NETWORK */}

        <div className="overview-card">

          <span>MONITORING NETWORK</span>

          <h2>

            {selectedStation
              ? loading
                ? "Loading measurements..."
                : data
                  ? "Station connected"
                  : "Selected"
              : "No station selected"}

          </h2>

          <p>{stationName}</p>

          <p>{locationName}</p>

        </div>


        {/* FORECAST */}

        <div className="overview-card">

          <span>AIR QUALITY FORECAST</span>

          <h2>Not connected</h2>

          <p>
            Forecast integration is separate from ground sensor
            observations.
          </p>

        </div>

      </section>


      {/* SELECTED STATION DETAILS */}

      {selectedStation && (

        <>

          <div className="section-header">

            <div>

              <h3>{stationName}</h3>

              <p>{locationName}</p>

            </div>

            <button
              onClick={refresh}
              disabled={loading || refreshing}
            >

              {refreshing
                ? "Refreshing..."
                : "Refresh measurements"}

            </button>

          </div>


          {lastUpdated && (

            <p>
              Last retrieved: {lastUpdated}
            </p>

          )}


          <StationInfo data={data} />

          <PollutantGrid
            data={data}
            loading={loading}
            error={error}
          />

        </>

      )}


      {!selectedStation && (

        <div className="data-notice">

          <ShieldCheck size={19} />

          <p>
            Select a monitoring station to view its sensor
            measurements. No station is selected automatically.
          </p>

        </div>

      )}


      {/* INTELLIGENCE MODULES */}

      <div className="section-header">

        <div>

          <h3>Intelligence Modules</h3>

          <p>
            Explore the AIRWISE platform capabilities
          </p>

        </div>

      </div>


      <section className="module-grid">

        {modules.map((module) => {

          const Icon = module.icon;

          return (

            <button
              type="button"
              className="dashboard-module"
              key={module.title}
              onClick={() => onNavigate({
                "Live AQI Intelligence": "Live AQI Intelligence",
                "Pollution Map": "Pollution Map",
                "Historical Tracker": "Historical Tracker",
                "Health & Safety": "Health & Safety",
                "AQI Forecasting": "AQI Forecasting",
                "Data Trust Engine": "ML & Data Intelligence"
              }[module.title])}
              aria-label={`Open ${module.title}`}
            >
              <div className="module-icon">
                <Icon size={21} />
              </div>
              <h4>{module.title}</h4>
              <p>{module.description}</p>
              <span className="module-open-label">Open module →</span>
            </button>

          );

        })}

      </section>


      {/* DATA TRANSPARENCY NOTICE */}

      <div className="data-notice">

        <ShieldCheck size={19} />

        <p>
          Data transparency: Live readings and forecasts will
          only appear when verified source data is available.
          Missing pollutant measurements are not treated as zero.
        </p>

      </div>

    </div>

  );

}


// --------------------------------------------------
// MAIN APPLICATION
// --------------------------------------------------

function App() {

  const [theme, setTheme] = useState(
    () => localStorage.getItem("airwise-theme") || "light"
  );

  const [activePage, setActivePage] = useState("Overview");
  const [language, setLanguage] = useState(
    () => localStorage.getItem("airwise-language") || "en"
  );

  const changeLanguage = (nextLanguage) => {
    setLanguage(nextLanguage);
    localStorage.setItem("airwise-language", nextLanguage);
  };


  // ----------------------------------------------
  // THEME MANAGEMENT
  // ----------------------------------------------

  useEffect(() => {

    document.documentElement.setAttribute(
      "data-theme",
      theme
    );

    localStorage.setItem("airwise-theme", theme);

  }, [theme]);


  const toggleTheme = () => {

    setTheme((current) =>
      current === "light" ? "dark" : "light"
    );

  };


  // ----------------------------------------------
  // PAGE RENDERING
  // ----------------------------------------------

  const renderPage = () => {

    switch (activePage) {

      case "Overview":
      case "Live AQI Intelligence":
        return (
          <Overview
            mode={activePage}
            onNavigate={setActivePage}
          />
        );

      case "Pollution Map":
        return <PollutionMap />;

      case "Historical Tracker":
        return <HistoricalTracker />;

      case "City Comparison":
        return <CityComparison />;

      case "AQI Forecasting":
        return <AQIForecasting />;

      case "Health & Safety":
        return <HealthSafety />;

      case "Pollution Spike Detective":
        return <PollutionSpikeDetector />;

      case "Diwali Impact Intelligence":
        return <DiwaliImpact />;

      case "Personal Exposure":
        return <PersonalExposure />;

      case "ML & Data Intelligence":
        return <MLDataIntelligence />;

      case "Air Quality Guide":
        return <AirQualityGuide />;

      default:

        return (

          <section className="page-placeholder">

            <h1>{activePage}</h1>

            <p>
              This module is being developed.
              Verified environmental data will be integrated here.
            </p>

          </section>

        );

    }

  };


  // ----------------------------------------------
  // MAIN LAYOUT
  // ----------------------------------------------

  return (

    <div className="app-layout">

      <Sidebar
        activePage={activePage}
        onNavigate={setActivePage}
        language={language}
      />


      <main className="main-layout">

        <Navbar
          activePage={activePage}
          theme={theme}
          onToggleTheme={toggleTheme}
          language={language}
          onLanguageChange={changeLanguage}
        />


        <div className="dashboard-content">

          <PageErrorBoundary>
            <Suspense
              fallback={
                <div className="page-loading" role="status">
                  Loading AIRWISE module...
                </div>
              }
            >
              {renderPage()}
            </Suspense>
          </PageErrorBoundary>

        </div>

      </main>

    </div>

  );

}


export default App;
