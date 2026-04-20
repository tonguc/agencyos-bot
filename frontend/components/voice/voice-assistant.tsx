"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Volume2, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import { voiceApi } from "@/lib/api";

type Status = "idle" | "listening" | "thinking" | "speaking";

interface ScrapeAction {
  type: "scrape";
  job_id: string;
  sector: string;
  city: string;
  district?: string;
  limit: number;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}
interface SpeechRecognitionInstance extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: Event) => void) | null;
  onend: (() => void) | null;
}
declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
  }
}

const SECTOR_LABELS: Record<string, string> = {
  klinik: "Klinik", avukat: "Avukat", emlak: "Emlak", guzellik: "Güzellik",
  egitim: "Eğitim", ev_hizmetleri: "Tesisat", kadin_dogum: "Kadın Doğum",
  restoran: "Restoran", oto_servis: "Oto Servis", klima_beyaz_esya: "Klima / Beyaz Eşya",
  cilingir: "Çilingir", tadilat: "Tadilat", nakliyat: "Nakliyat", hali_temizlik: "Halı & Temizlik",
};

function buildRecognition(): SpeechRecognitionInstance | null {
  if (typeof window === "undefined") return null;
  const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
  if (!Ctor) return null;
  const r = new Ctor();
  r.lang = "tr-TR";
  r.continuous = false;
  r.interimResults = false;
  r.maxAlternatives = 1;
  return r;
}

function speak(text: string, onEnd: () => void) {
  if (typeof window === "undefined" || !window.speechSynthesis) { onEnd(); return; }
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "tr-TR";
  u.rate = 1.0;
  u.pitch = 1.0;

  // Wait for voices to load then pick Turkish
  const trySpeak = () => {
    const voices = window.speechSynthesis.getVoices();
    const tr = voices.find((v) => v.lang === "tr-TR") ?? voices.find((v) => v.lang.startsWith("tr"));
    if (tr) u.voice = tr;
    u.onend = onEnd;
    u.onerror = onEnd;
    window.speechSynthesis.speak(u);
  };

  if (window.speechSynthesis.getVoices().length > 0) {
    trySpeak();
  } else {
    window.speechSynthesis.onvoiceschanged = () => { trySpeak(); };
  }
}

export function VoiceAssistant() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("idle");
  const [caption, setCaption] = useState("");
  const [action, setAction] = useState<ScrapeAction | null>(null);
  const [supported, setSupported] = useState(true);
  const [errMsg, setErrMsg] = useState("");
  const historyRef = useRef<{ role: string; content: string }[]>([]);
  const recogRef = useRef<SpeechRecognitionInstance | null>(null);

  useEffect(() => { if (!buildRecognition()) setSupported(false); }, []);

  const handleAnswer = useCallback(async (userText: string) => {
    setStatus("thinking");
    setCaption("");
    setErrMsg("");

    // Keep last 8 turns in memory
    historyRef.current = [...historyRef.current, { role: "user", content: userText }].slice(-8);

    try {
      const data = await voiceApi.chat(userText, historyRef.current.slice(0, -1));
      historyRef.current = [...historyRef.current, { role: "assistant", content: data.reply }].slice(-8);
      setCaption(data.reply);
      if (data.action) setAction(data.action);
      setStatus("speaking");
      speak(data.reply, () => setStatus("idle"));
    } catch {
      setErrMsg("Bağlantı hatası");
      setStatus("idle");
    }
  }, []);

  const startListening = useCallback(() => {
    const recog = buildRecognition();
    if (!recog) return;
    recogRef.current = recog;

    let gotResult = false;

    recog.onresult = (e: SpeechRecognitionEvent) => {
      gotResult = true;
      const text = e.results[0]?.[0]?.transcript?.trim();
      if (text) handleAnswer(text);
    };

    recog.onerror = (e: Event) => {
      const err = (e as ErrorEvent).message ?? "Mikrofon hatası";
      setErrMsg(err.includes("not-allowed") ? "Mikrofon izni reddedildi" : "Ses algılanamadı, tekrar dene");
      setStatus("idle");
    };

    recog.onend = () => {
      if (!gotResult) setStatus("idle");
    };

    setStatus("listening");
    setCaption("");
    setAction(null);
    setErrMsg("");
    recog.start();
  }, [handleAnswer]);

  const handleMicClick = useCallback(() => {
    if (status === "listening") {
      recogRef.current?.abort();
      recogRef.current = null;
      setStatus("idle");
    } else if (status === "speaking") {
      window.speechSynthesis?.cancel();
      setStatus("idle");
    } else if (status === "idle") {
      startListening();
    }
  }, [status, startListening]);

  const micColor = status === "listening" ? "#f43f5e"
    : status === "speaking" ? "#34d399"
    : status === "thinking" ? "#38bdf8"
    : "#4a5876";

  const micBg = status === "listening" ? "rgba(244,63,94,0.12)"
    : status === "speaking" ? "rgba(52,211,153,0.08)"
    : status === "thinking" ? "rgba(56,189,248,0.08)"
    : "transparent";

  const micBorder = status === "listening" ? "#f43f5e44"
    : status === "speaking" ? "#34d39944"
    : status === "thinking" ? "#38bdf844"
    : "#1c2742";

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col items-end gap-2">

      {/* Caption / action strip */}
      {(caption || errMsg || action) && (
        <div
          className="max-w-xs border px-3 py-2"
          style={{ background: "#0d1324", borderColor: action ? "#38bdf8" : "#1c2742" }}
        >
          {errMsg ? (
            <p className="font-mono text-[12px] text-hot">{errMsg}</p>
          ) : action ? (
            <div>
              <p className="font-mono text-[11px] text-accent tracking-wider uppercase mb-1">Tarama Başlatıldı</p>
              <p className="font-mono text-[13px] text-bright">
                {SECTOR_LABELS[action.sector] ?? action.sector} · {action.city}
                {action.district ? ` / ${action.district}` : ""}
              </p>
              <p className="font-mono text-[12px] text-dim">{caption}</p>
              <button
                type="button"
                onClick={() => { setAction(null); router.push("/jobs"); }}
                className="mt-1.5 font-mono text-[11px] uppercase tracking-wider px-2 py-0.5 border border-accent/40 text-accent hover:bg-accent/10 transition-all"
              >
                Görevlere Git →
              </button>
            </div>
          ) : (
            <p className="font-mono text-[13px] leading-relaxed" style={{ color: "#94a3b8" }}>
              {caption}
            </p>
          )}
        </div>
      )}

      {/* Mic button */}
      <button
        type="button"
        onClick={handleMicClick}
        disabled={!supported || status === "thinking"}
        title={
          !supported ? "Tarayıcın desteklemiyor (Chrome kullan)"
          : status === "listening" ? "Durdur"
          : status === "speaking" ? "Sessizleştir"
          : "Konuş"
        }
        className="flex items-center gap-2 border px-3 py-2 transition-all disabled:opacity-40"
        style={{ background: micBg, borderColor: micBorder }}
      >
        {status === "speaking" ? (
          <Volume2 className="h-4 w-4 shrink-0" style={{ color: micColor }} />
        ) : status === "listening" ? (
          <MicOff className="h-4 w-4 shrink-0" style={{ color: micColor }} />
        ) : status === "thinking" ? (
          <Zap className="h-4 w-4 shrink-0 animate-pulse" style={{ color: micColor }} />
        ) : (
          <Mic className="h-4 w-4 shrink-0" style={{ color: micColor }} />
        )}
        <span className="font-mono text-[11px] tracking-[0.2em] uppercase" style={{ color: micColor }}>
          {status === "listening" ? "Dinliyor" : status === "thinking" ? "Düşünüyor" : status === "speaking" ? "Konuşuyor" : "Asistan"}
        </span>
      </button>
    </div>
  );
}
