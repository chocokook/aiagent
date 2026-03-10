import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TechHub Support",
  description: "AI-powered customer support for TechHub",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
