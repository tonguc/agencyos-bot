"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, X, Volume2 } from "lucide-react";
import { voiceApi } from "@/lib/api";

type Status = "idle" | "listening" | "thinking" | "speaking";

interface Message {
  role: "user" | "assistant";
  content: string;
}

// SpeechRecognition types (not in standard TS lib)
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
  u.pitch = 1.0;

  // Try to pick a Turkish voice
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

export function VoiceAssistant() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [transcript, setTranscript] = useState("");
  const [supported, setSupported] = useState(true);
  const recogRef = useRef<SpeechRecognitionInstance | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!getSpeechRecognition()) setSupported(false);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => () => { window.speechSynthesis?.cancel(); }, []);

  const stopListening = useCallback(() => {
    recogRef.current?.stop();
    recogRef.current = null;
  }, []);

  const handleAnswer = useCallback(async (userText: string) => {
    const updated: Message[] = [...messages, { role: "user", content: userText }];
    setMessages(updated);
    setTranscript("");
    setStatus("thinking");

    try {
      const history = updated.slice(-8).map((m) => ({ role: m.role, content: m.content }));
      const { reply } = await voiceApi.chat(userText, history.slice(0, -1));
      const next: Message[] = [...updated, { role: "assistant", content: reply }];
      setMessages(next);
      setStatus("speaking");
      speak(reply, () => setStatus("idle"));
    } catch {
      setStatus("idle");
    }
  }, [messages]);

  const startListening = useCallback(() => {
    if (status !== "idle") return;
    const recog = getSpeechRecognition();
    if (!recog) return;
    recogRef.current = recog;

    recog.onresult = (e: SpeechRecognitionEvent) => {
      const text = e.results[0]?.[0]?.transcript?.trim();
      if (text) handleAnswer(text);
    };
    recog.onerror = () => setStatus("idle");
    recog.onend = () => {
      if (status === "listening") setStatus("idle");
    };

    setStatus("listening");
    recog.start();
  }, [status, handleAnswer]);

  const handleMicClick = useCallback(() => {
    if (status === "listening") {
      stopListening();
      setStatus("idle");
    } else if (status === "speaking") {
      window.speechSynthesis?.cancel();
      setStatus("idle");
    } else if (status === "idle") {
      startListening();
    }
  }, [status, startListening, stopListening]);

  function handleClose() {
    stopListening();
    window.speechSynthesis?.cancel();
    setOpen(false);
    setStatus("idle");
    setTranscript("");
  }

  function clearHistory() {
    setMessages([]);
    setTranscript("");
  }

  const isActive = status !== "idle";

  return (
    <>
      {/* Floating trigger button */}
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
          style={{
            width: 360,
            maxHeight: 480,
            background: "#0d1324",
            borderColor: "#1c2742",
            boxShadow: "0 0 40px rgba(0,0,0,0.7)",
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: "#1c2742" }}>
            <div className="flex items-center gap-2">
              <div
                className="h-1.5 w-1.5 rounded-full"
                style={{
                  background: isActive ? "#38bdf8" : "#34d399",
                  boxShadow: isActive ? "0 0 6px #38bdf8" : "0 0 5px #34d399",
                  animation: isActive ? "pulse 1s ease-in-out infinite" : "pulse 2s ease-in-out infinite",
                }}
              />
              <span className="font-mono text-[12px] tracking-[0.2em] text-bright uppercase">Sesli Asistan</span>
            </div>
            <div className="flex items-center gap-2">
              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={clearHistory}
                  className="font-mono text-[11px] text-dim hover:text-muted transition-colors px-1"
                  title="Geçmişi temizle"
                >
                  temizle
                </button>
              )}
              <button
                type="button"
                onClick={handleClose}
                className="text-dim hover:text-bright transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0" style={{ maxHeight: 300 }}>
            {messages.length === 0 && (
              <p className="font-mono text-[12px] text-dim text-center py-6 tracking-wide">
                {supported
                  ? "Merhaba! Sana nasıl yardımcı olabilirim?"
                  : "Tarayıcın sesli girişi desteklemiyor. Chrome kullanmayı dene."}
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className="max-w-[85%] px-3 py-2 font-mono text-[13px] leading-relaxed"
                  style={
                    m.role === "user"
                      ? { background: "rgba(56,189,248,0.1)", borderLeft: "2px solid #38bdf8", color: "#e6edf7" }
                      : { background: "#111827", borderLeft: "2px solid #1c2742", color: "#94a3b8" }
                  }
                >
                  {m.content}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Status bar */}
          <div
            className="px-4 py-2 border-t flex items-center gap-3"
            style={{ borderColor: "#1c2742" }}
          >
            <div className="flex-1">
              <p
                className="font-mono text-[11px] tracking-wider"
                style={{ color: status === "listening" ? "#f43f5e" : status === "thinking" ? "#38bdf8" : status === "speaking" ? "#34d399" : "#4a5876" }}
              >
                {transcript || STATUS_LABEL[status]}
              </p>
            </div>

            {/* Mic / stop button */}
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
                title={status === "listening" ? "Durdur" : status === "speaking" ? "Sessizleştir" : "Konuş"}
              >
                {status === "speaking" ? (
                  <Volume2 className="h-4 w-4" style={{ color: "#34d399" }} />
                ) : status === "listening" ? (
                  <MicOff className="h-4 w-4" style={{ color: "#f43f5e" }} />
                ) : (
                  <Mic
                    className="h-4 w-4"
                    style={{ color: status === "thinking" ? "#38bdf8" : "#4a5876" }}
                  />
                )}
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}
