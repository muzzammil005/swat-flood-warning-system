import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import Link from "next/link";
import 'leaflet/dist/leaflet.css';
import "./globals.css";
import './leaflet-overrides.css';
import { Toaster } from 'react-hot-toast';
import { RedAlertProvider } from '@/components/RedAlertProvider';
import { HeaderAction } from '@/components/HeaderAction';

const outfit = Outfit({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Swat Flood Monitoring Dashboard",
  description: "Real-time flood risk monitoring for Swat district",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${outfit.className} antialiased bg-gradient-to-br from-slate-50 via-white to-blue-50 text-slate-900`}>
        <Toaster position="top-right" />
        <div className="min-h-screen relative">
          <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-400/20 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-blob"></div>
            <div className="absolute top-[20%] right-[-10%] w-[30%] h-[30%] bg-purple-300/20 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-blob animation-delay-2000"></div>
            <div className="absolute bottom-[-20%] left-[20%] w-[40%] h-[40%] bg-emerald-300/20 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-blob animation-delay-4000"></div>
          </div>
          
          <RedAlertProvider>
            <div className="relative z-10">
              <header className="sticky top-0 z-50 border-b border-white/40 bg-white/60 backdrop-blur-xl shadow-sm">
                <div className="container mx-auto px-4 py-4">
                <div className="flex items-center justify-between">
                  <Link href="/" className="flex items-center space-x-3 hover:opacity-90 transition-opacity">
                    <div className="relative w-9 h-9">
                      <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl shadow-sm"></div>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                        </svg>
                      </div>
                    </div>
                    <h1 className="text-2xl font-bold">Swat Flood Monitoring</h1>
                  </Link>
                  <div className="flex items-center space-x-4">
                    <div className="text-sm text-neutral-500">
                      Real-time risk assessment
                    </div>
                    <HeaderAction />
                  </div>
                </div>
              </div>
            </header>
            <main className="container mx-auto px-4 py-8">
              {children}
            </main>
            <footer className="border-t border-neutral-200 bg-white py-4">
              <div className="container mx-auto px-4 text-center text-neutral-500 text-sm">
                <p>Swat District Flood Monitoring System • Data updates every 15 minutes</p>
              </div>
            </footer>
            </div>
          </RedAlertProvider>
        </div>
      </body>
    </html>
  );
}