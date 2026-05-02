import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import ActivationGate from "@/components/ActivationGate";
import TomeToast from "@/components/TomeToast";
import { WorkstationProvider } from "@/context/WorkstationContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Tome-Master",
  description: "Designed, Engineered, Programmed and Security Hardened by Bennett Consulting.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta 
          httpEquiv="Content-Security-Policy" 
          content="default-src 'self' http://localhost:8080 http://127.0.0.1:8080; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src 'self' fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self' http://localhost:8080 http://127.0.0.1:8080 http://localhost:11434 http://127.0.0.1:11434 ws://localhost:8080 ws://127.0.0.1:8080; frame-ancestors 'none'; object-src 'none';"
        />
        <script dangerouslySetInnerHTML={{ __html: `
          (function() {
            try {
              const savedTheme = localStorage.getItem('tome-master-theme');
              const theme = savedTheme || 'dark';
              document.documentElement.setAttribute('data-theme', theme);
            } catch (e) {}
          })();
        `}} />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <WorkstationProvider>
          <ActivationGate>
            {children}
          </ActivationGate>
        </WorkstationProvider>
        <TomeToast />
      </body>
    </html>
  );
}
