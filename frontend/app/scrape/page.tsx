"use client";

import { useState, useEffect, useRef } from "react";
import {
  Stethoscope, Scale, Home, Sparkles, GraduationCap, Wrench, Baby, Utensils,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { scrapeApi } from "@/lib/api";

const CITIES: Record<string, string[]> = {
  "İstanbul": ["Adalar","Arnavutköy","Ataşehir","Avcılar","Bağcılar","Bahçelievler","Bakırköy","Başakşehir","Bayrampaşa","Beşiktaş","Beykoz","Beylikdüzü","Beyoğlu","Büyükçekmece","Çatalca","Çekmeköy","Esenler","Esenyurt","Eyüpsultan","Fatih","Gaziosmanpaşa","Güngören","Kadıköy","Kağıthane","Kartal","Küçükçekmece","Maltepe","Pendik","Sancaktepe","Sarıyer","Şile","Şişli","Silivri","Sultanbeyli","Sultangazi","Tuzla","Ümraniye","Üsküdar","Zeytinburnu"],
  "Ankara": ["Altındağ","Çankaya","Etimesgut","Gölbaşı","Keçiören","Mamak","Pursaklar","Sincan","Yenimahalle"],
  "İzmir": ["Aliağa","Balçova","Bayındır","Bayraklı","Bergama","Bornova","Buca","Çeşme","Çiğli","Dikili","Foça","Gaziemir","Güzelbahçe","Karabağlar","Karşıyaka","Kemalpaşa","Konak","Menderes","Menemen","Narlıdere","Ödemiş","Seferihisar","Selçuk","Tire","Torbalı","Urla"],
  "Bursa": ["Gemlik","Gürsu","İnegöl","İznik","Karacabey","Kestel","Mudanya","Mustafakemalpaşa","Nilüfer","Osmangazi","Yıldırım"],
  "Antalya": ["Aksu","Alanya","Döşemealtı","Finike","Gazipaşa","Kaş","Kemer","Kepez","Konyaaltı","Korkuteli","Kumluca","Manavgat","Muratpaşa","Serik"],
  "Adana": ["Ceyhan","Çukurova","Karaisalı","Karataş","Kozan","Sarıçam","Seyhan","Yüreğir"],
  "Konya": ["Akşehir","Beyşehir","Çumra","Ereğli","Karatay","Meram","Sarayönü","Selçuklu","Seydişehir"],
  "Gaziantep": ["Araban","İslahiye","Nizip","Oğuzeli","Şahinbey","Şehitkamil"],
  "Mersin": ["Akdeniz","Anamur","Erdemli","Mezitli","Silifke","Tarsus","Toroslar","Yenişehir"],
  "Kayseri": ["Bünyan","Develi","Hacılar","İncesu","Kocasinan","Melikgazi","Talas","Tomarza"],
  "Eskişehir": ["Odunpazarı","Tepebaşı"],
  "Diyarbakır": ["Bağlar","Bismil","Çınar","Ergani","Kayapınar","Silvan","Sur","Yenişehir"],
  "Samsun": ["Atakum","Bafra","Canik","Çarşamba","İlkadım","Tekkeköy","Terme"],
  "Trabzon": ["Akçaabat","Araklı","Maçka","Of","Ortahisar","Sürmene","Yomra"],
  "Kocaeli": ["Başiskele","Çayırova","Darıca","Derince","Gebze","Gölcük","İzmit","Kartepe","Körfez"],
  "Sakarya": ["Adapazarı","Akyazı","Arifiye","Erenler","Hendek","Karasu","Sapanca","Serdivan"],
  "Tekirdağ": ["Çerkezköy","Çorlu","Ergene","Kapaklı","Malkara","Muratlı","Süleymanpaşa"],
  "Balıkesir": ["Altıeylül","Ayvalık","Bandırma","Burhaniye","Edremit","Erdek","Gönen","Karesi","Susurluk"],
  "Muğla": ["Bodrum","Dalaman","Datça","Fethiye","Köyceğiz","Marmaris","Menteşe","Milas","Ortaca","Seydikemer","Ula","Yatağan"],
  "Hatay": ["Altınözü","Antakya","Arsuz","Belen","Defne","Dörtyol","Erzin","Hassa","İskenderun","Kırıkhan","Kumlu","Payas","Reyhanlı","Samandağ","Yayladağı"],
};

const LIMIT_PRESETS = [5, 10, 15, 20, 25];

const SECTORS = [
  { key: "klinik",        label: "Klinik",         sub: "Muayenehane, Poliklinik",   Icon: Stethoscope,  color: "#38bdf8" },
  { key: "avukat",        label: "Avukat",          sub: "Hukuk Bürosu, Danışmanlık", Icon: Scale,         color: "#a774ff" },
  { key: "emlak",         label: "Emlak",           sub: "Gayrimenkul, Danışman",     Icon: Home,          color: "#34d399" },
  { key: "guzellik",      label: "Güzellik",        sub: "Kuaför, Lazer, Estetik",    Icon: Sparkles,      color: "#f472b6" },
  { key: "egitim",        label: "Eğitim",          sub: "Kurs, Dil Okulu, Koçluk",   Icon: GraduationCap, color: "#ffb648" },
  { key: "ev_hizmetleri", label: "Ev Hizmetleri",   sub: "Tesisat, Elektrik, Tadilat",Icon: Wrench,        color: "#fb923c" },
  { key: "kadin_dogum",   label: "Kadın Doğum",     sub: "Jinekoloji, Gebelik",       Icon: Baby,          color: "#f43f5e" },
  { key: "restoran",      label: "Restoran",        sub: "Lokanta, Kafe, Bistro",     Icon: Utensils,      color: "#facc15" },
];

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
    (labelMap?.[o] ?? o).toLowerCase().includes(search.toLowerCase())
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
            <div className="px-3 py-2 font-mono text-[10px] text-dim">Sonuç yok</div>
          ) : filtered.map((o) => (
            <button
              key={o}
              type="button"
              className={`w-full text-left px-3 py-2 font-mono text-[11px] transition-colors ${
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
  const [sector, setSector] = useState("");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [limit, setLimit] = useState(20);
  const [customLimit, setCustomLimit] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ job_id: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    setResult(null);
    try {
      const res = await scrapeApi.run(sector, city, district, limit);
      setResult({ job_id: res.job_id });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Hata oluştu");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col flex-1">
      <Header title="Lead Topla" description="Google Maps'ten yeni lead'ler topla" />
      <div className="p-6 max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-6">

          {/* Sektör */}
          <div>
            <p className="font-mono text-[9px] text-dim tracking-[0.25em] uppercase mb-3">▸ Sektör Seç</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
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
                        ? {
                            borderColor: color,
                            backgroundColor: `${color}12`,
                            boxShadow: `0 0 12px ${color}25`,
                          }
                        : {
                            borderColor: "#1c2742",
                            backgroundColor: "#0d1324",
                          }
                    }
                  >
                    <Icon
                      className="h-5 w-5"
                      strokeWidth={1.5}
                      style={{ color: selected ? color : "#4a5876" }}
                    />
                    <span
                      className="text-xs font-mono font-semibold leading-tight tracking-wide"
                      style={{ color: selected ? color : "#e6edf7" }}
                    >
                      {label}
                    </span>
                    <span className="font-mono text-[9px] leading-tight text-dim">{sub}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Şehir */}
          <div>
            <p className="font-mono text-[9px] text-dim tracking-[0.25em] uppercase mb-2">▸ Şehir</p>
            <SearchableDropdown
              options={cities}
              value={city}
              onChange={handleCityChange}
              placeholder="Şehir seçin veya yazın..."
            />
          </div>

          {/* İlçe */}
          <div>
            <p className="font-mono text-[9px] text-dim tracking-[0.25em] uppercase mb-2">
              ▸ İlçe <span className="text-dim/50">(opsiyonel)</span>
            </p>
            <SearchableDropdown
              options={districts}
              value={district}
              onChange={setDistrict}
              placeholder={city ? "İlçe seçin..." : "Önce şehir seçin"}
              disabled={!city}
            />
          </div>

          {/* Limit */}
          <div>
            <p className="font-mono text-[9px] text-dim tracking-[0.25em] uppercase mb-3">▸ Limit</p>
            <div className="flex gap-2 flex-wrap items-center">
              {LIMIT_PRESETS.map((v) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => handleLimitPreset(v)}
                  className={`font-mono text-[10px] uppercase tracking-wider px-3 py-1.5 border transition-all ${
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
                className="w-24"
              />
            </div>
          </div>

          <Button
            type="submit"
            loading={loading}
            disabled={!sector || !city}
            className="w-full"
            size="lg"
          >
            Taramayı Başlat
          </Button>
        </form>

        {result && (
          <div className="mt-4 border border-ok/40 bg-ok/5 p-3 font-mono text-[11px] text-ok">
            İş kuyruğa alındı. Job ID:{" "}
            <span className="font-bold">{result.job_id.slice(0, 8)}</span>
          </div>
        )}
        {error && (
          <div className="mt-4 border border-hot/40 bg-hot/5 p-3 font-mono text-[11px] text-hot">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
