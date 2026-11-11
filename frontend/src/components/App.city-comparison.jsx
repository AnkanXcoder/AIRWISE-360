
import { useEffect, useState } from "react";

import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import PollutantGrid from "./components/PollutantGrid";
import PollutionMap from "./components/PollutionMap";
import HistoricalTracker from "./components/HistoricalTracker";
import CityComparison from "./components/CityComparison";

import useStationData from "./hooks/useStationData";
import StationInfo from "./components/StationInfo";

import {
  Activity,
  Map,
  TrendingUp,
  HeartPulse,
  CloudSun,
  ShieldCheck
} from "lucide-react";

import "./App.css";

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

function Overview() {
  const {
    data,
    loading,
    refreshing,
    error,
    lastUpdated,
    refresh
  } = useStationData(6950);

  const stationName = data?.station?.name || "Jadavpur";
  const cityName = data?.station?.city || "Kolkata";

  return (
    <div className="dashboard-content">

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


      <div className="section-header">
        <div>
          <h3>Monitoring Overview</h3>
          <p>Current application connection status</p>
        </div>
      </div>


      <section className="overview-grid">

        <div className="overview-card">
          <span>LIVE AQI</span>

          <h2>Not calculated</h2>

          <p>
            Pollutant measurements connected.
            Official CPCB AQI calculation pending.
          </p>
        </div>


        <div className="overview-card">
          <span>MONITORING NETWORK</span>

          <h2>
            {loading
              ? "Loading..."
              : data
                ? "1 station connected"
                : "Unavailable"}
          </h2>

          <p>
            {stationName}, {cityName}
          </p>
        </div>


        <div className="overview-card">
          <span>AIR QUALITY FORECAST</span>

          <h2>Not connected</h2>

          <p>Forecast integration pending</p>
        </div>

      </section>


      <StationInfo data={data} />

      <PollutantGrid
        data={data}
        loading={loading}
        error={error}
      />


      <div className="section-header">
        <div>
          <h3>Intelligence Modules</h3>
          <p>Explore the AIRWISE platform capabilities</p>
        </div>
      </div>


      <section className="module-grid">

        {modules.map(module => {
          const Icon = module.icon;

          return (
            <article
              className="dashboard-module"
              key={module.title}
            >
              <div className="module-icon">
                <Icon size={21} />
              </div>

              <h4>{module.title}</h4>

              <p>{module.description}</p>
            </article>
          );
        })}

      </section>


      <div className="data-notice">
        <ShieldCheck size={19} />

        <p>
          Data transparency: Live readings and forecasts will only
          appear when verified source data is available.
        </p>
      </div>

    </div>
  );
}


// --------------------------------------------------
// APP
// --------------------------------------------------

function App() {

  const [theme, setTheme] = useState(
    () => localStorage.getItem("airwise-theme") || "light"
  );

  const [activePage, setActivePage] = useState("Overview");


  // ----------------------------------------------
  // THEME MANAGEMENT
  // ----------------------------------------------

  useEffect(() => {

    document.documentElement.setAttribute("data-theme", theme);

    localStorage.setItem("airwise-theme", theme);

  }, [theme]);


  const toggleTheme = () => {

    setTheme(current =>
      current === "light" ? "dark" : "light"
    );

  };


  // ----------------------------------------------
  // PAGE RENDERING
  // ----------------------------------------------

  const renderPage = () => {

    switch (activePage) {

      case "Overview":

        return <Overview />;


      case "Pollution Map":

        return <PollutionMap />;


      case "Historical Tracker":

        return <HistoricalTracker />;


      case "City Comparison":

        return <CityComparison />;


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
      />


      <main className="main-layout">

        <Navbar
          activePage={activePage}
          theme={theme}
          onToggleTheme={toggleTheme}
        />


        <div className="dashboard-content">

          {renderPage()}

        </div>

      </main>

    </div>

  );

}


export default App;
