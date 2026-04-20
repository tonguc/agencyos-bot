"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  BarChart3,
  Users,
  Search,
  Sparkles,
  Zap,
  Settings,
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
      className="flex h-screen w-14 flex-col shrink-0 border-r border-stroke"
      style={{ background: "#0d1324" }}
    >
      {/* Brand mark */}
      <div className="flex items-center justify-center py-4 border-b border-stroke">
        <div
          className="relative flex h-7 w-7 items-center justify-center border border-accent shrink-0"
          style={{ boxShadow: "0 0 10px rgba(56,189,248,0.3)" }}
          title="AgencyOS"
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
      </div>

      {/* Nav */}
      <nav className="flex-1 flex flex-col items-center py-3 gap-0.5">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={cn(
                "relative group flex items-center justify-center w-10 h-10 transition-all",
                active
                  ? "text-accent bg-accent/10 border-l-2 border-accent"
                  : "text-muted hover:text-bright hover:bg-panel-high border-l-2 border-transparent"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {/* Tooltip */}
              <span className="pointer-events-none absolute left-full ml-2 px-2 py-1 bg-panel border border-stroke font-mono text-[11px] text-bright whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-50 shadow-lg">
                {label}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Status dot */}
      <div className="flex items-center justify-center py-4 border-t border-stroke">
        <div
          className="h-1.5 w-1.5 rounded-full bg-ok"
          style={{ boxShadow: "0 0 5px #34d399", animation: "pulse 2s ease-in-out infinite" }}
          title="System Online"
        />
      </div>
    </aside>
  );
}
