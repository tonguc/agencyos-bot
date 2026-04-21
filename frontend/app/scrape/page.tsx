"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Stethoscope, Scale, Home, Sparkles, GraduationCap, Wrench, Baby, Utensils,
  Car, Wind, Key, Hammer, Truck, Droplets,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { scrapeApi, jobsApi } from "@/lib/api";
import type { Job } from "@/types";

const CITIES: Record<string, string[]> = {
  "Adana":           ["Ceyhan","Çukurova","Karaisalı","Karataş","Kozan","Sarıçam","Seyhan","Yüreğir"],
  "Adıyaman":        ["Besni","Gerger","Kahta","Merkez","Samsat"],
  "Afyonkarahisar":  ["Afyonkarahisar Merkez","Bolvadin","Dinar","Emirdağ","Sandıklı","Sincanlı"],
  "Ağrı":            ["Diyadin","Doğubayazıt","Eleşkirt","Merkez","Patnos"],
  "Aksaray":         ["Ağaçören","Eskil","Gülağaç","Merkez","Ortaköy"],
  "Amasya":          ["Göynücek","Gümüşhacıköy","Merkez","Merzifon","Suluova","Taşova"],
  "Ankara":          ["Altındağ","Çankaya","Etimesgut","Gölbaşı","Keçiören","Kızılcahamam","Mamak","Polatlı","Pursaklar","Sincan","Yenimahalle"],
  "Antalya":         ["Aksu","Alanya","Döşemealtı","Finike","Gazipaşa","Kaş","Kemer","Kepez","Konyaaltı","Korkuteli","Kumluca","Manavgat","Muratpaşa","Serik"],
  "Ardahan":         ["Çıldır","Göle","Hanak","Merkez","Posof"],
  "Artvin":          ["Ardanuç","Arhavi","Borçka","Hopa","Merkez","Şavşat","Yusufeli"],
  "Aydın":           ["Bozdoğan","Buharkent","Çine","Didim","Efeler","Germencik","İncirliova","Karacasu","Köşk","Kuşadası","Kuyucak","Nazilli","Söke","Sultanhisar","Yenipazar"],
  "Balıkesir":       ["Altıeylül","Ayvalık","Bandırma","Burhaniye","Edremit","Erdek","Gönen","Karesi","Susurluk"],
  "Bartın":          ["Amasra","Kurucaşile","Merkez","Ulus"],
  "Batman":          ["Beşiri","Gercüş","Hasankeyf","Merkez","Sason"],
  "Bayburt":         ["Aydıntepe","Demirözü","Merkez"],
  "Bilecik":         ["Bozüyük","Gölpazarı","Merkez","Osmaneli","Pazaryeri","Söğüt"],
  "Bingöl":          ["Genç","Karlıova","Merkez","Solhan"],
  "Bitlis":          ["Adilcevaz","Ahlat","Güroymak","Hizan","Merkez","Tatvan"],
  "Bolu":            ["Gerede","Göynük","Merkez","Mudurnu","Seben"],
  "Burdur":          ["Bucak","Gölhisar","Merkez","Tefenni","Yeşilova"],
  "Bursa":           ["Gemlik","Gürsu","İnegöl","İznik","Karacabey","Kestel","Mudanya","Mustafakemalpaşa","Nilüfer","Osmangazi","Yıldırım"],
  "Çanakkale":       ["Ayvacık","Biga","Çan","Eceabat","Gelibolu","Gökçeada","Lapseki","Merkez","Yenice"],
  "Çankırı":         ["Çerkeş","Ilgaz","Kızılırmak","Kurşunlu","Merkez","Orta","Şabanözü"],
  "Çorum":           ["Alaca","Bayat","Boğazkale","İskilip","Kargı","Merkez","Osmancık","Sungurlu"],
  "Denizli":         ["Acıpayam","Babadağ","Baklan","Bekilli","Beyağaç","Bozkurt","Buldan","Çal","Çameli","Çardak","Çivril","Güney","Honaz","Kale","Merkezefendi","Pamukkale","Sarayköy","Serinhisar","Tavas"],
  "Diyarbakır":      ["Bağlar","Bismil","Çınar","Ergani","Kayapınar","Silvan","Sur","Yenişehir"],
  "Düzce":           ["Akçakoca","Cumayeri","Çilimli","Gölyaka","Gümüşova","Kaynaşlı","Merkez","Yığılca"],
  "Edirne":          ["Enez","Havsa","İpsala","Keşan","Lalapaşa","Merkez","Meriç","Süloğlu","Uzunköprü"],
  "Elazığ":          ["Ağın","Alacakaya","Arıcak","Baskil","Karakoçan","Keban","Kovancılar","Merkez","Palu","Sivrice"],
  "Erzincan":        ["Çayırlı","İliç","Kemah","Kemaliye","Merkez","Refahiye","Tercan","Üzümlü"],
  "Erzurum":         ["Aşkale","Aziziye","Horasan","İspir","Karayazı","Köprüköy","Merkez","Narman","Oltu","Palandöken","Pasinler","Şenkaya","Tortum","Yakutiye"],
  "Eskişehir":       ["Odunpazarı","Tepebaşı"],
  "Gaziantep":       ["Araban","İslahiye","Nizip","Oğuzeli","Şahinbey","Şehitkamil"],
  "Giresun":         ["Bulancak","Çamoluk","Dereli","Espiye","Eynesil","Görele","Güce","Keşap","Merkez","Piraziz","Şebinkarahisar","Tirebolu","Yağlıdere"],
  "Gümüşhane":       ["Kelkit","Köse","Kürtün","Merkez","Şiran","Torul"],
  "Hakkari":         ["Çukurca","Merkez","Şemdinli","Yüksekova"],
  "Hatay":           ["Altınözü","Antakya","Arsuz","Belen","Defne","Dörtyol","Erzin","Hassa","İskenderun","Kırıkhan","Kumlu","Payas","Reyhanlı","Samandağ","Yayladağı"],
  "Iğdır":           ["Aralık","Karakoyunlu","Merkez","Tuzluca"],
  "Isparta":         ["Atabey","Eğirdir","Gelendost","Gönen","Keçiborlu","Merkez","Senirkent","Sütçüler","Şarkikaraağaç","Uluborlu","Yalvaç","Yenişarbademli"],
  "İstanbul":        ["Adalar","Arnavutköy","Ataşehir","Avcılar","Bağcılar","Bahçelievler","Bakırköy","Başakşehir","Bayrampaşa","Beşiktaş","Beykoz","Beylikdüzü","Beyoğlu","Büyükçekmece","Çatalca","Çekmeköy","Esenler","Esenyurt","Eyüpsultan","Fatih","Gaziosmanpaşa","Güngören","Kadıköy","Kağıthane","Kartal","Küçükçekmece","Maltepe","Pendik","Sancaktepe","Sarıyer","Şile","Şişli","Silivri","Sultanbeyli","Sultangazi","Tuzla","Ümraniye","Üsküdar","Zeytinburnu"],
  "İzmir":           ["Aliağa","Balçova","Bayındır","Bayraklı","Bergama","Bornova","Buca","Çeşme","Çiğli","Dikili","Foça","Gaziemir","Güzelbahçe","Karabağlar","Karşıyaka","Kemalpaşa","Konak","Menderes","Menemen","Narlıdere","Ödemiş","Seferihisar","Selçuk","Tire","Torbalı","Urla"],
  "Kahramanmaraş":   ["Afşin","Andırın","Çağlayancerit","Dulkadiroğlu","Ekinözü","Elbistan","Göksun","Merkez","Nurhak","Onikişubat","Pazarcık","Türkoğlu"],
  "Karabük":         ["Eflani","Eskipazar","Merkez","Ovacık","Safranbolu","Yenice"],
  "Karaman":         ["Ayrancı","Başyayla","Ermenek","Kazımkarabekir","Merkez","Sarıveliler"],
  "Kars":            ["Akyaka","Arpaçay","Digor","Kağızman","Merkez","Sarıkamış","Selim","Susuz"],
  "Kastamonu":       ["Abana","Araç","Azdavay","Bozkurt","Çatalzeytin","Cide","Daday","Devrekani","Doğanyurt","Hanönü","İhsangazi","İnebolu","Küre","Merkez","Pınarbaşı","Seydiler","Şenpazar","Taşköprü","Tosya"],
  "Kayseri":         ["Bünyan","Develi","Hacılar","İncesu","Kocasinan","Melikgazi","Talas","Tomarza"],
  "Kilis":           ["Elbeyli","Merkez","Musabeyli","Polateli"],
  "Kırıkkale":       ["Bahşili","Balışeyh","Çelebi","Delice","Karakeçili","Keskin","Merkez","Sulakyurt","Yahşihan"],
  "Kırklareli":      ["Babaeski","Demirköy","Kofçaz","Lüleburgaz","Merkez","Pehlivanköy","Pınarhisar","Vize"],
  "Kırşehir":        ["Akçakent","Akpınar","Boztepe","Çiçekdağı","Kaman","Merkez","Mucur"],
  "Kocaeli":         ["Başiskele","Çayırova","Darıca","Derince","Gebze","Gölcük","İzmit","Kartepe","Körfez"],
  "Konya":           ["Akşehir","Beyşehir","Çumra","Ereğli","Karatay","Meram","Sarayönü","Selçuklu","Seydişehir"],
  "Kütahya":         ["Altıntaş","Aslanapa","Çavdarhisar","Domaniç","Dumlupınar","Emet","Gediz","Hisarcık","Merkez","Pazarlar","Simav","Şaphane","Tavşanlı"],
  "Malatya":         ["Akçadağ","Arapgir","Arguvan","Battalgazi","Darende","Doğanşehir","Doğanyol","Hekimhan","Kale","Kuluncak","Merkez","Pütürge","Yazıhan","Yeşilyurt"],
  "Manisa":          ["Ahmetli","Akhisar","Alaşehir","Demirci","Gölmarmara","Gördes","Kırkağaç","Köprübaşı","Kula","Merkez","Salihli","Sarıgöl","Saruhanlı","Selendi","Soma","Şehzadeler","Turgutlu","Yunusemre"],
  "Mardin":          ["Artuklu","Dargeçit","Derik","Kızıltepe","Mazıdağı","Midyat","Nusaybin","Ömerli","Savur","Yeşilli"],
  "Mersin":          ["Akdeniz","Anamur","Erdemli","Mezitli","Silifke","Tarsus","Toroslar","Yenişehir"],
  "Muğla":           ["Bodrum","Dalaman","Datça","Fethiye","Köyceğiz","Marmaris","Menteşe","Milas","Ortaca","Seydikemer","Ula","Yatağan"],
  "Muş":             ["Bulanık","Hasköy","Korkut","Malazgirt","Merkez","Varto"],
  "Nevşehir":        ["Acıgöl","Avanos","Derinkuyu","Gülşehir","Hacıbektaş","Kozaklı","Merkez","Ürgüp"],
  "Niğde":           ["Altunhisar","Bor","Çamardı","Çiftlik","Merkez","Ulukışla"],
  "Ordu":            ["Akkuş","Altınordu","Aybastı","Çamaş","Çatalpınar","Çaybaşı","Fatsa","Gölköy","Gülyalı","Gürgentepe","İkizce","Kabadüz","Kabataş","Korgan","Kumru","Mesudiye","Perşembe","Ulubey","Ünye"],
  "Osmaniye":        ["Bahçe","Düziçi","Hasanbeyli","Kadirli","Merkez","Sumbas","Toprakkale"],
  "Rize":            ["Ardeşen","Çamlıhemşin","Çayeli","Derepazarı","Fındıklı","Güneysu","Hemşin","İkizdere","İyidere","Kalkandere","Merkez","Pazar"],
  "Sakarya":         ["Adapazarı","Akyazı","Arifiye","Erenler","Hendek","Karasu","Sapanca","Serdivan"],
  "Samsun":          ["Atakum","Bafra","Canik","Çarşamba","İlkadım","Tekkeköy","Terme"],
  "Siirt":           ["Baykan","Eruh","Kurtalan","Merkez","Pervari","Şirvan","Tillo"],
  "Sinop":           ["Ayancık","Boyabat","Dikmen","Durağan","Erfelek","Gerze","Merkez","Saraydüzü","Türkeli"],
  "Sivas":           ["Divriği","Gemerek","Gürün","Hafik","İmranlı","Kangal","Koyulhisar","Merkez","Şarkışla","Suşehri","Ulaş","Yıldızeli","Zara"],
  "Şanlıurfa":       ["Akçakale","Birecik","Bozova","Ceylanpınar","Eyyübiye","Halfeti","Haliliye","Harran","Hilvan","Karaköprü","Merkez","Siverek","Suruç","Viranşehir"],
  "Şırnak":          ["Beytüşşebap","Cizre","Güçlükonak","İdil","Merkez","Silopi","Uludere"],
  "Tekirdağ":        ["Çerkezköy","Çorlu","Ergene","Kapaklı","Malkara","Muratlı","Süleymanpaşa"],
  "Tokat":           ["Almus","Artova","Başçiftlik","Erbaa","Merkez","Niksar","Pazar","Reşadiye","Sulusaray","Turhal","Yeşilyurt","Zile"],
  "Trabzon":         ["Akçaabat","Araklı","Maçka","Of","Ortahisar","Sürmene","Yomra"],
  "Tunceli":         ["Çemişgezek","Hozat","Merkez","Mazgirt","Nazimiye","Ovacık","Pertek","Pülümür"],
  "Uşak":            ["Banaz","Eşme","Karahallı","Merkez","Sivaslı","Ulubey"],
  "Van":             ["Bahçesaray","Başkale","Çaldıran","Çatak","Edremit","Erciş","Gevaş","Gürpınar","İpekyolu","Merkez","Muradiye","Özalp","Saray","Tuşba"],
  "Yalova":          ["Altınova","Armutlu","Çınarcık","Çiftlikköy","Merkez","Termal"],
  "Yozgat":          ["Akdağmadeni","Aydıncık","Boğazlıyan","Çandır","Çayıralan","Çekerek","Kadışehri","Merkez","Saraykent","Sarıkaya","Şefaatli","Sorgun","Yenifakılı","Yerköy"],
  "Zonguldak":       ["Alaplı","Çaycuma","Devrek","Ereğli","Gökçebey","Kilimli","Kozlu","Merkez"],
};

const LIMIT_PRESETS = [5, 10, 15, 20, 25];

const SECTORS = [
  { key: "klinik",          label: "Klinik",           sub: "Muayenehane, Poliklinik",    Icon: Stethoscope,  color: "#38bdf8" },
  { key: "avukat",          label: "Avukat",            sub: "Hukuk Bürosu, Danışmanlık",  Icon: Scale,        color: "#a774ff" },
  { key: "emlak",           label: "Emlak",             sub: "Gayrimenkul, Danışman",      Icon: Home,         color: "#34d399" },
  { key: "guzellik",        label: "Güzellik",          sub: "Kuaför, Lazer, Estetik",     Icon: Sparkles,     color: "#f472b6" },
  { key: "egitim",          label: "Eğitim",            sub: "Kurs, Dil Okulu, Koçluk",    Icon: GraduationCap,color: "#ffb648" },
  { key: "ev_hizmetleri",   label: "Tesisat",           sub: "Tesisat, Elektrik, Kombi",   Icon: Wrench,       color: "#fb923c" },
  { key: "kadin_dogum",     label: "Kadın Doğum",       sub: "Jinekoloji, Gebelik",        Icon: Baby,         color: "#f43f5e" },
  { key: "restoran",        label: "Restoran",          sub: "Lokanta, Kafe, Bistro",      Icon: Utensils,     color: "#facc15" },
  { key: "oto_servis",      label: "Oto Servis",        sub: "Tamir, Lastik, Kaporta",     Icon: Car,          color: "#94a3b8" },
  { key: "klima_beyaz_esya",label: "Klima / Beyaz Eşya",sub: "Klima, Kombi, Beyaz Eşya",  Icon: Wind,         color: "#7dd3fc" },
  { key: "cilingir",        label: "Çilingir",          sub: "Kilitçi, Acil Giriş",        Icon: Key,          color: "#fbbf24" },
  { key: "tadilat",         label: "Tadilat",           sub: "Boya, Badana, Dekorasyon",   Icon: Hammer,       color: "#c084fc" },
  { key: "nakliyat",        label: "Nakliyat",          sub: "Evden Eve, Taşımacılık",     Icon: Truck,        color: "#4ade80" },
  { key: "hali_temizlik",   label: "Halı & Temizlik",   sub: "Halı Yıkama, Ev Temizliği", Icon: Droplets,     color: "#60a5fa" },
];

function trNorm(s: string) {
  return s
    .replace(/İ/g, "i").replace(/I/g, "i")
    .replace(/Ğ/g, "g").replace(/ğ/g, "g")
    .replace(/Ü/g, "u").replace(/ü/g, "u")
    .replace(/Ş/g, "s").replace(/ş/g, "s")
    .replace(/Ö/g, "o").replace(/ö/g, "o")
    .replace(/Ç/g, "c").replace(/ç/g, "c")
    .replace(/ı/g, "i")
    .toLowerCase();
}

function SearchableDropdown({
  options, value, onChange, placeholder, labelMap, disabled,
}: {
  options: string[];
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  labelMap?: Record<string, string>;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filtered = options.filter((o) =>
    trNorm(labelMap?.[o] ?? o).includes(trNorm(search))
  );
  const displayValue = value ? (labelMap?.[value] ?? value) : "";

  return (
    <div ref={ref} className="relative">
      <Input
        value={open ? search : displayValue}
        onChange={(e) => { setSearch(e.target.value); setOpen(true); }}
        onFocus={() => { setOpen(true); setSearch(""); }}
        placeholder={placeholder}
        disabled={disabled}
        className="cursor-pointer"
      />
      {open && !disabled && (
        <div className="absolute z-50 mt-1 w-full border border-stroke bg-panel shadow-xl max-h-56 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="px-3 py-2 font-mono text-[12px] text-dim">Sonuç yok</div>
          ) : filtered.map((o) => (
            <button
              key={o}
              type="button"
              className={`w-full text-left px-3 py-2 font-mono text-[13px] transition-colors ${
                value === o
                  ? "bg-accent/10 text-accent"
                  : "text-muted hover:bg-panel-high hover:text-bright"
              }`}
              onClick={() => { onChange(o); setOpen(false); setSearch(""); }}
            >
              {labelMap?.[o] ?? o}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ScrapePage() {
  const router = useRouter();
  const [sector, setSector] = useState("");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [limit, setLimit] = useState(15);
  const [customLimit, setCustomLimit] = useState("");
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  useEffect(() => {
    if (!jobId) return;
    pollRef.current = setInterval(async () => {
      try {
        const job = await jobsApi.get(jobId);
        setJobStatus(job);
        if (job.status === "completed" || job.status === "failed") {
          stopPolling();
          if (job.status === "completed") {
            setTimeout(() => router.push("/jobs"), 2500);
          }
        }
      } catch { stopPolling(); }
    }, 3000);
    return stopPolling;
  }, [jobId, stopPolling, router]);

  const cities = Object.keys(CITIES).sort((a, b) => a.localeCompare(b, "tr"));
  const districts = city ? (CITIES[city] ?? []) : [];

  function handleCityChange(c: string) {
    setCity(c);
    setDistrict("");
  }

  function handleLimitPreset(v: number) {
    setLimit(v);
    setCustomLimit("");
  }

  function handleCustomLimit(v: string) {
    setCustomLimit(v);
    const n = parseInt(v);
    if (!isNaN(n) && n > 0) setLimit(n);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!sector || !city) return;
    setLoading(true);
    setError(null);
    setJobId(null);
    setJobStatus(null);
    stopPolling();
    try {
      const res = await scrapeApi.run(sector, city, district, limit);
      setJobId(res.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Hata oluştu");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col flex-1">
      <Header title="Lead Topla" description="Google Maps'ten yeni lead'ler topla" />
      <div className="p-4 md:p-6">
        <form onSubmit={handleSubmit} className="space-y-6">

          {/* Sektör kartları — tam genişlik */}
          <div>
            <p className="font-mono text-[11px] text-dim tracking-[0.25em] uppercase mb-3">▸ Sektör Seç</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7">
              {SECTORS.map(({ key, label, sub, Icon, color }) => {
                const selected = sector === key;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSector(key)}
                    className="flex flex-col items-center gap-1.5 border p-3 text-center transition-all"
                    style={
                      selected
                        ? { borderColor: color, backgroundColor: `${color}12`, boxShadow: `0 0 12px ${color}25` }
                        : { borderColor: "#1c2742", backgroundColor: "#0d1324" }
                    }
                  >
                    <Icon className="h-5 w-5" strokeWidth={1.5} style={{ color: selected ? color : "#4a5876" }} />
                    <span className="text-xs font-mono font-semibold leading-tight tracking-wide" style={{ color: selected ? color : "#e6edf7" }}>
                      {label}
                    </span>
                    <span className="font-mono text-[11px] leading-tight text-dim">{sub}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Form kontrolleri — yatay sıra */}
          <div className="flex flex-wrap items-end gap-4 border-t border-stroke pt-5">
            <div className="w-52">
              <p className="font-mono text-[11px] text-dim tracking-[0.25em] uppercase mb-2">▸ Şehir</p>
              <SearchableDropdown
                options={cities}
                value={city}
                onChange={handleCityChange}
                placeholder="Şehir seçin..."
              />
            </div>

            <div className="w-44">
              <p className="font-mono text-[11px] text-dim tracking-[0.25em] uppercase mb-2">
                ▸ İlçe <span className="text-dim/50">(ops.)</span>
              </p>
              <SearchableDropdown
                options={districts}
                value={district}
                onChange={setDistrict}
                placeholder={city ? "İlçe seçin..." : "Önce şehir"}
                disabled={!city}
              />
            </div>

            <div>
              <p className="font-mono text-[11px] text-dim tracking-[0.25em] uppercase mb-2">▸ Limit</p>
              <div className="flex gap-1.5 items-center flex-wrap">
                {LIMIT_PRESETS.map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => handleLimitPreset(v)}
                    className={`font-mono text-[12px] uppercase tracking-wider px-3 py-1.5 border transition-all ${
                      limit === v && !customLimit
                        ? "bg-accent/10 border-accent text-accent"
                        : "border-stroke text-muted hover:border-stroke-2 hover:text-bright"
                    }`}
                  >
                    {v}
                  </button>
                ))}
                <Input
                  type="number"
                  min={1}
                  max={100}
                  value={customLimit}
                  onChange={(e) => handleCustomLimit(e.target.value)}
                  placeholder="Manuel"
                  className="w-20"
                />
              </div>
            </div>

            <Button
              type="submit"
              loading={loading}
              disabled={!sector || !city}
              size="lg"
              className="ml-auto"
            >
              Taramayı Başlat
            </Button>
          </div>

        </form>

        {jobId && (
          <div className={`mt-6 px-4 py-3 flex items-center justify-between gap-4 border transition-all ${
            jobStatus?.status === "completed"
              ? "border-ok/40 bg-ok/5"
              : jobStatus?.status === "failed"
              ? "border-hot/40 bg-hot/5"
              : "border-accent/30 bg-accent/5"
          }`}>
            <div>
              {!jobStatus || jobStatus.status === "pending" || jobStatus.status === "running" ? (
                <>
                  <p className="font-mono text-[13px] text-accent font-semibold flex items-center gap-2">
                    <span className="inline-block w-2 h-2 rounded-full bg-accent animate-pulse" />
                    Tarama devam ediyor…
                  </p>
                  <p className="font-mono text-[12px] text-accent/60 mt-0.5">
                    {jobStatus?.progress_message || "Lead'ler toplanıyor, bu 1-2 dakika sürebilir."}
                  </p>
                </>
              ) : jobStatus.status === "completed" ? (
                <>
                  <p className="font-mono text-[13px] text-ok font-semibold">
                    Tarama tamamlandı — {(jobStatus.result as { saved?: number })?.saved ?? 0} lead kaydedildi
                  </p>
                  <p className="font-mono text-[12px] text-ok/60 mt-0.5">Fırsatlar sayfasına yönlendiriliyorsun…</p>
                </>
              ) : (
                <p className="font-mono text-[13px] text-hot font-semibold">
                  Tarama başarısız: {jobStatus.error_message || "Bilinmeyen hata"}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => router.push("/jobs")}
              className="font-mono text-[11px] uppercase tracking-wider px-4 py-1.5 border border-accent/40 text-accent hover:bg-accent/10 transition-all whitespace-nowrap shrink-0"
            >
              Fırsatlara Git →
            </button>
          </div>
        )}
        {error && (
          <div className="mt-4 max-w-4xl border border-hot/40 bg-hot/5 p-3 font-mono text-[13px] text-hot">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
