import { useEffect, useMemo, useState } from "react";
import { AlertCircle, LoaderCircle, MapPin } from "lucide-react";
import { getIndiaFilters, getIndiaStations, getApiErrorMessage } from "../services/airwiseApi";
import "./IndiaLocationSelector.css";

/**
 * Shared administrative geography selector backed by the India station registry.
 * City options are limited to verified city records. District fallback labels
 * remain districts and are never promoted to city names.
 */
export default function IndiaLocationSelector({ onStationChange, title = "Select an Indian monitoring location", requireCoordinates = false }) {
  const [filters, setFilters] = useState(null);
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [city, setCity] = useState("");
  const [stationKey, setStationKey] = useState("");
  const [stations, setStations] = useState([]);
  const [loadingFilters, setLoadingFilters] = useState(true);
  const [loadingStations, setLoadingStations] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getIndiaFilters()
      .then(data => { if (active) setFilters(data); })
      .catch(err => { if (active) setError(getApiErrorMessage(err)); })
      .finally(() => { if (active) setLoadingFilters(false); });
    return () => { active = false; };
  }, []);

  const locationOptions = filters?.location_options || [];
  const districts = useMemo(() => [...new Set(
    locationOptions
      .filter(item => item.state === state && item.district)
      .map(item => item.district)
  )].sort((a, b) => a.localeCompare(b)), [locationOptions, state]);

  const cities = useMemo(() => [...new Set(
    locationOptions
      .filter(item => item.state === state && item.location_level === "city" && item.city && (!district || item.district === district))
      .map(item => item.city)
  )].sort((a, b) => a.localeCompare(b)), [locationOptions, state, district]);

  useEffect(() => {
    if (!state) {
      setStations([]);
      setStationKey("");
      onStationChange?.(null);
      return;
    }

    let active = true;
    setLoadingStations(true);
    setError("");
    setStationKey("");
    onStationChange?.(null);

    getIndiaStations({ page: 1, limit: 1000, state, ...(district ? { district } : {}), ...(city ? { city } : {}) })
      .then(data => {
        if (active) setStations(Array.isArray(data?.stations) ? data.stations : []);
      })
      .catch(err => { if (active) { setStations([]); setError(getApiErrorMessage(err)); } })
      .finally(() => { if (active) setLoadingStations(false); });

    return () => { active = false; };
  }, [state, district, city, onStationChange]);

  const coordinateValidStations = requireCoordinates
    ? stations.filter(item =>
        item.latitude !== null &&
        item.latitude !== undefined &&
        item.latitude !== "" &&
        item.longitude !== null &&
        item.longitude !== undefined &&
        item.longitude !== "" &&
        Number.isFinite(Number(item.latitude)) &&
        Number.isFinite(Number(item.longitude)) &&
        Number(item.latitude) >= -90 &&
        Number(item.latitude) <= 90 &&
        Number(item.longitude) >= -180 &&
        Number(item.longitude) <= 180
      )
    : stations;

  // The upstream registry can contain duplicate representations of the same
  // station. Collapse only exact same-name/same-coordinate duplicates; retain
  // distinct source IDs when coordinates or station names differ.
  const availableStations = useMemo(() => {
    const seen = new Set();
    return coordinateValidStations.filter(item => {
      const stationName = String(item.station_name || "").trim().toLowerCase();
      const latitude = item.latitude == null ? "" : Number(item.latitude).toFixed(5);
      const longitude = item.longitude == null ? "" : Number(item.longitude).toFixed(5);
      const location = String(item.location_label || item.display_area || item.district || "").trim().toLowerCase();
      const signature = [stationName, location, latitude, longitude].join("|");
      if (seen.has(signature)) return false;
      seen.add(signature);
      return true;
    });
  }, [coordinateValidStations]);
  const selectedStation = availableStations.find(item => `${item.source}:${item.source_location_id}` === stationKey) || null;

  const handleStationChange = value => {
    setStationKey(value);
    const station = availableStations.find(item => `${item.source}:${item.source_location_id}` === value) || null;
    onStationChange?.(station);
  };

  if (loadingFilters) {
    return <div className="india-location-status"><LoaderCircle size={16} className="india-location-spin" /> Loading India location registry…</div>;
  }

  return (
    <section className="india-location-selector" aria-label={title}>
      <div className="india-location-heading">
        <MapPin size={18} />
        <div><strong>{title}</strong><small>State → District → Verified city → Monitoring station</small></div>
      </div>

      <div className="india-location-fields">
        <label>State / UT
          <select value={state} onChange={event => { setState(event.target.value); setDistrict(""); setCity(""); }}>
            <option value="">Select state / UT</option>
            {(filters?.states || []).map(item => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>

        <label>District
          <select value={district} disabled={!state} onChange={event => { setDistrict(event.target.value); setCity(""); }}>
            <option value="">All districts</option>
            {districts.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>

        <label>Verified city
          <select value={city} disabled={!state || cities.length === 0} onChange={event => setCity(event.target.value)}>
            <option value="">All verified cities</option>
            {cities.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>

        <label>Monitoring station
          <select value={stationKey} disabled={!state || loadingStations || availableStations.length === 0} onChange={event => handleStationChange(event.target.value)}>
            <option value="">{loadingStations ? "Loading stations…" : stations.length ? "Select station" : "No stations available"}</option>
            {availableStations.map(item => {
              const key = `${item.source}:${item.source_location_id}`;
              return <option key={key} value={key}>{item.station_name} · {item.location_label || item.display_area || item.state}</option>;
            })}
          </select>
        </label>
      </div>

      {error && <div className="india-location-error"><AlertCircle size={15} />{error}</div>}
      {selectedStation && <p className="india-location-selected">Selected: <strong>{selectedStation.station_name}</strong> · {selectedStation.location_label || selectedStation.state} · {selectedStation.location_level || "location level unavailable"}</p>}
      {!error && state && !loadingStations && availableStations.length === 0 && <p className="india-location-empty">No registered stations match this geographic selection.</p>}
    </section>
  );
}
