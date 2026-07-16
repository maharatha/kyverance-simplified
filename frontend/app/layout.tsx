import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kyverance",
  description: "AI-native community for simulated portfolios",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
