'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { MetricsOverview } from '@/components/dashboard/MetricsOverview';
import { ZoneFeed } from '@/components/dashboard/ZoneFeed';
import { LiveAlerts } from '@/components/dashboard/LiveAlerts';
import { SubmitReportModal } from '@/components/SubmitReportModal';
import { ZoneDetailsModal } from '@/components/ZoneDetailsModal';
import { SubscribeCard } from '@/components/SubscribeButton';
import { OpenAPI, ZonesService, MetaService, type ZoneListResponse } from '@/src/api/generated';

// Configure the generated API client base URL
OpenAPI.BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/api$/, '');

const RiskTrendChart = dynamic(() => import('@/components/RiskTrendChart').then((mod) => mod.RiskTrendChart), { ssr: false });
const RainfallVsRiskChart = dynamic(() => import('@/components/RainfallVsRiskChart').then((mod) => mod.RainfallVsRiskChart), { ssr: false });
const ZoneMap = dynamic(() => import('@/components/ZoneMap').then((mod) => mod.ZoneMap), { ssr: false });

export default function Home() {
  const [zones, setZones] = useState<ZoneListResponse[]>([]);
  const [resourceCenters, setResourceCenters] = useState<any[]>([]);
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  const [detailsZoneId, setDetailsZoneId] = useState<string | null>(null);
  const [riskTrendData, setRiskTrendData] = useState<any[]>([]);
  const [rainfallVsRiskData, setRainfallVsRiskData] = useState<any[]>([]);

  useEffect(() => {
    ZonesService.getZonesApiZonesGet().then((data) => {
      setZones(data as any);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedZone) {
      ZonesService.getZoneRiskTrendApiZonesZoneIdRiskTrendGet(selectedZone, '24h')
        .then(setRiskTrendData).catch(console.error);
      ZonesService.getZoneRainfallVsRiskApiZonesZoneIdRainfallVsRiskGet(selectedZone, '24h')
        .then(setRainfallVsRiskData).catch(console.error);
    } else {
      setRiskTrendData([]);
      setRainfallVsRiskData([]);
    }
  }, [selectedZone]);

  const selectedZoneObj = zones.find((z: any) => z.id === selectedZone);
  const zoneName = selectedZoneObj?.name || 'Selected Zone';

  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  return (
    <div className="space-y-6 pb-24 relative">
      {/* Top row: Metrics Overview */}
      <MetricsOverview />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[800px]">
        {/* Left column: Zone Feed and Alerts */}
        <motion.div
          className="lg:col-span-4 xl:col-span-3 flex flex-col gap-6"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <SubscribeCard />
          <div className="h-[400px]">
            <ZoneFeed onZoneClick={(id) => {
              setSelectedZone(id);
              setDetailsZoneId(id);
            }} />
          </div>
          <div className="h-[400px]">
            <LiveAlerts onZoneClick={(id) => {
              setSelectedZone(id);
              setDetailsZoneId(id);
            }} />
          </div>
        </motion.div>

        {/* Center/Right column: Map and Charts */}
        <motion.div
          className="lg:col-span-8 xl:col-span-9 flex flex-col gap-6"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="h-[450px] rounded-xl overflow-hidden shadow-sm border border-white/60 bg-white/40 backdrop-blur-md z-0">
            <ZoneMap
              zones={zones as any}
              selectedZoneId={selectedZone}
              onZoneSelect={setSelectedZone}
              onViewDetails={setDetailsZoneId}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-[325px]">
            <div className="rounded-xl border border-white/60 bg-white/70 backdrop-blur-md p-4 shadow-sm flex flex-col">
              <h3 className="font-semibold text-slate-800 mb-2">Risk Trend</h3>
              <div className="flex-1 min-h-0">
                <RiskTrendChart data={riskTrendData} zoneName={zoneName} />
              </div>
            </div>
            <div className="rounded-xl border border-white/60 bg-white/70 backdrop-blur-md p-4 shadow-sm flex flex-col">
              <h3 className="font-semibold text-slate-800 mb-2">Rainfall vs Risk</h3>
              <div className="flex-1 min-h-0">
                <RainfallVsRiskChart data={rainfallVsRiskData} zoneName={zoneName} />
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      <div className="fixed bottom-6 right-6 z-40">
        <button
          onClick={() => setIsReportModalOpen(true)}
          className="flex items-center gap-2 rounded-full bg-blue-600 px-5 py-3 font-semibold text-white shadow-lg transition-transform hover:scale-105 hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-600/30"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><line x1="12" x2="12" y1="8" y2="12" /><line x1="12" x2="12.01" y1="16" y2="16" /></svg>
          Report an Incident
        </button>
      </div>

      <SubmitReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        zones={zones as any}
        selectedZoneId={selectedZone}
      />

      <ZoneDetailsModal
        isOpen={!!detailsZoneId}
        zoneId={detailsZoneId}
        onClose={() => setDetailsZoneId(null)}
      />
    </div>
  );
}