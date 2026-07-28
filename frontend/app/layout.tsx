import type { Metadata } from "next";

import "./globals.css";
import { AppProviders } from "@/components/app-providers";

export const metadata: Metadata = {
  title: "Sentinel AI | Emergency Response Decision Support",
  description: "Emergency response decision support platform for incident commanders.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body><AppProviders>{children}</AppProviders></body>
    </html>
  );
}
