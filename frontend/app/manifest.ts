import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "C2D2 — Combat Decision Dominance",
    short_name: "C2D2",
    description: "AI-Powered Force Intelligence Platform — field evaluate, readiness, and battlespace.",
    start_url: "/assess",
    scope: "/",
    display: "standalone",
    orientation: "portrait-primary",
    background_color: "#0d1117",
    theme_color: "#f59e0b",
    icons: [
      {
        src: "/icon.svg",
        sizes: "512x512",
        type: "image/svg+xml",
        purpose: "any",
      },
      {
        src: "/icon.svg",
        sizes: "192x192",
        type: "image/svg+xml",
        purpose: "maskable",
      },
    ],
  };
}
