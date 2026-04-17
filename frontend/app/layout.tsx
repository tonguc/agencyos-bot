import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";

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
      <body className="flex h-full bg-slate-50">
        <Sidebar />
        <main className="flex-1 overflow-auto flex flex-col">{children}</main>
      </body>
    </html>
  );
}
