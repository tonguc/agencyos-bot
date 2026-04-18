"use client";

import { useState, useEffect, useRef } from "react";
import {
  Stethoscope, Scale, Home, Sparkles, GraduationCap, Wrench, Baby, Utensils,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  { key: "klinik",        label: "Klinik",          sub: "Muayenehane, Poliklinik",        Icon: Stethoscope, color: "text-blue-600",   bg: "bg-blue-50",   ring: "ring-blue-400" },
  { key: "avukat",        label: "Avukat",           sub: "Hukuk Bürosu, Danışmanlık",      Icon: Scale,        color: "text-violet-600", bg: "bg-violet-50", ring: "ring-violet-400" },
  { key: "emlak",         label: "Emlak",            sub: "Gayrimenkul, Danışman",          Icon: Home,         color: "text-emerald-600",bg: "bg-emerald-50",ring: "ring-emerald-400" },
  { key: "guzellik",      label: "Güzellik",         sub: "Kuaför, Lazer, Estetik",         Icon: Sparkles,     color: "text-pink-600",   bg: "bg-pink-50",   ring: "ring-pink-400" },
  { key: "egitim",        label: "Eğitim",           sub: "Kurs, Dil Okulu, Koçluk",        Icon: GraduationCap,color: "text-amber-600",  bg: "bg-amber-50",  ring: "ring-amber-400" },
  { key: "ev_hizmetleri", label: "Ev Hizmetleri",   sub: "Tesisat, Elektrik, Tadilat",     Icon: Wrench,       color: "text-orange-600", bg: "bg-orange-50", ring: "ring-orange-400" },
  { key: "kadin_dogum",   label: "Kadın Doğum",      sub: "Jinekoloji, Gebelik",            Icon: Baby,         color: "text-rose-600",   bg: "bg-rose-50",   ring: "ring-rose-400" },
  { key: "restoran",      label: "Restoran",          sub: "Lokanta, Kafe, Bistro",          Icon: Utensils,     color: "text-yellow-600", bg: "bg-yellow-50", ring: "ring-yellow-400" },
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
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-lg max-h-56 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="px-3 py-2 text-sm text-slate-400">Sonuç yok</div>
          ) : filtered.map((o) => (
            <button
              key={o}
              type="button"
              className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-50 ${value === o ? "bg-blue-50 text-blue-700 font-medium" : "text-slate-700"}`}
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
        <Card>
          <CardHeader><CardTitle>Yeni Tarama</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-2">Sektör</label>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
                  {SECTORS.map(({ key, label, sub, Icon, color, bg, ring }) => {
                    const selected = sector === key;
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setSector(key)}
                        className={`flex flex-col items-center gap-1.5 rounded-xl border-2 p-3 text-center transition-all ${
                          selected
                            ? `border-current ring-2 ${ring} ${color} ${bg}`
                            : "border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:bg-slate-50"
                        }`}
                      >
                        <Icon className={`h-6 w-6 ${selected ? color : "text-slate-400"}`} strokeWidth={1.5} />
                        <span className={`text-xs font-semibold leading-tight ${selected ? color : "text-slate-700"}`}>
                          {label}
                        </span>
                        <span className="text-[10px] leading-tight text-slate-400">{sub}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Şehir</label>
                <SearchableDropdown
                  options={cities}
                  value={city}
                  onChange={handleCityChange}
                  placeholder="Şehir seçin veya yazın..."
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  İlçe <span className="text-slate-400">(opsiyonel)</span>
                </label>
                <SearchableDropdown
                  options={districts}
                  value={district}
                  onChange={setDistrict}
                  placeholder={city ? "İlçe seçin..." : "Önce şehir seçin"}
                  disabled={!city}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-2">Limit</label>
                <div className="flex gap-2 flex-wrap items-center">
                  {LIMIT_PRESETS.map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => handleLimitPreset(v)}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                        limit === v && !customLimit
                          ? "bg-blue-600 text-white border-blue-600"
                          : "bg-white text-slate-600 border-slate-200 hover:border-blue-300"
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
                    className="w-24 text-sm"
                  />
                </div>
              </div>

              <Button
                type="submit"
                loading={loading}
                disabled={!sector || !city}
                className="w-full"
              >
                Taramayı Başlat
              </Button>
            </form>

            {result && (
              <div className="mt-4 rounded-lg bg-green-50 border border-green-200 p-3 text-sm text-green-700">
                İş kuyruğa alındı. Job ID: <span className="font-mono">{result.job_id.slice(0, 8)}</span>
              </div>
            )}
            {error && (
              <div className="mt-4 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                {error}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
