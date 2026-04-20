"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, X, Volume2 } from "lucide-react";
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

interface Message {
  role: "user" | "assistant";
  content: string;
  action?: ScrapeAction;
}

// SpeechRecognition types
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}
interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}
interface SpeechRecognitionInstance extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: SpeechRecognitionErrorEvent) => void) | null;
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

function getSpeechRecognition(): SpeechRecognitionInstance | null {
  if (typeof window === "undefined") return null;
  const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
  if (!Ctor) return null;
  const r = new Ctor();
  r.lang = "tr-TR";
  r.continuous = false;
  r.interimResults = false;
  return r;
}

function speak(text: string, onEnd: () => void) {
  if (typeof window === "undefined" || !window.speechSynthesis) { onEnd(); return; }
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "tr-TR";
  u.rate = 1.05;
  const voices = window.speechSynthesis.getVoices();
  const trVoice = voices.find((v) => v.lang.startsWith("tr"));
  if (trVoice) u.voice = trVoice;
  u.onend = onEnd;
  u.onerror = onEnd;
  window.speechSynthesis.speak(u);
}

const STATUS_LABEL: Record<Status, string> = {
  idle: "Konuşmak için mikrofona bas",
  listening: "Dinliyorum…",
  thinking: "Düşünüyorum…",
  speaking: "Konuşuyor…",
};

function ActionCard({ action, onNavigate }: { action: ScrapeAction; onNavigate: () => void }) {
  return (
    <div className="mt-2 border px-3 py-2.5 text-left" style={{ borderColor: "#38bdf8", background: "rgba(56,189,248,0.06)" }}>
      <p className="font-mono text-[11px] text-accent tracking-wider uppercase mb-1.5">Tarama Başlatıldı</p>
      <p className="font-mono text-[13px] text-bright">
        {SECTOR_LABELS[action.sector] ?? action.sector} · {action.city}{action.district ? ` / ${action.district}` : ""}
      </p>
      <p className="font-mono text-[12px] text-dim mt-0.5">{action.limit} lead hedefi</p>
      <button
        type="button"
        onClick={onNavigate}
        className="mt-2 font-mono text-[11px] uppercase tracking-wider px-3 py-1 border border-accent/40 text-accent hover:bg-accent/10 transition-all"
      >
        Görevlere Git →
      </button>
    </div>
  );
}

export function VoiceAssistant() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [supported, setSupported] = useState(true);
  const recogRef = useRef<SpeechRecognitionInstance | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (!getSpeechRecognition()) setSupported(false); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => () => { window.speechSynthesis?.cancel(); }, []);

  const stopListening = useCallback(() => {
    recogRef.current?.stop();
    recogRef.current = null;
  }, []);

  const handleAnswer = useCallback(async (userText: string) => {
    const withUser: Message[] = [...messages, { role: "user", content: userText }];
    setMessages(withUser);
    setStatus("thinking");

    try {
      const historyForApi = withUser.slice(-8).map((m) => ({ role: m.role, content: m.content }));
      const data = await voiceApi.chat(userText, historyForApi.slice(0, -1));
      const assistantMsg: Message = {
        role: "assistant",
        content: data.reply,
        action: data.action ?? undefined,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setStatus("speaking");
      speak(data.reply, () => setStatus("idle"));
    } catch {
      setStatus("idle");
    }
  }, [messages]);

  const startListening = useCallback(() => {
    if (status !== "idle") return;
    const recog = getSpeechRecognition();
    if (!recog) return;
    recogRef.current = recog;

    let gotResult = false;
    recog.onresult = (e: SpeechRecognitionEvent) => {
      gotResult = true;
      const text = e.results[0]?.[0]?.transcript?.trim();
      if (text) handleAnswer(text);
    };
    recog.onerror = () => setStatus("idle");
    recog.onend = () => { if (!gotResult) setStatus("idle"); };

    setStatus("listening");
    recog.start();
  }, [status, handleAnswer]);

  const handleMicClick = useCallback(() => {
    if (status === "listening") { stopListening(); setStatus("idle"); }
    else if (status === "speaking") { window.speechSynthesis?.cancel(); setStatus("idle"); }
    else if (status === "idle") startListening();
  }, [status, startListening, stopListening]);

  function handleClose() {
    stopListening();
    window.speechSynthesis?.cancel();
    setOpen(false);
    setStatus("idle");
  }

  const isActive = status !== "idle";

  return (
    <>
      {/* Floating button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        title="Sesli Asistan"
        className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center border transition-all"
        style={{
          background: open ? "rgba(56,189,248,0.15)" : "#0d1324",
          borderColor: open ? "#38bdf8" : "#1c2742",
          boxShadow: open ? "0 0 20px rgba(56,189,248,0.3)" : "0 0 10px rgba(0,0,0,0.5)",
        }}
      >
        <Mic className="h-5 w-5" style={{ color: open ? "#38bdf8" : "#4a5876" }} />
      </button>

      {/* Panel */}
      {open && (
        <div
          className="fixed bottom-22 right-6 z-50 flex flex-col border"
          style={{ width: 380, maxHeight: 520, background: "#0d1324", borderColor: "#1c2742", boxShadow: "0 0 40px rgba(0,0,0,0.7)" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: "#1c2742" }}>
            <div className="flex items-center gap-2">
              <div
                className="h-1.5 w-1.5 rounded-full"
                style={{
                  background: isActive ? "#38bdf8" : "#34d399",
                  boxShadow: isActive ? "0 0 6px #38bdf8" : "0 0 5px #34d399",
                  animation: "pulse 2s ease-in-out infinite",
                }}
              />
              <span className="font-mono text-[12px] tracking-[0.2em] text-bright uppercase">Sesli Asistan</span>
            </div>
            <div className="flex items-center gap-3">
              {messages.length > 0 && (
                <button type="button" onClick={() => setMessages([])} className="font-mono text-[11px] text-dim hover:text-muted transition-colors">
                  temizle
                </button>
              )}
              <button type="button" onClick={handleClose} className="text-dim hover:text-bright transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0" style={{ maxHeight: 360 }}>
            {messages.length === 0 ? (
              <p className="font-mono text-[12px] text-dim text-center py-8 tracking-wide leading-relaxed">
                {supported
                  ? "Merhaba! Hangi sektörde, hangi ilde lead arıyoruz?"
                  : "Tarayıcın sesli girişi desteklemiyor.\nChrome kullanmayı dene."}
              </p>
            ) : (
              messages.map((m, i) => (
                <div key={i} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
                  <div
                    className="max-w-[88%] px-3 py-2 font-mono text-[13px] leading-relaxed"
                    style={
                      m.role === "user"
                        ? { background: "rgba(56,189,248,0.08)", borderLeft: "2px solid #38bdf8", color: "#e6edf7" }
                        : { background: "#111827", borderLeft: "2px solid #1c2742", color: "#94a3b8" }
                    }
                  >
                    {m.content}
                  </div>
                  {m.action && (
                    <div className="max-w-[88%] w-full">
                      <ActionCard action={m.action} onNavigate={() => { router.push("/jobs"); handleClose(); }} />
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={bottomRef} />
          </div>

          {/* Status + mic */}
          <div className="px-4 py-3 border-t flex items-center gap-3" style={{ borderColor: "#1c2742" }}>
            <p
              className="flex-1 font-mono text-[11px] tracking-wider"
              style={{
                color: status === "listening" ? "#f43f5e"
                  : status === "thinking" ? "#38bdf8"
                  : status === "speaking" ? "#34d399"
                  : "#4a5876",
              }}
            >
              {STATUS_LABEL[status]}
            </p>
            {supported && (
              <button
                type="button"
                onClick={handleMicClick}
                disabled={status === "thinking"}
                className="flex h-9 w-9 items-center justify-center border transition-all disabled:opacity-40"
                style={
                  status === "listening"
                    ? { borderColor: "#f43f5e", background: "rgba(244,63,94,0.15)" }
                    : status === "speaking"
                    ? { borderColor: "#34d399", background: "rgba(52,211,153,0.1)" }
                    : { borderColor: "#1c2742", background: "transparent" }
                }
              >
                {status === "speaking" ? (
                  <Volume2 className="h-4 w-4" style={{ color: "#34d399" }} />
                ) : status === "listening" ? (
                  <MicOff className="h-4 w-4" style={{ color: "#f43f5e" }} />
                ) : (
                  <Mic className="h-4 w-4" style={{ color: status === "thinking" ? "#38bdf8" : "#4a5876" }} />
                )}
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}
