import { useState } from "react";
import { BookOpen, Search, ShieldAlert } from "lucide-react";

const CONTENT = {
  en: {
    title: "Understand the air you breathe",
    subtitle: "Simple explanations of air-quality terms and how they can affect health.",
    search: "Search a term, for example PM2.5",
    terms: [
      ["AQI", "Air Quality Index", "A simple scale that summarises how polluted the air is. A higher number generally means greater health concern.", "Check the category and follow the health advice shown for your situation."],
      ["PM2.5", "Fine particles", "Tiny particles with a diameter of 2.5 micrometres or less. They can travel deep into the lungs and some may enter the bloodstream.", "Reduce strenuous outdoor activity when levels are high. Keep windows closed during severe episodes if outdoor air is worse."],
      ["PM10", "Coarse particles", "Particles with a diameter of 10 micrometres or less. Dust, road activity and construction can contribute.", "Avoid dusty areas and use a well-fitting particulate respirator when exposure cannot be avoided."],
      ["NO₂", "Nitrogen dioxide", "A gas mainly produced by fuel burning, including traffic and some industrial processes. It can irritate airways.", "Avoid busy roads during high readings and ensure indoor combustion appliances are ventilated."],
      ["SO₂", "Sulphur dioxide", "A gas released mainly by burning sulphur-containing fuels and some industrial processes. It can affect breathing.", "People with asthma should be especially careful during elevated episodes."],
      ["O₃", "Ground-level ozone", "A pollutant formed when other pollutants react in sunlight. It is different from the protective ozone layer high in the atmosphere.", "Outdoor levels can rise on sunny afternoons. Consider shifting exercise to a cleaner time."],
      ["CO", "Carbon monoxide", "A colourless, odourless gas from incomplete fuel burning. High exposure can be life-threatening.", "Never run generators or fuel-burning equipment indoors. Use a certified CO alarm where appropriate."],
      ["NH₃", "Ammonia", "A gas associated with agriculture, waste and some industrial sources. High concentrations can irritate the eyes and airways.", "Avoid suspected release areas and follow local emergency instructions."],
      ["Dominant pollutant", "Main contributor to AQI", "The pollutant with the highest calculated sub-index. It is the pollutant driving the overall AQI at that time.", "Read its individual concentration and health guidance, not only the overall AQI."],
      ["Forecast", "Modelled estimate", "A computer model estimates future pollutant concentrations. It is not a direct measurement or an official CPCB forecast.", "Use forecasts for planning, and confirm current conditions with live monitoring data."]
    ]
  },
  hi: {
    title: "आप जिस हवा में साँस लेते हैं, उसे समझें",
    subtitle: "वायु गुणवत्ता के शब्दों और स्वास्थ्य पर उनके प्रभाव की सरल जानकारी।",
    search: "शब्द खोजें, जैसे PM2.5",
    terms: [
      ["AQI", "वायु गुणवत्ता सूचकांक", "यह बताता है कि हवा कितनी प्रदूषित है। संख्या जितनी अधिक होगी, स्वास्थ्य की चिंता उतनी अधिक हो सकती है।", "AQI श्रेणी देखें और अपनी स्थिति के अनुसार स्वास्थ्य सलाह अपनाएँ।"],
      ["PM2.5", "सूक्ष्म कण", "2.5 माइक्रोमीटर या उससे छोटे कण। ये फेफड़ों के अंदर तक जा सकते हैं और कुछ रक्त में भी पहुँच सकते हैं।", "स्तर अधिक होने पर बाहर कठिन व्यायाम कम करें।"],
      ["PM10", "धूल और बड़े कण", "10 माइक्रोमीटर या उससे छोटे कण। सड़क की धूल और निर्माण कार्य इनके स्रोत हो सकते हैं।", "धूल वाले क्षेत्रों से बचें।"],
      ["NO₂", "नाइट्रोजन डाइऑक्साइड", "ईंधन जलने, यातायात और उद्योगों से निकलने वाली गैस, जो साँस की नली को प्रभावित कर सकती है।", "अधिक स्तर पर व्यस्त सड़कों से दूरी रखें।"],
      ["SO₂", "सल्फर डाइऑक्साइड", "सल्फर वाले ईंधन जलने और कुछ उद्योगों से निकलने वाली गैस।", "अस्थमा वाले लोग अधिक सावधानी रखें।"],
      ["O₃", "जमीनी ओज़ोन", "धूप में अन्य प्रदूषकों की प्रतिक्रिया से बनने वाला प्रदूषक।", "दोपहर में स्तर बढ़ सकता है; बाहर जाने का समय बदलें।"],
      ["CO", "कार्बन मोनोऑक्साइड", "ईंधन अधूरा जलने से बनने वाली बिना रंग और गंध की गैस। अधिक मात्रा जानलेवा हो सकती है।", "जनरेटर या ईंधन वाले उपकरण घर के अंदर न चलाएँ।"],
      ["NH₃", "अमोनिया", "कृषि, कचरे और कुछ उद्योगों से जुड़ी गैस।", "रिसाव वाले क्षेत्र से दूर रहें और स्थानीय निर्देश मानें।"],
      ["मुख्य प्रदूषक", "AQI का सबसे बड़ा कारण", "जिस प्रदूषक का उप-सूचकांक सबसे अधिक हो, वही कुल AQI को सबसे अधिक प्रभावित करता है।", "उस प्रदूषक की अलग मात्रा और स्वास्थ्य सलाह भी देखें।"],
      ["पूर्वानुमान", "मॉडल का अनुमान", "कंप्यूटर मॉडल भविष्य की प्रदूषण मात्रा का अनुमान लगाता है। यह प्रत्यक्ष माप या आधिकारिक CPCB पूर्वानुमान नहीं है।", "योजना बनाने के लिए उपयोग करें और वर्तमान स्थिति लाइव डेटा से जाँचें।"]
    ]
  },
  bn: {
    title: "আপনি যে বাতাসে শ্বাস নেন, তা বুঝুন",
    subtitle: "বায়ুর গুণমানের শব্দ ও স্বাস্থ্যের ওপর প্রভাব সহজ ভাষায়।",
    search: "শব্দ খুঁজুন, যেমন PM2.5",
    terms: [
      ["AQI", "বায়ুর গুণমান সূচক", "বাতাস কতটা দূষিত তা সহজ সংখ্যায় বোঝায়। সংখ্যা বেশি হলে স্বাস্থ্যঝুঁকিও বাড়তে পারে।", "AQI-এর বিভাগ দেখে স্বাস্থ্য পরামর্শ মেনে চলুন।"],
      ["PM2.5", "অতি সূক্ষ্ম কণা", "২.৫ মাইক্রোমিটার বা তার চেয়ে ছোট কণা। ফুসফুসের গভীরে পৌঁছাতে পারে।", "মাত্রা বেশি হলে বাইরে কঠিন ব্যায়াম কমান।"],
      ["PM10", "ধুলো ও বড় কণা", "১০ মাইক্রোমিটার বা তার চেয়ে ছোট কণা। রাস্তার ধুলো ও নির্মাণকাজ উৎস হতে পারে।", "ধুলোময় এলাকা এড়িয়ে চলুন।"],
      ["NO₂", "নাইট্রোজেন ডাই-অক্সাইড", "জ্বালানি পোড়ানো, যানবাহন ও শিল্প থেকে নির্গত গ্যাস।", "মাত্রা বেশি হলে ব্যস্ত রাস্তা এড়ান।"],
      ["SO₂", "সালফার ডাই-অক্সাইড", "সালফারযুক্ত জ্বালানি ও কিছু শিল্প থেকে নির্গত গ্যাস।", "হাঁপানি থাকলে বিশেষ সতর্ক থাকুন।"],
      ["O₃", "ভূ-পৃষ্ঠের ওজোন", "সূর্যালোকে অন্য দূষকের বিক্রিয়ায় তৈরি হয়।", "রোদেলা দুপুরে বাইরে থাকার সময় কমান।"],
      ["CO", "কার্বন মনোক্সাইড", "জ্বালানি অসম্পূর্ণ পোড়ালে তৈরি গন্ধহীন ও বর্ণহীন গ্যাস। বেশি হলে প্রাণঘাতী।", "ঘরের ভিতরে জেনারেটর চালাবেন না।"],
      ["NH₃", "অ্যামোনিয়া", "কৃষি, বর্জ্য ও কিছু শিল্পের সঙ্গে যুক্ত গ্যাস।", "সম্ভাব্য নির্গমনের এলাকা এড়িয়ে চলুন।"],
      ["প্রধান দূষক", "AQI-তে সবচেয়ে বড় অবদান", "যে দূষকের উপ-সূচক সবচেয়ে বেশি, সেটিই সামগ্রিক AQI নির্ধারণে প্রধান।", "তার আলাদা মাত্রা ও স্বাস্থ্য পরামর্শ দেখুন।"],
      ["পূর্বাভাস", "মডেলের অনুমান", "কম্পিউটার মডেল ভবিষ্যতের দূষণ অনুমান করে। এটি সরাসরি মাপ বা সরকারি CPCB পূর্বাভাস নয়।", "পরিকল্পনার জন্য ব্যবহার করুন, বর্তমান অবস্থা লাইভ ডেটায় দেখুন।"]
    ]
  },
  mr: {
    title: "तुम्ही श्वास घेत असलेली हवा समजून घ्या",
    subtitle: "हवेच्या गुणवत्तेतील संज्ञा आणि आरोग्यावरील परिणाम सोप्या भाषेत.",
    search: "संज्ञा शोधा, उदा. PM2.5",
    terms: [
      ["AQI", "हवा गुणवत्ता निर्देशांक", "हवा किती प्रदूषित आहे हे सोप्या संख्येत दाखवतो. संख्या जास्त असल्यास आरोग्याची चिंता वाढू शकते.", "AQI श्रेणी पाहून आरोग्यविषयक सूचना पाळा."],
      ["PM2.5", "अतिसूक्ष्म कण", "२.५ मायक्रोमीटर किंवा त्याहून लहान कण. ते फुफ्फुसांच्या खोल भागात जाऊ शकतात.", "पातळी जास्त असताना बाहेरचा कठीण व्यायाम कमी करा."],
      ["PM10", "धूळ आणि मोठे कण", "१० मायक्रोमीटर किंवा त्याहून लहान कण. रस्त्याची धूळ आणि बांधकाम हे स्रोत असू शकतात.", "धुळीच्या ठिकाणांपासून दूर राहा."],
      ["NO₂", "नायट्रोजन डायऑक्साइड", "इंधन जळणे, वाहतूक आणि उद्योगांमधून निघणारा वायू.", "पातळी जास्त असल्यास गर्दीचे रस्ते टाळा."],
      ["SO₂", "सल्फर डायऑक्साइड", "सल्फरयुक्त इंधन आणि काही उद्योगांमधून निघणारा वायू.", "दमा असल्यास विशेष काळजी घ्या."],
      ["O₃", "जमिनीवरील ओझोन", "सूर्यप्रकाशात इतर प्रदूषकांच्या अभिक्रियेतून तयार होतो.", "उन्हाळी दुपारी बाहेरचा वेळ कमी करा."],
      ["CO", "कार्बन मोनॉक्साइड", "इंधन अपूर्ण जळल्याने तयार होणारा रंगहीन, गंधहीन वायू. जास्त प्रमाण धोकादायक असते.", "जनरेटर घरात चालवू नका."],
      ["NH₃", "अमोनिया", "शेती, कचरा आणि काही उद्योगांशी संबंधित वायू.", "गळतीच्या ठिकाणांपासून दूर राहा."],
      ["प्रमुख प्रदूषक", "AQI मधील सर्वाधिक योगदान", "ज्या प्रदूषकाचा उपनिर्देशांक सर्वाधिक असतो तो एकूण AQI वर सर्वाधिक प्रभाव टाकतो.", "त्याची स्वतंत्र पातळी आणि आरोग्य सूचना पाहा."],
      ["अंदाज", "मॉडेलचा अंदाज", "संगणकीय मॉडेल भविष्यातील प्रदूषणाचा अंदाज देते. हे प्रत्यक्ष मोजमाप किंवा अधिकृत CPCB अंदाज नाही.", "नियोजनासाठी वापरा आणि सध्याची स्थिती थेट डेटातून तपासा."]
    ]
  },
  te: {
    title: "మీరు పీల్చే గాలిని అర్థం చేసుకోండి",
    subtitle: "గాలి నాణ్యత పదాలు మరియు ఆరోగ్యంపై వాటి ప్రభావం సులభంగా.",
    search: "పదాన్ని వెతకండి, ఉదా. PM2.5",
    terms: [
      ["AQI", "గాలి నాణ్యత సూచిక", "గాలి ఎంత కలుషితమైందో సులభమైన సంఖ్యలో చూపిస్తుంది. సంఖ్య ఎక్కువైతే ఆరోగ్య ఆందోళన పెరగవచ్చు.", "AQI వర్గాన్ని చూసి ఆరోగ్య సూచనలను అనుసరించండి."],
      ["PM2.5", "సూక్ష్మ కణాలు", "2.5 మైక్రోమీటర్లు లేదా అంతకంటే చిన్న కణాలు. ఇవి ఊపిరితిత్తుల లోతుకు చేరవచ్చు.", "స్థాయి ఎక్కువగా ఉన్నప్పుడు బయట తీవ్రమైన వ్యాయామం తగ్గించండి."],
      ["PM10", "ధూళి కణాలు", "10 మైక్రోమీటర్లు లేదా అంతకంటే చిన్న కణాలు. రోడ్డు ధూళి, నిర్మాణ పనులు మూలాలు కావచ్చు.", "ధూళి ప్రాంతాలను నివారించండి."],
      ["NO₂", "నైట్రోజన్ డయాక్సైడ్", "ఇంధన దహనం, వాహనాలు, పరిశ్రమల నుంచి వచ్చే వాయువు.", "స్థాయి ఎక్కువగా ఉన్నప్పుడు రద్దీ రహదారులను నివారించండి."],
      ["SO₂", "సల్ఫర్ డయాక్సైడ్", "సల్ఫర్ కలిగిన ఇంధనాలు, కొన్ని పరిశ్రమల నుంచి విడుదలవుతుంది.", "ఆస్తమా ఉన్నవారు జాగ్రత్తగా ఉండాలి."],
      ["O₃", "భూమి సమీప ఓజోన్", "సూర్యకాంతిలో ఇతర కాలుష్యకారకాల చర్యలతో ఏర్పడుతుంది.", "ఎండ ఎక్కువగా ఉన్న మధ్యాహ్నం బయట సమయాన్ని తగ్గించండి."],
      ["CO", "కార్బన్ మోనాక్సైడ్", "ఇంధనం పూర్తిగా మండకపోవడం వల్ల ఏర్పడే రంగులేని, వాసనలేని వాయువు.", "జనరేటర్లను ఇంటి లోపల నడపవద్దు."],
      ["NH₃", "అమోనియా", "వ్యవసాయం, వ్యర్థాలు, కొన్ని పరిశ్రమలతో సంబంధం ఉన్న వాయువు.", "లీకేజీ ప్రాంతాలకు దూరంగా ఉండండి."],
      ["ప్రధాన కాలుష్యకారకం", "AQIపై ఎక్కువ ప్రభావం", "అత్యధిక ఉప-సూచిక కలిగిన కాలుష్యకారకం మొత్తం AQIపై ఎక్కువ ప్రభావం చూపుతుంది.", "దాని ప్రత్యేక స్థాయి, ఆరోగ్య సూచనలను చూడండి."],
      ["అంచనా", "మోడల్ అంచనా", "కంప్యూటర్ మోడల్ భవిష్యత్తు కాలుష్యాన్ని అంచనా వేస్తుంది. ఇది ప్రత్యక్ష కొలత లేదా అధికారిక CPCB అంచనా కాదు.", "ప్రణాళికకు ఉపయోగించండి; ప్రస్తుత స్థితిని ప్రత్యక్ష డేటాతో తనిఖీ చేయండి."]
    ]
  },
  ta: {
    title: "நீங்கள் சுவாசிக்கும் காற்றைப் புரிந்துகொள்ளுங்கள்",
    subtitle: "காற்றுத் தரச் சொற்களும் உடல்நல பாதிப்புகளும் எளிய மொழியில்.",
    search: "சொல்லைத் தேடுங்கள், உதா. PM2.5",
    terms: [
      ["AQI", "காற்றுத் தரக் குறியீடு", "காற்று எவ்வளவு மாசடைந்துள்ளது என்பதை எளிய எண்ணாகக் காட்டுகிறது. எண் அதிகமானால் உடல்நலக் கவலை அதிகரிக்கலாம்.", "வகையைப் பார்த்து உடல்நல ஆலோசனையைப் பின்பற்றுங்கள்."],
      ["PM2.5", "மிக நுண்ணிய துகள்கள்", "2.5 மைக்ரோமீட்டர் அல்லது அதற்குக் குறைவான துகள்கள். இவை நுரையீரலின் ஆழம் வரை செல்லலாம்.", "அளவு அதிகமாக இருக்கும்போது கடுமையான வெளிப்புற உடற்பயிற்சியைக் குறைக்கவும்."],
      ["PM10", "தூசித் துகள்கள்", "10 மைக்ரோமீட்டர் அல்லது அதற்குக் குறைவான துகள்கள். சாலைத் தூசி, கட்டுமானம் காரணமாக இருக்கலாம்.", "தூசி நிறைந்த பகுதிகளைத் தவிர்க்கவும்."],
      ["NO₂", "நைட்ரஜன் டைஆக்சைடு", "எரிபொருள் எரிதல், போக்குவரத்து, தொழிற்சாலைகளிலிருந்து வெளிவரும் வாயு.", "அளவு அதிகமாக இருக்கும்போது நெரிசலான சாலைகளைத் தவிர்க்கவும்."],
      ["SO₂", "சல்பர் டைஆக்சைடு", "சல்பர் கொண்ட எரிபொருட்கள் மற்றும் சில தொழில்களிலிருந்து வெளிவரும் வாயு.", "ஆஸ்துமா உள்ளவர்கள் கூடுதல் கவனம் செலுத்த வேண்டும்."],
      ["O₃", "தரைத்தள ஓசோன்", "சூரிய ஒளியில் மற்ற மாசுபடுத்திகள் வினைபுரிவதால் உருவாகிறது.", "வெயிலான பிற்பகலில் வெளியில் செலவிடும் நேரத்தைக் குறைக்கவும்."],
      ["CO", "கார்பன் மோனாக்சைடு", "எரிபொருள் முழுமையாக எரியாதபோது உருவாகும் நிறமற்ற, மணமற்ற வாயு.", "ஜெனரேட்டர்களை வீட்டுக்குள் இயக்க வேண்டாம்."],
      ["NH₃", "அமோனியா", "விவசாயம், கழிவுகள் மற்றும் சில தொழில்களுடன் தொடர்புடைய வாயு.", "கசிவு இருக்கக்கூடிய பகுதிகளைத் தவிர்க்கவும்."],
      ["முக்கிய மாசுபடுத்தி", "AQI-க்கு அதிக பங்களிப்பு", "அதிக துணைக் குறியீடு கொண்ட மாசுபடுத்தியே மொத்த AQI-யை அதிகம் தீர்மானிக்கிறது.", "அதன் தனிப்பட்ட அளவையும் உடல்நல ஆலோசனையையும் பாருங்கள்."],
      ["முன்னறிவிப்பு", "மாதிரி கணிப்பு", "கணினி மாதிரி எதிர்கால மாசு அளவைக் கணிக்கிறது. இது நேரடி அளவீடோ அதிகாரப்பூர்வ CPCB கணிப்போ அல்ல.", "திட்டமிடப் பயன்படுத்தி, தற்போதைய நிலையை நேரடி தரவில் சரிபார்க்கவும்."]
    ]
  }
};

const LANGS = [
  ["en", "English"], ["hi", "हिन्दी"], ["bn", "বাংলা"],
  ["mr", "मराठी"], ["te", "తెలుగు"], ["ta", "தமிழ்"]
];

export default function AirQualityGuide() {
  const [language, setLanguage] = useState(() => localStorage.getItem("airwise-language") || "en");
  const [query, setQuery] = useState("");
  const content = CONTENT[language] || CONTENT.en;
  const filtered = content.terms.filter(row => row.join(" ").toLowerCase().includes(query.toLowerCase()));

  function changeLanguage(value) {
    setLanguage(value);
    localStorage.setItem("airwise-language", value);
  }

  return (
    <section className="air-guide">
      <header className="air-guide-header">
        <div className="air-guide-icon"><BookOpen size={24} /></div>
        <div>
          <span className="air-guide-kicker">AIRWISE LEARNING CENTRE</span>
          <h1>{content.title}</h1>
          <p>{content.subtitle}</p>
        </div>
      </header>
      <div className="air-guide-tools">
        <label className="air-guide-language">
          Language
          <select value={language} onChange={e => changeLanguage(e.target.value)}>
            {LANGS.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
          </select>
        </label>
        <label className="air-guide-search">
          <Search size={17} />
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder={content.search} />
        </label>
      </div>
      <div className="air-guide-grid">
        {filtered.map(([term, name, meaning, advice]) => (
          <article className="air-guide-card" key={term}>
            <div className="air-guide-term"><strong>{term}</strong><span>{name}</span></div>
            <p>{meaning}</p>
            <div className="air-guide-advice"><ShieldAlert size={17} /><span>{advice}</span></div>
          </article>
        ))}
      </div>
      {filtered.length === 0 && <p className="air-guide-empty">No matching terms found.</p>}
      <p className="air-guide-footnote">Educational information only. AIRWISE readings and model outputs may differ from official CPCB reporting. Follow official local health and emergency guidance.</p>
    </section>
  );
}
