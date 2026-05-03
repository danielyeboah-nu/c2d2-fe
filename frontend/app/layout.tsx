import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/AuthContext";
import { OfflineIndicator } from "@/components/OfflineIndicator";
import { RegisterServiceWorker } from "@/components/RegisterServiceWorker";
import { SimulationProvider } from "@/contexts/SimulationContext";

export const metadata: Metadata = {
  title: "C2D2 — Combat Decision Dominance",
  description: "AI-Powered Force Intelligence Platform",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "C2D2",
  },
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
};

export const viewport: Viewport = {
  themeColor: "#f59e0b",
  width: "device-width",
  initialScale: 1,
  minimumScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <SimulationProvider>{children}</SimulationProvider>
        </AuthProvider>
        <OfflineIndicator />
        <RegisterServiceWorker />
      </body>
    </html>
  );
}
