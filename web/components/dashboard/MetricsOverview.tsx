'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ZonesService, type ZoneSummaryResponse } from '@/src/api/generated';
import { Card } from '@/shared/ui/Card';

export function MetricsOverview() {
  const [summary, setSummary] = useState<ZoneSummaryResponse | null>(null);

  useEffect(() => {
    ZonesService.getZoneSummaryApiZonesSummaryGet().then(setSummary).catch(console.error);
  }, []);

  const metrics = [
    { label: 'Safe', value: summary?.safe ?? '-', color: 'text-slate-700', bg: 'bg-slate-500/10' },
    { label: 'Low', value: summary?.low ?? '-', color: 'text-emerald-700', bg: 'bg-emerald-500/10' },
    { label: 'Medium', value: summary?.medium ?? '-', color: 'text-amber-700', bg: 'bg-amber-500/10' },
    { label: 'High', value: summary?.high ?? '-', color: 'text-orange-700', bg: 'bg-orange-500/10' },
    { label: 'Danger', value: summary?.danger ?? '-', color: 'text-red-700', bg: 'bg-red-500/10 border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.3)]' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
      {metrics.map((m, i) => (
        <motion.div 
          key={m.label} 
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: i * 0.1 }}
        >
          <Card className={`text-center py-6 h-full ${m.bg}`}>
            <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2">{m.label}</h3>
            <p className={`text-4xl font-bold ${m.color}`}>{m.value}</p>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
