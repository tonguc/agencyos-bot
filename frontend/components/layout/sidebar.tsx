"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  BarChart3,
  Users,
  Search,
  Sparkles,
  BriefcaseBusiness,
  Settings,
  Zap,
} from "lucide-react";

const nav = [
  { href: "/pipeline", label: "Pipeline",    icon: BarChart3 },
  { href: "/search",   label: "Firma Ara",   icon: Sparkles },
  { href: "/leads",    label: "Adaylar",     icon: Users },
  { href: "/scrape",   label: "Yeni Tarama", icon: Search },
  { href: "/jobs",     label: "Görevler",    icon: Zap },
  { href: "/settings", label: "Ayarlar",     icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="flex h-screen w-52 flex-col shrink-0 border-r border-stroke"
      style={{ background: "#0d1324" }}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-stroke">
        <div
          className="relative flex h-7 w-7 items-center justify-center border border-accent shrink-0"
          style={{ boxShadow: "0 0 10px rgba(56,189,248,0.3)" }}
        >
          <div
            className="absolute inset-1 border border-dashed border-accent opacity-50"
            style={{ animation: "spin 10s linear infinite" }}
          />
          <div
            className="h-1.5 w-1.5 rounded-full bg-accent"
            style={{ boxShadow: "0 0 6px #38bdf8" }}
          />
        </div>
        <div>
          <p className="font-mono font-bold text-bright text-[13px] tracking-[0.2em]">AGENCYOS</p>
          <p className="font-mono text-[11px] text-dim tracking-[0.15em]">/ INTEL</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 text-[12px] font-mono font-medium tracking-[0.15em] uppercase transition-all",
                active
                  ? "text-accent bg-accent/10 border-l-2 border-accent"
                  : "text-muted hover:text-bright hover:bg-panel-high border-l-2 border-transparent"
              )}
            >
              <Icon className="h-3.5 w-3.5 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Status footer */}
      <div className="px-4 py-4 border-t border-stroke">
        <div className="flex items-center gap-2">
          <div
            className="h-1.5 w-1.5 rounded-full bg-ok"
            style={{ boxShadow: "0 0 5px #34d399", animation: "pulse 2s ease-in-out infinite" }}
          />
          <span className="font-mono text-[11px] text-dim tracking-[0.2em]">SYSTEM · ONLINE</span>
        </div>
      </div>
    </aside>
  );
}
