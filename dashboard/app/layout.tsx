import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "UPI Fraud Detector — Live Dashboard",
  description: "Real-time UPI transaction fraud detection. ML-powered risk scoring with SHAP explanations. Built with XGBoost, FastAPI, Kafka, and Next.js.",
  openGraph: {
    title: "UPI Fraud Detector",
    description: "Real-time fraud scoring for UPI transactions",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}
