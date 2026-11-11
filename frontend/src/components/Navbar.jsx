
import { Search, Bell, UserCircle } from "lucide-react";
import ThemeToggle from "./ThemeToggle";

const LANGUAGE_OPTIONS = [
  ["en", "English"], ["hi", "हिन्दी"], ["bn", "বাংলা"],
  ["mr", "मराठी"], ["te", "తెలుగు"], ["ta", "தமிழ்"]
];

function Navbar({ activePage, theme, onToggleTheme, language = "en", onLanguageChange }) {
  return (
    <header className="top-navbar">

      <div className="navbar-page-info">
        <div className="breadcrumb">
          Workspace <span>/</span> {activePage}
        </div>

        <h2>{activePage}</h2>
      </div>

      <div className="navbar-actions">

        <div className="navbar-search">
          <Search size={17} />
          <input
            type="search"
            placeholder="Search AIRWISE..."
            aria-label="Search AIRWISE"
          />
          <span className="search-shortcut">/</span>
        </div>

        <label className="navbar-language-control" title="Choose interface language">
          <span className="sr-only">Language</span>
          <select value={language} onChange={event => onLanguageChange?.(event.target.value)} aria-label="Choose language">
            {LANGUAGE_OPTIONS.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
          </select>
        </label>

        <ThemeToggle
          theme={theme}
          onToggle={onToggleTheme}
        />

        <button
          type="button"
          className="notification-button"
          aria-label="Notifications"
          title="Notifications"
        >
          <Bell size={19} />
          <span className="notification-dot" />
        </button>

        <div className="navbar-profile">
          <UserCircle size={30} />
          <div>
            <strong>Administrator</strong>
            <span>Air Quality Analyst</span>
          </div>
        </div>

      </div>

    </header>
  );
}

export default Navbar;
