import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { VoiceAssistant } from "@/components/voice/voice-assistant";

export const metadata: Metadata = {
  title: "AgencyOS",
  description: "Otonom freelance ajans yönetim sistemi",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="flex h-full">
        <Sidebar />
        <main className="flex-1 overflow-auto flex flex-col">{children}</main>
        <VoiceAssistant />
      </body>
    </html>
  );
}
