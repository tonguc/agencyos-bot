"use client";

import { cn } from "@/lib/utils";
import {
  Swords,
  Megaphone,
  Share2,
  ShoppingCart,
} from "lucide-react";

interface ScoreEntry {
  label: string;
  value: number | null;
  icon: React.ElementType;
  color: string;
  description: string;
  thresholds: { high: number; mid: number };
}

const SCORES: ScoreEntry[] = [
  {
    label: "Rekabet",
    value: null,
    icon: Swords,
    color: "text-hot",
    description: "Bölgedeki güçlü rakipler",
    thresholds: { high: 70, mid: 40 },
  },
  {
    label: "PPC İsraf",
    value: null,
    icon: Megaphone,
    color: "text-warm",
    description: "Reklam bütçesi yanlış harcanıyor",
    thresholds: { high: 60, mid: 30 },
  },
  {
    label: "Sosyal Uyumsuzluk",
    value: null,
    icon: Share2,
    color: "text-review",
    description: "Sosyal aktif ama site zayıf",
    thresholds: { high: 60, mid: 30 },
  },
  {
    label: "E-Ticaret Aciliyet",
    value: null,
    icon: ShoppingCart,
    color: "text-ok",
    description: "Fiziksel-only, yüksek potansiyel",
    thresholds: { high: 70, mid: 40 },
  },
];

function barColor(v: number, thresholds: { high: number; mid: number }): string {
  if (v >= thresholds.high) return "from-hot to-red-500";
  if (v >= thresholds.mid) return "from-warm to-orange-400";
  return "from-dim to-slate-500";
}

function labelColor(v: number, thresholds: { high: number; mid: number }): string {
  if (v >= thresholds.high) return "text-hot";
  if (v >= thresholds.mid) return "text-warm";
  return "text-dim";
}

interface Props {
  competitionDensity?: number | null;
  ppcWaste?: number | null;
  socialMismatch?: number | null;
  ecommerceUrgency?: number | null;
  compact?: boolean;
}

export function AdvancedScores({
  competitionDensity,
  ppcWaste,
  socialMismatch,
  ecommerceUrgency,
  compact = false,
}: Props) {
  const values = [competitionDensity, ppcWaste, socialMismatch, ecommerceUrgency];
  const allNull = values.every((v) => v == null);
  if (allNull) return null;

  const entries = SCORES.map((s, i) => ({
    ...s,
    value: values[i] ?? 0,
  }));

  if (compact) {
    return (
      <div className="flex flex-wrap gap-1.5">
        {entries
          .filter((e) => e.value > 0)
          .map((e) => {
            const Icon = e.icon;
            return (
              <span
                key={e.label}
                className={cn(
                  "inline-flex items-center gap-1 font-mono text-[10px] px-1.5 py-0.5 border border-stroke-2",
                  labelColor(e.value, e.thresholds)
                )}
                title={`${e.description}: ${e.value}/100`}
              >
                <Icon className="h-2.5 w-2.5" />
                {e.label} {e.value}
              </span>
            );
          })}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="font-mono text-[10px] text-dim uppercase tracking-[0.15em]">
        Mikro-Skoring · 4 Kriter
      </p>
      <div className="grid grid-cols-2 gap-3">
        {entries.map((e) => {
          const Icon = e.icon;
          return (
            <div key={e.label} className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Icon className={cn("h-3 w-3", e.color)} />
                <span className="font-mono text-[11px] text-muted uppercase tracking-wider">
                  {e.label}
                </span>
                <span
                  className={cn(
                    "ml-auto font-mono text-[11px] font-bold",
                    labelColor(e.value, e.thresholds)
                  )}
                >
                  {e.value}
                </span>
              </div>
              <div className="h-1 w-full bg-stroke overflow-hidden">
                <div
                  className={cn(
                    "h-full bg-gradient-to-r transition-all duration-300",
                    barColor(e.value, e.thresholds)
                  )}
                  style={{ width: `${Math.max(e.value, 2)}%` }}
                />
              </div>
              <p className="font-mono text-[9px] text-dim">{e.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}