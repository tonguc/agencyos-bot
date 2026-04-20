"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { BarChart3, Users, Search, Sparkles, BriefcaseBusiness, Settings, Zap } from "lucide-react";

const nav = [
  { href: "/pipeline", label: "Pipeline", icon: BarChart3 },
  { href: "/search",   label: "Ara",      icon: Sparkles },
  { href: "/leads",    label: "Adaylar",  icon: Users },
  { href: "/scrape",   label: "Tarama",   icon: Search },
  { href: "/jobs",     label: "Görevler", icon: Zap },
  { href: "/settings", label: "Ayarlar",  icon: Settings },
];

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex md:hidden border-t border-stroke"
      style={{ background: "#0d1324" }}
    >
      {nav.map(({ href, label, icon: Icon }) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex flex-1 flex-col items-center gap-0.5 py-2.5 text-center transition-all",
              active ? "text-accent" : "text-dim"
            )}
          >
            <Icon className="h-4 w-4" />
            <span className="font-mono text-[9px] tracking-wider uppercase">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
