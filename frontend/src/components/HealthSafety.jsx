import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle, Activity, HeartPulse, ShieldCheck, Wind,
  RefreshCw, Users, Home, Stethoscope
} from "lucide-react";
import { getHealthGuidance, getApiErrorMessage } from "../services/airwiseApi";
import "./HealthSafety.css";

const GUIDANCE_SECTIONS = [
  { key: "general", title: "General guidance", description: "Understanding current air-quality information", icon: Activity },
  { key: "sensitive", title: "Sensitive groups", description: "Additional care for people who may be more vulnerable", icon: HeartPulse },
  { key: "activity", title: "Outdoor activity", description: "Planning time outdoors", icon: Wind },
  { key: "ventilation", title: "Indoor ventilation", description: "Deciding when to bring outdoor air indoors", icon: Home },
  { key: "mask", title: "Respiratory protection", description: "Reducing particle exposure when outdoors", icon: ShieldCheck }
];

export default function HealthSafety() {
  const [guidance, setGuidance] = useState(null);
  const [sensitiveGroup, setSensitiveGroup] = useState(false);
  const [symptoms, setSymptoms] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadGuidance = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError("");

    try {
      const result = await getHealthGuidance({
        sourceType: "unknown",
        sensitiveGroup,
        symptoms
      });
      if (!result || typeof result !== "object" || !result.guidance) {
        throw new Error("Health guidance API returned an unexpected response.");
      }
      setGuidance(result);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [sensitiveGroup, symptoms]);

  useEffect(() => {
    loadGuidance();
  }, [loadGuidance]);

  return (
    <main className="health-safety-page">
      <header className="health-header">
        <div>
          <span className="health-eyebrow">AIRWISE 360° · ENVIRONMENTAL HEALTH</span>
          <h2>Health &amp; Safety Intelligence</h2>
          <p>Practical educational guidance based on the air-quality information currently available.</p>
        </div>
        <button className="health-refresh" onClick={() => loadGuidance(true)} disabled={loading || refreshing}>
          <RefreshCw size={16} className={refreshing ? "health-spin" : ""} />
          {refreshing ? "Refreshing..." : "Refresh guidance"}
        </button>
      </header>

      <section className="health-status-card">
        <div className="health-status-icon"><AlertTriangle size={25} /></div>
        <div className="health-status-content">
          <span className="health-status-label">Official air-quality status</span>
          <h3>{guidance?.status === "official_aqi_unavailable" ? "Official AQI unavailable" : guidance?.aqi_category || "Checking availability"}</h3>
          <p>
            {guidance?.official_aqi == null
              ? "No verified official CPCB AQI value is available for this selection."
              : `Official AQI: ${guidance.official_aqi}`}
          </p>
        </div>
        <span className="health-status-badge">Not verified</span>
      </section>

      {error && (
        <div className="health-error">
          <AlertTriangle size={18} />
          <span>{error}{guidance ? " Showing the last successful guidance." : ""}</span>
          {!guidance && <button onClick={() => loadGuidance()}>Retry</button>}
        </div>
      )}

      <section className="health-preferences">
        <div className="health-section-title">
          <div><h3>Personal guidance context</h3><p>These options tailor the wording of general guidance. They do not diagnose a condition.</p></div>
          <Users size={21} />
        </div>
        <label className="health-toggle-row">
          <span><strong>Sensitive-group consideration</strong><small>Consider guidance for children, older adults, or people with heart or lung conditions.</small></span>
          <input type="checkbox" checked={sensitiveGroup} onChange={event => setSensitiveGroup(event.target.checked)} />
        </label>
        <label className="health-toggle-row">
          <span><strong>Currently experiencing symptoms</strong><small>Use this to request the API's symptom-aware general guidance.</small></span>
          <input type="checkbox" checked={symptoms} onChange={event => setSymptoms(event.target.checked)} />
        </label>
        <button className="health-apply" onClick={() => loadGuidance(true)} disabled={loading || refreshing}>
          Update guidance
        </button>
      </section>

      <section className="health-guidance-section">
        <div className="health-section-title">
          <div><h3>Recommended precautions</h3><p>Guidance returned by the AIRWISE health endpoint.</p></div>
          <Stethoscope size={21} />
        </div>
        {loading && !guidance ? (
          <div className="health-loading"><RefreshCw className="health-spin" /> Loading health guidance...</div>
        ) : (
          <div className="health-guidance-grid">
            {GUIDANCE_SECTIONS.map(({ key, title, description, icon: Icon }) => (
              <article className="health-guidance-card" key={key}>
                <div className="health-card-icon"><Icon size={20} /></div>
                <div><h4>{title}</h4><p className="health-card-description">{description}</p></div>
                <p className="health-card-guidance">{guidance?.guidance?.[key] || "Guidance is currently unavailable."}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="health-integrity">
        <ShieldCheck size={20} />
        <div>
          <strong>Data integrity and interpretation</strong>
          <p>Individual sensor pollutant concentrations are not official CPCB AQI. AIRWISE does not assign an AQI category unless an official CPCB AQI value and source are available. Modelled forecasts must also be interpreted separately from ground-station observations.</p>
        </div>
      </section>

      <p className="health-disclaimer">
        {guidance?.disclaimer || "General educational guidance only. This is not a medical diagnosis or a substitute for professional medical advice."}
        {" "}If you are experiencing severe or worsening symptoms, seek appropriate medical care.
      </p>
    </main>
  );
}
