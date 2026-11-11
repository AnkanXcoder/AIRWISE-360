
import {
  LayoutDashboard,
  Activity,
  Map,
  History,
  GitCompareArrows,
  HeartPulse,
  CloudSun,
  BrainCircuit,
  AlertTriangle,
  Flame,
  UserRound,
  ChevronRight,
  Wind,
  BookOpen
} from "lucide-react";

const navigationGroups = [
  {
    title: "MAIN MENU",
    items: [
      { name: "Overview", icon: LayoutDashboard },
      { name: "Live AQI Intelligence", icon: Activity },
      { name: "Pollution Map", icon: Map }
    ]
  },
  {
    title: "ANALYTICS",
    items: [
      { name: "Historical Tracker", icon: History },
      { name: "City Comparison", icon: GitCompareArrows },
      { name: "AQI Forecasting", icon: CloudSun }
    ]
  },
  {
    title: "INTELLIGENCE",
    items: [
      { name: "Health & Safety", icon: HeartPulse },
      { name: "Pollution Spike Detective", icon: AlertTriangle },
      { name: "Diwali Impact Intelligence", icon: Flame },
      { name: "Personal Exposure", icon: UserRound },
      { name: "ML & Data Intelligence", icon: BrainCircuit },
      { name: "Air Quality Guide", icon: BookOpen }
    ]
  }
];

const NAV_TRANSLATIONS = {
  hi: {
    "MAIN MENU": "मुख्य मेनू", "ANALYTICS": "विश्लेषण", "INTELLIGENCE": "विशेष जानकारी",
    "Overview": "अवलोकन", "Live AQI Intelligence": "लाइव AQI जानकारी", "Pollution Map": "प्रदूषण मानचित्र",
    "Historical Tracker": "ऐतिहासिक रिकॉर्ड", "City Comparison": "शहरों की तुलना", "AQI Forecasting": "AQI पूर्वानुमान",
    "Health & Safety": "स्वास्थ्य और सुरक्षा", "Pollution Spike Detective": "प्रदूषण में अचानक वृद्धि",
    "Diwali Impact Intelligence": "दिवाली प्रभाव", "Personal Exposure": "व्यक्तिगत संपर्क",
    "ML & Data Intelligence": "ML और डेटा जानकारी", "Air Quality Guide": "वायु गुणवत्ता मार्गदर्शिका"
  },
  bn: {
    "MAIN MENU": "প্রধান মেনু", "ANALYTICS": "বিশ্লেষণ", "INTELLIGENCE": "বিশেষ তথ্য",
    "Overview": "সারসংক্ষেপ", "Live AQI Intelligence": "লাইভ AQI তথ্য", "Pollution Map": "দূষণ মানচিত্র",
    "Historical Tracker": "ঐতিহাসিক তথ্য", "City Comparison": "শহরের তুলনা", "AQI Forecasting": "AQI পূর্বাভাস",
    "Health & Safety": "স্বাস্থ্য ও নিরাপত্তা", "Pollution Spike Detective": "দূষণের আকস্মিক বৃদ্ধি",
    "Diwali Impact Intelligence": "দীপাবলির প্রভাব", "Personal Exposure": "ব্যক্তিগত সংস্পর্শ",
    "ML & Data Intelligence": "ML ও ডেটা তথ্য", "Air Quality Guide": "বায়ুর গুণমান নির্দেশিকা"
  },
  mr: {
    "MAIN MENU": "मुख्य मेनू", "ANALYTICS": "विश्लेषण", "INTELLIGENCE": "माहिती",
    "Overview": "आढावा", "Live AQI Intelligence": "थेट AQI माहिती", "Pollution Map": "प्रदूषण नकाशा",
    "Historical Tracker": "ऐतिहासिक नोंदी", "City Comparison": "शहरांची तुलना", "AQI Forecasting": "AQI अंदाज",
    "Health & Safety": "आरोग्य आणि सुरक्षितता", "Pollution Spike Detective": "प्रदूषणातील अचानक वाढ",
    "Diwali Impact Intelligence": "दिवाळीचा परिणाम", "Personal Exposure": "वैयक्तिक संपर्क",
    "ML & Data Intelligence": "ML आणि डेटा माहिती", "Air Quality Guide": "हवा गुणवत्ता मार्गदर्शक"
  },
  te: {
    "MAIN MENU": "ప్రధాన మెను", "ANALYTICS": "విశ్లేషణ", "INTELLIGENCE": "సమాచారం",
    "Overview": "సారాంశం", "Live AQI Intelligence": "లైవ్ AQI సమాచారం", "Pollution Map": "కాలుష్య మ్యాప్",
    "Historical Tracker": "చారిత్రక సమాచారం", "City Comparison": "నగరాల పోలిక", "AQI Forecasting": "AQI అంచనా",
    "Health & Safety": "ఆరోగ్యం మరియు భద్రత", "Pollution Spike Detective": "కాలుష్య పెరుగుదల గుర్తింపు",
    "Diwali Impact Intelligence": "దీపావళి ప్రభావం", "Personal Exposure": "వ్యక్తిగత ప్రభావం",
    "ML & Data Intelligence": "ML మరియు డేటా సమాచారం", "Air Quality Guide": "గాలి నాణ్యత మార్గదర్శి"
  },
  ta: {
    "MAIN MENU": "முதன்மை மெனு", "ANALYTICS": "பகுப்பாய்வு", "INTELLIGENCE": "தகவல்",
    "Overview": "கண்ணோட்டம்", "Live AQI Intelligence": "நேரடி AQI தகவல்", "Pollution Map": "மாசு வரைபடம்",
    "Historical Tracker": "வரலாற்றுப் பதிவு", "City Comparison": "நகர ஒப்பீடு", "AQI Forecasting": "AQI முன்னறிவிப்பு",
    "Health & Safety": "உடல்நலம் மற்றும் பாதுகாப்பு", "Pollution Spike Detective": "மாசு திடீர் உயர்வு கண்டறிதல்",
    "Diwali Impact Intelligence": "தீபாவளி தாக்கம்", "Personal Exposure": "தனிப்பட்ட வெளிப்பாடு",
    "ML & Data Intelligence": "ML மற்றும் தரவுத் தகவல்", "Air Quality Guide": "காற்றுத் தர வழிகாட்டி"
  }
};

function Sidebar({ activePage, onNavigate, language = "en" }) {
  const labels = NAV_TRANSLATIONS[language] || {};
  return (
    <aside className="sidebar">

      <div className="sidebar-brand">
        <div className="brand-icon">
          <Wind size={25} />
        </div>

        <div>
          <h2>AIRWISE <span>360°</span></h2>
          <p>AIR QUALITY INTELLIGENCE</p>
        </div>
      </div>

      <div className="sidebar-navigation">

        {navigationGroups.map((group) => (
          <div className="nav-group" key={group.title}>

            <p className="nav-group-title">{labels[group.title] || group.title}</p>

            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.name;

              return (
                <button
                  key={item.name}
                  type="button"
                  className={`nav-item ${isActive ? "active" : ""}`}
                  onClick={() => onNavigate(item.name)}
                >
                  <Icon size={18} strokeWidth={1.8} />

                  <span>{labels[item.name] || item.name}</span>

                  {isActive && (
                    <ChevronRight
                      size={15}
                      className="nav-chevron"
                    />
                  )}
                </button>
              );
            })}

          </div>
        ))}

      </div>

      <div className="sidebar-footer">
        <div className="sidebar-footer-icon">
          <Activity size={17} />
        </div>

        <div>
          <strong>Environmental Intelligence</strong>
          <p>Predict. Detect. Protect.</p>
        </div>
      </div>

    </aside>
  );
}

export default Sidebar;
