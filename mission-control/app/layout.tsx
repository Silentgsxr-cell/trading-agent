import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { MarketStrip } from "@/components/MarketStrip";
import { TabTracker } from "@/components/TabTracker";

export const metadata: Metadata = {
  title: "ClawOps Control Center",
  description: "Mission control for Silent's ORB multi-agent trading system",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex min-h-screen flex-1 flex-col">
            <MarketStrip />
            <TabTracker />
            <main className="flex-1 px-5 py-5">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
