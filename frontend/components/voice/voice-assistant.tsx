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
  lang: string; continuous: boolean; interimResults: boolean; maxAlternatives: number;
  start(): void; stop(): void; abort(): void;
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

function getBestMimeType(): string {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return types.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
}

// Browser TTS fallback — pick best Turkish voice (quality-ranked)
function pickTurkishVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const tr = voices.filter((v) => v.lang.toLowerCase().startsWith("tr"));
  if (tr.length === 0) return null;
  const preferred = [
    (v: SpeechSynthesisVoice) => /google/i.test(v.name),
    (v: SpeechSynthesisVoice) => /yelda|emel|tolga|microsoft/i.test(v.name),
    (v: SpeechSynthesisVoice) => !v.localService,
    () => true,
  ];
  for (const test of preferred) {
    const match = tr.find(test);
    if (match) return match;
  }
  return tr[0];
}

// Chrome bug workaround: speechSynthesis freezes after ~15s
// Keep it alive by pausing/resuming every 10s while speaking
let keepAliveTimer: ReturnType<typeof setInterval> | null = null;
function startKeepAlive() {
  if (keepAliveTimer) return;
  keepAliveTimer = setInterval(() => {
    if (window.speechSynthesis?.speaking) {
      window.speechSynthesis.pause();
      window.speechSynthesis.resume();
    }
  }, 10000);
}
function stopKeepAlive() {
  if (keepAliveTimer) { clearInterval(keepAliveTimer); keepAliveTimer = null; }
}

interface BrowserSpeakResult {
  ok: boolean;
  usedFallbackLang: boolean; // true if no Turkish voice found
}

function browserSpeak(text: string, onEnd: () => void): Promise<BrowserSpeakResult> {
  return new Promise((resolve) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      onEnd();
      resolve({ ok: false, usedFallbackLang: false });
      return;
    }

    // Full reset — fixes "second question no sound" Chrome bug
    window.speechSynthesis.cancel();
    stopKeepAlive();

    const doSpeak = () => {
      const tr = pickTurkishVoice(window.speechSynthesis.getVoices());
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "tr-TR";
      u.rate = 1.0;
      u.pitch = 1.0;
      if (tr) u.voice = tr;

      const finish = () => {
        stopKeepAlive();
        onEnd();
      };
      u.onend = finish;
      u.onerror = finish;

      // Small delay before speaking — lets Chrome fully reset after cancel()
      setTimeout(() => {
        window.speechSynthesis.speak(u);
        startKeepAlive();
        resolve({ ok: true, usedFallbackLang: !tr });
      }, 80);
    };

    if (window.speechSynthesis.getVoices().length > 0) {
      doSpeak();
    } else {
      window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.onvoiceschanged = null;
        doSpeak();
      };
    }
  });
}

// Browser STT fallback (Chrome/Edge only)
function buildBrowserRecognition(): SpeechRecognitionInstance | null {
  if (typeof window === "undefined") return null;
  const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
  if (!Ctor) return null;
  const r = new Ctor();
  r.lang = "tr-TR"; r.continuous = false; r.interimResults = false; r.maxAlternatives = 1;
  return r;
}

export function VoiceAssistant() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("idle");
  const [caption, setCaption] = useState("");
  const [action, setAction] = useState<ScrapeAction | null>(null);
  const [supported, setSupported] = useState(true);
  const [errMsg, setErrMsg] = useState("");
  const historyRef = useRef<{ role: string; content: string }[]>([]);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const browserRecogRef = useRef<SpeechRecognitionInstance | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const hasMediaRecorder = useRef(false);
  const hasBrowserSTT = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    hasMediaRecorder.current = !!(navigator.mediaDevices && typeof window.MediaRecorder !== "undefined");
    hasBrowserSTT.current = !!buildBrowserRecognition();
    if (!hasMediaRecorder.current && !hasBrowserSTT.current) setSupported(false);
  }, []);

  const stopAudio = useCallback(() => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    window.speechSynthesis?.cancel();
    stopKeepAlive();
  }, []);

  const interrupt = useCallback(() => {
    stopAudio();
    if (abortRef.current) { abortRef.current.abort(); abortRef.current = null; }
    if (recorderRef.current?.state === "recording") { recorderRef.current.stop(); recorderRef.current = null; }
    if (browserRecogRef.current) { browserRecogRef.current.abort(); browserRecogRef.current = null; }
  }, [stopAudio]);

  // Play reply: try OpenAI TTS (native Turkish), fall back to browser
  const playReply = useCallback((text: string, onEnd: () => void) => {
    const tryBrowser = () => {
      browserSpeak(text, onEnd).then((r) => {
        if (r.ok && r.usedFallbackLang) {
          setErrMsg("Türkçe ses yok — OPENAI_API_KEY ekle (native ses için)");
        }
      });
    };
    voiceApi.speak(text).then((audio) => {
      if (audio) {
        audioRef.current = audio;
        audio.onended = onEnd;
        audio.onerror = tryBrowser;
        audio.play().catch(tryBrowser);
      } else {
        tryBrowser();
      }
    }).catch(tryBrowser);
  }, []);

  const handleTranscribed = useCallback(async (text: string) => {
    if (!text.trim()) { setStatus("idle"); return; }
    setStatus("thinking"); setCaption(""); setErrMsg(""); setAction(null);
    historyRef.current = [...historyRef.current, { role: "user", content: text }].slice(-8);

    const abort = new AbortController();
    abortRef.current = abort;
    try {
      const data = await voiceApi.chat(text, historyRef.current.slice(0, -1), abort.signal);
      if (abort.signal.aborted) return;
      historyRef.current = [...historyRef.current, { role: "assistant", content: data.reply }].slice(-8);
      setCaption(data.reply);
      if (data.action) setAction(data.action);
      setStatus("speaking");
      playReply(data.reply, () => setStatus("idle"));
    } catch (e) {
      if ((e as Error)?.name === "AbortError") return;
      setErrMsg("Bağlantı hatası"); setStatus("idle");
    } finally {
      if (abortRef.current === abort) abortRef.current = null;
    }
  }, [playReply]);

  // MediaRecorder-based recording (all browsers)
  const startMediaRecorder = useCallback(async () => {
    let stream: MediaStream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch { setErrMsg("Mikrofon izni reddedildi"); return; }

    const mimeType = getBestMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    recorderRef.current = recorder;
    chunksRef.current = [];
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
      const ext = mimeType.includes("mp4") ? "audio.mp4" : mimeType.includes("ogg") ? "audio.ogg" : "audio.webm";
      setStatus("thinking");
      try {
        const { text, error } = await voiceApi.transcribe(blob, ext);
        if (error || !text) { setErrMsg(error ?? "Ses algılanamadı"); setStatus("idle"); return; }
        await handleTranscribed(text);
      } catch { setErrMsg("Transkripsiyon hatası"); setStatus("idle"); }
    };
    recorder.start();
    setStatus("listening");
  }, [handleTranscribed]);

  // Browser SpeechRecognition fallback (Chrome/Edge)
  const startBrowserRecognition = useCallback(() => {
    const recog = buildBrowserRecognition();
    if (!recog) { setErrMsg("Ses desteği yok"); return; }
    browserRecogRef.current = recog;
    let gotResult = false;
    recog.onresult = (e: SpeechRecognitionEvent) => {
      gotResult = true;
      const text = e.results[0]?.[0]?.transcript?.trim();
      if (text) handleTranscribed(text);
    };
    recog.onerror = () => { setErrMsg("Ses algılanamadı"); setStatus("idle"); };
    recog.onend = () => { if (!gotResult) setStatus("idle"); };
    setStatus("listening");
    recog.start();
  }, [handleTranscribed]);

  const startListening = useCallback(() => {
    setErrMsg("");
    // Prefer browser STT (free, works without OPENAI_API_KEY in Chrome/Edge)
    // Fall back to MediaRecorder + Whisper for Firefox/Safari
    if (hasBrowserSTT.current) startBrowserRecognition();
    else if (hasMediaRecorder.current) startMediaRecorder();
  }, [startMediaRecorder, startBrowserRecognition]);

  const stopListening = useCallback(() => {
    if (recorderRef.current?.state === "recording") { recorderRef.current.stop(); recorderRef.current = null; }
    else if (browserRecogRef.current) { browserRecogRef.current.stop(); browserRecogRef.current = null; }
  }, []);

  const handleMicClick = useCallback(() => {
    if (status === "listening") { stopListening(); }
    else if (status === "idle") { startListening(); }
    else { interrupt(); setStatus("idle"); setTimeout(() => startListening(), 50); }
  }, [status, startListening, stopListening, interrupt]);

  useEffect(() => () => { interrupt(); }, [interrupt]);

  const micColor = status === "listening" ? "#f43f5e" : status === "speaking" ? "#34d399" : status === "thinking" ? "#38bdf8" : "#4a5876";
  const micBg = status === "listening" ? "rgba(244,63,94,0.12)" : status === "speaking" ? "rgba(52,211,153,0.08)" : status === "thinking" ? "rgba(56,189,248,0.08)" : "transparent";
  const micBorder = status === "listening" ? "#f43f5e55" : status === "speaking" ? "#34d39955" : status === "thinking" ? "#38bdf855" : "#1c2742";
  const micLabel = status === "listening" ? "Dinliyor" : status === "thinking" ? "Düşünüyor" : status === "speaking" ? "Konuşuyor" : "Asistan";

  return (
    <div className="fixed top-3 right-3 md:top-4 md:right-4 z-50 flex flex-col items-end gap-2">
      {(caption || errMsg || action) && (
        <div className="max-w-[260px] md:max-w-xs border px-3 py-2.5" style={{ background: "#0a0f1e", borderColor: action ? "#38bdf8" : "#1c2742" }}>
          {errMsg ? (
            <p className="font-mono text-[12px] text-hot">{errMsg}</p>
          ) : action ? (
            <div>
              <p className="font-mono text-[11px] text-accent tracking-wider uppercase mb-1">Tarama Başlatıldı</p>
              <p className="font-mono text-[12px] text-bright">{SECTOR_LABELS[action.sector] ?? action.sector} · {action.city}{action.district ? ` / ${action.district}` : ""}</p>
              {caption && <p className="font-mono text-[11px] text-muted mt-0.5">{caption}</p>}
              <button type="button" onClick={() => { setAction(null); setCaption(""); router.push("/jobs"); }}
                className="mt-1.5 font-mono text-[11px] uppercase tracking-wider px-2 py-1 border border-accent/40 text-accent hover:bg-accent/10 transition-all">
                Görevlere Git →
              </button>
            </div>
          ) : (
            <p className="font-mono text-[12px] leading-relaxed" style={{ color: "#94a3b8" }}>{caption}</p>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={handleMicClick}
        disabled={!supported}
        className="flex items-center gap-2 border px-3 py-2 transition-all disabled:opacity-40"
        style={{ background: micBg, borderColor: micBorder }}
      >
        {status === "speaking" ? <Volume2 className="h-4 w-4 shrink-0" style={{ color: micColor }} />
          : status === "listening" ? <MicOff className="h-4 w-4 shrink-0" style={{ color: micColor }} />
          : status === "thinking" ? <Zap className="h-4 w-4 shrink-0 animate-pulse" style={{ color: micColor }} />
          : <Mic className="h-4 w-4 shrink-0" style={{ color: micColor }} />}
        <span className="font-mono text-[11px] tracking-[0.2em] uppercase hidden sm:inline" style={{ color: micColor }}>{micLabel}</span>
      </button>
    </div>
  );
}
