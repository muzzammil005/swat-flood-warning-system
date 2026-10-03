'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ZonesService, type ZoneListResponse } from '@/src/api/generated';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/ui/Card';
import { Badge } from '@/shared/ui/Badge';
import { Skeleton } from '@/shared/ui/Skeleton';

interface ZoneFeedProps {
  onZoneClick?: (zoneId: string) => void;
}

export function ZoneFeed({ onZoneClick }: ZoneFeedProps = {}) {
  const [zones, setZones] = useState<ZoneListResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ZonesService.getZonesApiZonesGet()
      .then(setZones)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const sortedZones = useMemo(() => {
    const riskScore = { DANGER: 4, HIGH: 3, MEDIUM: 2, LOW: 1, SAFE: 0 };
    return [...zones].sort((a, b) => {
      const scoreA = riskScore[(a.latest_assessment?.tier as keyof typeof riskScore) ?? 'SAFE'];
      const scoreB = riskScore[(b.latest_assessment?.tier as keyof typeof riskScore) ?? 'SAFE'];
      return scoreB - scoreA;
    });
  }, [zones]);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>Monitored Zones</span>
          <span className="text-sm font-normal text-slate-500">{zones.length} active</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto overflow-x-hidden pr-2">
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {sortedZones.map((zone, i) => (
                <motion.div
                  key={zone.id}
                  onClick={() => onZoneClick?.(zone.id)}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-xl border border-white/40 bg-white/40 hover:bg-white/60 transition-colors flex flex-col justify-center cursor-pointer"
                >
                  <div className="flex justify-between items-start mb-1 gap-2">
                    <h4 className="font-semibold text-slate-800 leading-tight pt-0.5">{zone.name}</h4>
                    <div className="shrink-0">
                      <Badge tier={(zone.latest_assessment?.tier as any) || 'SAFE'} />
                    </div>
                  </div>
                  <p className="text-sm text-slate-500 line-clamp-2 leading-relaxed">
                    {zone.latest_assessment?.explanation || 'No recent data'}
                  </p>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
