"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Volume2, Zap, AlertCircle } from "lucide-react";
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

const SECTOR_LABELS: Record<string, string> = {
  klinik: "Klinik", avukat: "Avukat", emlak: "Emlak", guzellik: "Güzellik",
  egitim: "Eğitim", ev_hizmetleri: "Tesisat", kadin_dogum: "Kadın Doğum",
  restoran: "Restoran", oto_servis: "Oto Servis", klima_beyaz_esya: "Klima / Beyaz Eşya",
  cilingir: "Çilingir", tadilat: "Tadilat", nakliyat: "Nakliyat", hali_temizlik: "Halı & Temizlik",
};

// ── Voices ──────────────────────────────────────────────────────────────

interface SpeechRecognitionEvent extends Event { results: SpeechRecognitionResultList; }
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

function buildBrowserSTT(): SpeechRecognitionInstance | null {
  const Ctor = typeof window !== "undefined" ? (window.SpeechRecognition ?? window.webkitSpeechRecognition) : undefined;
  if (!Ctor) return null;
  const r = new Ctor();
  r.lang = "tr-TR"; r.continuous = false; r.interimResults = false; r.maxAlternatives = 1;
  return r;
}

function getBestMimeType(): string {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return types.find((t) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) ?? "";
}

// Keep SpeechSynthesis alive (Chrome freezes after ~15s)
let _synthTimer: ReturnType<typeof setInterval> | null = null;
function synthKeepAlive(active: boolean) {
  if (active) {
    if (_synthTimer) return;
    _synthTimer = setInterval(() => {
      if (window.speechSynthesis?.speaking) {
        window.speechSynthesis.pause(); window.speechSynthesis.resume();
      }
    }, 8000);
  } else {
    if (_synthTimer) { clearInterval(_synthTimer); _synthTimer = null; }
  }
}

function pickTurkishVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const tr = voices.filter((v) => v.lang.toLowerCase().startsWith("tr"));
  if (!tr.length) return null;
  for (const test of [
    (v: SpeechSynthesisVoice) => /google/i.test(v.name),
    (v: SpeechSynthesisVoice) => /yelda|emel|tolga/i.test(v.name),
    (v: SpeechSynthesisVoice) => !v.localService,
    () => true,
  ]) { const m = tr.find(test); if (m) return m; }
  return tr[0];
}

function browserSpeak(text: string, onEnd: () => void): boolean {
  if (typeof window === "undefined" || !window.speechSynthesis) { onEnd(); return false; }
  window.speechSynthesis.cancel();
  synthKeepAlive(false);
  const doSpeak = () => {
    const tr = pickTurkishVoice(window.speechSynthesis.getVoices());
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "tr-TR"; u.rate = 1.0; u.pitch = 1.0;
    if (tr) u.voice = tr;
    u.onend = () => { synthKeepAlive(false); onEnd(); };
    u.onerror = () => { synthKeepAlive(false); onEnd(); };
    setTimeout(() => { window.speechSynthesis.speak(u); synthKeepAlive(true); }, 80);
  };
  if (window.speechSynthesis.getVoices().length > 0) doSpeak();
  else { window.speechSynthesis.onvoiceschanged = () => { window.speechSynthesis.onvoiceschanged = null; doSpeak(); }; }
  return true;
}

// ── Component ────────────────────────────────────────────────────────────

export function VoiceAssistant() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("idle");
  const [active, setActive] = useState(false);
  const [caption, setCaption] = useState("");
  const [action, setAction] = useState<ScrapeAction | null>(null);
  const [openaiReady, setOpenaiReady] = useState<boolean | null>(null); // null = loading
  const [noTurkishVoice, setNoTurkishVoice] = useState(false);

  const activeRef = useRef(false);
  const historyRef = useRef<{ role: string; content: string }[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // MediaRecorder state
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  // VAD
  const audioCtxRef = useRef<AudioContext | null>(null);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Check OpenAI availability on mount
  useEffect(() => {
    voiceApi.status().then((s) => setOpenaiReady(s.openai)).catch(() => setOpenaiReady(false));
  }, []);

  // ── Cleanup ──────────────────────────────────────────────────────────

  const stopEverything = useCallback(() => {
    abortRef.current?.abort(); abortRef.current = null;
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    window.speechSynthesis?.cancel(); synthKeepAlive(false);
    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    audioCtxRef.current?.close().catch(() => {}); audioCtxRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop()); streamRef.current = null;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    recorderRef.current = null;
  }, []);

  useEffect(() => () => stopEverything(), [stopEverything]);

  // ── TTS ─────────────────────────────────────────────────────────────

  const playReply = useCallback((text: string, onEnd: () => void) => {
    if (openaiReady) {
      voiceApi.speak(text).then((audio) => {
        if (audio) {
          audioRef.current = audio;
          audio.onended = onEnd;
          audio.onerror = () => { console.warn("[voice] OpenAI TTS error, falling back"); browserSpeak(text, onEnd); };
          audio.play().catch((e) => { console.warn("[voice] play() failed:", e); browserSpeak(text, onEnd); });
        } else {
          console.warn("[voice] speak() returned null — OpenAI TTS failed, falling back to browser");
          setNoTurkishVoice(true);
          browserSpeak(text, onEnd);
        }
      }).catch((e) => { console.warn("[voice] speak fetch error:", e); browserSpeak(text, onEnd); });
    } else {
      const tr = pickTurkishVoice(window.speechSynthesis?.getVoices() ?? []);
      if (!tr) setNoTurkishVoice(true);
      browserSpeak(text, onEnd);
    }
  }, [openaiReady]);

  // ── Chat ─────────────────────────────────────────────────────────────

  const goIdleOrRestart = useCallback(() => {
    setStatus("idle");
    if (activeRef.current) setTimeout(() => { if (activeRef.current) startListeningRef.current?.(); }, 120);
  }, []);

  const handleTranscribed = useCallback(async (text: string) => {
    if (!text.trim()) { goIdleOrRestart(); return; }
    setStatus("thinking"); setCaption(""); setAction(null);

    historyRef.current = [...historyRef.current, { role: "user", content: text }].slice(-6);
    const abort = new AbortController();
    abortRef.current = abort;

    try {
      const data = await voiceApi.chat(text, historyRef.current.slice(0, -1), abort.signal);
      if (abort.signal.aborted) return;

      historyRef.current = [...historyRef.current, { role: "assistant", content: data.reply }].slice(-12);
      setCaption(data.reply);
      if (data.action) {
        // Stop session after scrape — prevents TTS echo ("Başlattım") from re-triggering tool
        historyRef.current = [];
        activeRef.current = false;
        setActive(false);
        setAction(data.action);
        setStatus("speaking");
        playReply(data.reply, () => {
          setStatus("idle");
          router.push("/jobs");
        });
        return;
      }
      setStatus("speaking");
      playReply(data.reply, () => goIdleOrRestart());
    } catch (e) {
      if ((e as Error)?.name === "AbortError") return;
      goIdleOrRestart();
    } finally {
      if (abortRef.current === abort) abortRef.current = null;
    }
  }, [playReply, router, goIdleOrRestart]);

  // ── VAD (silence detection) ───────────────────────────────────────────

  const stopListeningAndSubmit = useCallback(() => {
    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    audioCtxRef.current?.close().catch(() => {}); audioCtxRef.current = null;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }, []);

  const startVAD = useCallback((stream: MediaStream) => {
    try {
      const ctx = new AudioContext();
      audioCtxRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);

      const buf = new Float32Array(analyser.frequencyBinCount);
      let silenceStart: number | null = null;
      let hadSpeech = false;
      const startTime = Date.now();
      const SILENCE_THRESHOLD = 0.018;
      const SILENCE_DURATION = 900;
      const MIN_SPEECH_MS = 1200; // don't auto-stop before user has spoken

      const check = () => {
        if (!audioCtxRef.current) return;
        analyser.getFloatTimeDomainData(buf);
        const rms = Math.sqrt(buf.reduce((s, v) => s + v * v, 0) / buf.length);
        if (rms >= SILENCE_THRESHOLD) {
          hadSpeech = true;
          silenceStart = null;
        } else if (hadSpeech && (Date.now() - startTime) > MIN_SPEECH_MS) {
          if (!silenceStart) silenceStart = Date.now();
          else if (Date.now() - silenceStart > SILENCE_DURATION) {
            stopListeningAndSubmit(); return;
          }
        }
        requestAnimationFrame(check);
      };
      requestAnimationFrame(check);
    } catch {
      // VAD unavailable, rely on manual stop
    }
  }, [stopListeningAndSubmit]);

  // ── Recording ─────────────────────────────────────────────────────────

  const startMediaRecorder = useCallback(async () => {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      goIdleOrRestart(); return;
    }
    streamRef.current = stream;
    const mimeType = getBestMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    recorderRef.current = recorder;
    chunksRef.current = [];
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    recorder.onstop = async () => {
      streamRef.current?.getTracks().forEach((t) => t.stop()); streamRef.current = null;
      const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
      const ext = mimeType.includes("mp4") ? "audio.mp4" : mimeType.includes("ogg") ? "audio.ogg" : "audio.webm";
      setStatus("thinking");
      try {
        const { text, error } = await voiceApi.transcribe(blob, ext);
        if (error || !text) { goIdleOrRestart(); return; }
        await handleTranscribed(text);
      } catch { goIdleOrRestart(); }
    };
    recorder.start(100);
    startVAD(stream);
    setStatus("listening");
  }, [handleTranscribed, startVAD, goIdleOrRestart]);

  const startBrowserSTT = useCallback(() => {
    const recog = buildBrowserSTT();
    if (!recog) { startMediaRecorder(); return; }
    let gotResult = false;
    recog.onresult = (e: SpeechRecognitionEvent) => {
      gotResult = true;
      const text = e.results[0]?.[0]?.transcript?.trim() ?? "";
      if (text) handleTranscribed(text);
      else goIdleOrRestart();
    };
    recog.onerror = () => goIdleOrRestart();
    recog.onend = () => { if (!gotResult) goIdleOrRestart(); };
    setStatus("listening");
    recog.start();
    // Auto-stop after 8s max
    silenceTimerRef.current = setTimeout(() => recog.stop(), 8000);
  }, [handleTranscribed, startMediaRecorder, goIdleOrRestart]);

  const startListening = useCallback(() => {
    // Browser STT preferred (free, low latency) — MediaRecorder+Whisper as fallback
    if (buildBrowserSTT()) startBrowserSTT();
    else startMediaRecorder();
  }, [startBrowserSTT, startMediaRecorder]);

  const startListeningRef = useRef(startListening);
  useEffect(() => { startListeningRef.current = startListening; }, [startListening]);

  const handleMicClick = useCallback(() => {
    if (!active) {
      // Start session — stays listening until user clicks again
      activeRef.current = true;
      setActive(true);
      startListening();
    } else {
      // End session
      activeRef.current = false;
      setActive(false);
      stopEverything();
      setStatus("idle");
    }
  }, [active, startListening, stopEverything]);

  // ── UI ───────────────────────────────────────────────────────────────

  const micColor =
    status === "listening" ? "#f43f5e" :
    status === "speaking"  ? "#34d399" :
    status === "thinking"  ? "#38bdf8" : "#4a5876";

  const micBorder =
    status === "listening" ? "#f43f5e55" :
    status === "speaking"  ? "#34d39955" :
    status === "thinking"  ? "#38bdf855" : "#1c2742";

  const statusLabel =
    status === "listening" ? "Dinliyor" :
    status === "thinking"  ? "Düşünüyor" :
    status === "speaking"  ? "Konuşuyor" :
    active ? "Hazır" : "Asistan";

  return (
    <div className="fixed top-4 right-4 md:top-6 md:right-6 z-50 flex flex-col items-end gap-3">

      {/* OpenAI not configured warning */}
      {openaiReady === false && (
        <div className="max-w-xs border px-3 py-2 flex items-start gap-2 rounded-lg" style={{ background: "#0a0f1e", borderColor: "#f59e0b55" }}>
          <AlertCircle className="h-4 w-4 text-warm shrink-0 mt-0.5" />
          <div>
            <p className="font-mono text-[11px] text-warm tracking-wide">Native Türkçe ses için</p>
            <p className="font-mono text-[11px] text-dim">Railway'e <span className="text-bright">OPENAI_API_KEY</span> ekle</p>
          </div>
        </div>
      )}

      {/* No Turkish browser voice warning */}
      {noTurkishVoice && !openaiReady && (
        <div className="max-w-xs border px-3 py-2 rounded-lg" style={{ background: "#0a0f1e", borderColor: "#f43f5e44" }}>
          <p className="font-mono text-[11px] text-hot">Sistemde Türkçe ses yok, İngilizce aksanla okunuyor</p>
        </div>
      )}

      {/* Scrape action card — auto-navigates to /jobs */}
      {action && (
        <div className="max-w-xs border px-3 py-2.5 rounded-lg" style={{ background: "#0a0f1e", borderColor: "#38bdf8" }}>
          <p className="font-mono text-[11px] text-accent tracking-wider uppercase mb-1">Tarama Başlatıldı</p>
          <p className="font-mono text-[13px] text-bright">
            {SECTOR_LABELS[action.sector] ?? action.sector} · {action.city}
            {action.district ? ` / ${action.district}` : ""}
          </p>
        </div>
      )}

      {/* Status label (only when active, above orb) */}
      {active && (
        <span className="font-mono text-[10px] tracking-[0.2em] uppercase px-2 py-0.5 rounded" style={{ color: micColor, background: `${micColor}10` }}>
          {statusLabel}
        </span>
      )}

      {/* Orb button */}
      <button type="button" onClick={handleMicClick}
        className="relative flex items-center justify-center w-14 h-14 md:w-16 md:h-16 rounded-full transition-all duration-300 hover:scale-105"
        style={{
          background: active
            ? `radial-gradient(circle, ${micColor}40 0%, ${micColor}15 50%, #0a0f1e 100%)`
            : `radial-gradient(circle, #38bdf820 0%, #1c2742 70%)`,
          boxShadow: active
            ? `0 0 24px ${micColor}55, 0 0 48px ${micColor}25, inset 0 0 16px ${micColor}20`
            : `0 0 12px #38bdf825, 0 4px 12px rgba(0,0,0,0.4)`,
          border: `1px solid ${active ? micColor : "#38bdf855"}`,
        }}
        title={active ? "Sohbeti sonlandır" : "Sohbeti başlat"}
        aria-label={active ? "Sohbeti sonlandır" : "Sohbeti başlat"}
      >
        {/* Slow ring — listening or speaking */}
        {(status === "listening" || status === "speaking") && (
          <span className="absolute -inset-1.5 rounded-full animate-pulse" style={{ border: `1.5px solid ${micColor}60` }} />
        )}

        {/* Icon */}
        <span className="relative z-10">
          {status === "speaking" ? <Volume2 className="h-5 w-5 md:h-6 md:w-6" style={{ color: active ? micColor : "#38bdf8" }} /> :
           status === "thinking"  ? <Zap className="h-5 w-5 md:h-6 md:w-6 animate-pulse" style={{ color: micColor }} /> :
           status === "listening" ? <MicOff className="h-5 w-5 md:h-6 md:w-6" style={{ color: micColor }} /> :
           <Mic className="h-5 w-5 md:h-6 md:w-6" style={{ color: active ? micColor : "#38bdf8" }} />}
        </span>
      </button>
    </div>
  );
}
