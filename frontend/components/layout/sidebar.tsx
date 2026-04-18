"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  BarChart3,
  Users,
  Search,
  BriefcaseBusiness,
  Settings,
  Zap,
} from "lucide-react";

const nav = [
  { href: "/", label: "Gösterge", icon: BarChart3 },
  { href: "/pipeline", label: "Pipeline", icon: BriefcaseBusiness },
  { href: "/leads", label: "Lead'ler", icon: Users },
  { href: "/scrape", label: "Lead Topla", icon: Search },
  { href: "/jobs", label: "İşler", icon: Zap },
  { href: "/settings", label: "Ayarlar", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 flex-col bg-slate-900 text-slate-100 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-5 border-b border-slate-800">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-sm">
          A
        </div>
        <span className="font-semibold text-white tracking-tight">AgencyOS</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-slate-800 text-xs text-slate-500">
        v0.1 · Tonguc
      </div>
    </aside>
  );
}
