'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertsService, type AlertListResponse } from '@/src/api/generated';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/ui/Card';
import { Badge } from '@/shared/ui/Badge';
import { Skeleton } from '@/shared/ui/Skeleton';

interface LiveAlertsProps {
  onZoneClick?: (zoneId: string) => void;
}

export function LiveAlerts({ onZoneClick }: LiveAlertsProps = {}) {
  const [alerts, setAlerts] = useState<AlertListResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAlerts = () => {
    AlertsService.getAlertsApiAlertsGet()
      .then(data => setAlerts(data.slice(0, 10))) // Top 10 most recent
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAlerts();
    const id = setInterval(fetchAlerts, 60000);
    return () => clearInterval(id);
  }, []);

  return (
    <Card className="h-full flex flex-col bg-gradient-to-b from-white/70 to-red-50/30 border-red-100/50">
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
            </span>
            Live Alerts
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto overflow-x-hidden pr-2">
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-slate-400">
            <p>No active alerts</p>
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {alerts.map((alert, i) => (
                <motion.div
                  key={alert.id}
                  onClick={() => onZoneClick?.(alert.zone_id)}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.1 }}
                  className="p-4 rounded-xl border border-red-100 bg-white/60 hover:bg-white/90 transition-colors shadow-sm cursor-pointer"
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-semibold text-red-500 tracking-wider uppercase truncate pr-2">{alert.headline}</span>
                    <Badge tier={alert.severity as any} />
                  </div>
                  <p className="text-sm font-medium text-slate-800 line-clamp-2">{alert.description}</p>
                  <p className="text-xs text-slate-400 mt-2">{new Date(alert.sent_at).toLocaleString()}</p>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
