import type { Metadata } from "next";
import { Suspense } from "react";
import { MagicPath } from "@/components/MagicPath";
import { Nav } from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Living Data DNA Platform",
  description: "Data DNA Graph + Time Machine + AI Agents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="page-shell">
          <div className="bg-grid" />
          <div className="glow-orb orb-a" />
          <div className="glow-orb orb-b" />
          <main>
            <header className="hero">
              <h1>Living Data DNA Platform</h1>
              <p className="subtitle">Watch one schema mutation ripple through your stack, quantify business risk, and present the fix narrative in seconds.</p>
              <Nav />
              <Suspense fallback={null}>
                <MagicPath />
              </Suspense>
            </header>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
