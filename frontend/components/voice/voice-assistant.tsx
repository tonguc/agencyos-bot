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

export function VoiceAssistant() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("idle");
  const [caption, setCaption] = useState("");
  const [action, setAction] = useState<ScrapeAction | null>(null);
  const [supported, setSupported] = useState(true);
  const [errMsg, setErrMsg] = useState("");
  const historyRef = useRef<{ role: string; content: string }[]>([]);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setSupported(false);
    }
  }, []);

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
  }, []);

  const handleTranscribed = useCallback(async (text: string) => {
    if (!text.trim()) { setStatus("idle"); return; }

    setStatus("thinking");
    setCaption("");
    setErrMsg("");
    setAction(null);

    historyRef.current = [...historyRef.current, { role: "user", content: text }].slice(-8);

    try {
      const data = await voiceApi.chat(text, historyRef.current.slice(0, -1));
      historyRef.current = [...historyRef.current, { role: "assistant", content: data.reply }].slice(-8);
      setCaption(data.reply);
      if (data.action) setAction(data.action);

      setStatus("speaking");
      const audio = await voiceApi.speak(data.reply);
      if (!audio) { setStatus("idle"); return; }
      audioRef.current = audio;
      audio.onended = () => setStatus("idle");
      audio.onerror = () => setStatus("idle");
      audio.play();
    } catch {
      setErrMsg("Bağlantı hatası");
      setStatus("idle");
    }
  }, []);

  const startListening = useCallback(async () => {
    setErrMsg("");
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setErrMsg("Mikrofon izni reddedildi");
      return;
    }

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
        if (error || !text) {
          setErrMsg(error ?? "Ses algılanamadı");
          setStatus("idle");
          return;
        }
        await handleTranscribed(text);
      } catch {
        setErrMsg("Transkripsiyon hatası");
        setStatus("idle");
      }
    };

    recorder.start();
    setStatus("listening");
  }, [handleTranscribed]);

  const stopListening = useCallback(() => {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
      recorderRef.current = null;
    }
  }, []);

  const handleMicClick = useCallback(() => {
    if (status === "listening") {
      stopListening();
    } else if (status === "speaking") {
      stopAudio();
      setStatus("idle");
    } else if (status === "idle") {
      startListening();
    }
  }, [status, startListening, stopListening, stopAudio]);

  useEffect(() => () => { stopAudio(); }, [stopAudio]);

  const micColor = status === "listening" ? "#f43f5e"
    : status === "speaking" ? "#34d399"
    : status === "thinking" ? "#38bdf8"
    : "#4a5876";

  const micBg = status === "listening" ? "rgba(244,63,94,0.12)"
    : status === "speaking" ? "rgba(52,211,153,0.08)"
    : status === "thinking" ? "rgba(56,189,248,0.08)"
    : "transparent";

  const micBorder = status === "listening" ? "#f43f5e55"
    : status === "speaking" ? "#34d39955"
    : status === "thinking" ? "#38bdf855"
    : "#1c2742";

  const label = status === "listening" ? "Dinliyor — durdurmak için tıkla"
    : status === "thinking" ? "Düşünüyor…"
    : status === "speaking" ? "Konuşuyor — durdurmak için tıkla"
    : "Asistan";

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col items-end gap-2">

      {/* Caption / error / action */}
      {(caption || errMsg || action) && (
        <div
          className="max-w-xs border px-3 py-2.5"
          style={{ background: "#0a0f1e", borderColor: action ? "#38bdf8" : "#1c2742" }}
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
              {caption && <p className="font-mono text-[12px] text-muted mt-0.5">{caption}</p>}
              <button
                type="button"
                onClick={() => { setAction(null); setCaption(""); router.push("/jobs"); }}
                className="mt-2 font-mono text-[11px] uppercase tracking-wider px-2 py-1 border border-accent/40 text-accent hover:bg-accent/10 transition-all"
              >
                Görevlere Git →
              </button>
            </div>
          ) : (
            <p className="font-mono text-[13px] leading-relaxed" style={{ color: "#94a3b8" }}>{caption}</p>
          )}
        </div>
      )}

      {/* Mic button */}
      <button
        type="button"
        onClick={handleMicClick}
        disabled={!supported || status === "thinking"}
        title={!supported ? "MediaRecorder desteklenmiyor" : label}
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
        <span className="font-mono text-[11px] tracking-[0.2em] uppercase whitespace-nowrap" style={{ color: micColor }}>
          {status === "listening" ? "Dinliyor" : status === "thinking" ? "Düşünüyor" : status === "speaking" ? "Konuşuyor" : "Asistan"}
        </span>
      </button>
    </div>
  );
}
