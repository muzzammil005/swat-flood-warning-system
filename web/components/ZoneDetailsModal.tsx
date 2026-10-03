'use client';

import { useState, useEffect } from 'react';
import { ZonesService, type ZoneDetailResponse } from '@/src/api/generated';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, Skeleton } from '@/shared/ui';
import { motion, AnimatePresence } from 'framer-motion';

interface ZoneDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  zoneId: string | null;
}

export function ZoneDetailsModal({ isOpen, onClose, zoneId }: ZoneDetailsModalProps) {
  const [data, setData] = useState<ZoneDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && zoneId) {
      setLoading(true);
      setError(null);
      ZonesService.getZoneApiZonesZoneIdGet(zoneId)
        .then(setData)
        .catch((err) => setError(err.message || 'Failed to load zone details'))
        .finally(() => setLoading(false));
    } else {
      setData(null);
    }
  }, [isOpen, zoneId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-neutral-900/40 p-4 backdrop-blur-sm">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="w-full max-w-3xl"
          >
            <Card className="max-h-[90vh] flex flex-col shadow-2xl border-white/60 bg-white/95 backdrop-blur-xl">
              <CardHeader className="flex flex-row items-center justify-between border-b border-neutral-200/50 pb-4 shrink-0">
                <CardTitle className="text-2xl font-bold flex items-center gap-3">
                  {loading ? (
                    <Skeleton className="h-8 w-48" />
                  ) : data ? (
                    <>
                      {data.zone.name}
                      <Badge tier={(data.zone.latest_assessment?.tier as any) || 'SAFE'} className="text-sm px-3 py-1" />
                    </>
                  ) : (
                    'Zone Details'
                  )}
                </CardTitle>
                <button onClick={onClose} className="text-neutral-500 hover:text-neutral-900 rounded-full p-2 hover:bg-neutral-100 transition-colors">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                </button>
              </CardHeader>
              <CardContent className="flex-1 overflow-y-auto overflow-x-hidden p-6 space-y-8">
                {loading ? (
                  <div className="space-y-6">
                    <Skeleton className="h-24 w-full rounded-xl" />
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <Skeleton className="h-40 w-full rounded-xl" />
                      <Skeleton className="h-40 w-full rounded-xl" />
                    </div>
                  </div>
                ) : error ? (
                  <div className="text-center text-red-500 py-10">
                    <p>{error}</p>
                    <Button variant="outline" onClick={onClose} className="mt-4">Close</Button>
                  </div>
                ) : data ? (
                  <>
                    {/* Assessment Section */}
                    <div className="space-y-3">
                      <h3 className="text-lg font-semibold text-neutral-800">Latest Risk Assessment</h3>
                      <div className="p-5 rounded-xl bg-gradient-to-br from-neutral-50 to-white border border-neutral-200 shadow-sm">
                        <p className="text-neutral-700 leading-relaxed text-lg">
                          {data.zone.latest_assessment?.explanation || 'No recent risk assessment available.'}
                        </p>
                        <div className="flex flex-wrap gap-6 mt-5 pt-4 border-t border-neutral-100 text-sm text-neutral-600">
                          <span className="flex items-center gap-2">
                            <span className="font-semibold text-neutral-900">Probability:</span> 
                            <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-medium">{((data.zone.latest_assessment?.probability || 0) * 100).toFixed(1)}%</span>
                          </span>
                          <span className="flex items-center gap-2">
                            <span className="font-semibold text-neutral-900">Computed:</span> 
                            {data.zone.latest_assessment?.computed_at ? new Date(data.zone.latest_assessment.computed_at).toLocaleString() : 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Sensor Readings */}
                      <div className="space-y-3">
                        <h3 className="text-lg font-semibold text-neutral-800">Recent Sensor Readings</h3>
                        {data.recent_readings.length > 0 ? (
                          <div className="space-y-2">
                            {data.recent_readings.slice(0, 4).map((reading, i) => (
                              <div key={reading.id || i} className="flex justify-between items-center p-3 rounded-xl border border-neutral-200 bg-white shadow-sm hover:border-blue-300 transition-colors">
                                <span className="font-semibold text-blue-600 text-lg">{(reading.water_level?.metres || 0).toFixed(2)}m</span>
                                <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider">{new Date(reading.timestamp).toLocaleString()}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-neutral-500 italic p-4 bg-neutral-50 rounded-xl border border-neutral-100">No recent readings</p>
                        )}
                      </div>

                      {/* Rainfall Data */}
                      <div className="space-y-3">
                        <h3 className="text-lg font-semibold text-neutral-800">Recent Weather</h3>
                        {data.recent_rainfall ? (
                          <div className="p-6 rounded-xl bg-gradient-to-br from-blue-50/80 to-indigo-50/30 border border-blue-100 shadow-sm space-y-4 h-[calc(100%-2rem)]">
                            <div>
                              <div className="text-sm font-semibold text-blue-600/80 uppercase tracking-wider mb-2">Accumulated Rainfall</div>
                              <div className="text-4xl font-black text-blue-700 tracking-tight">{data.recent_rainfall.rainfall?.millimetres?.toFixed(1)} <span className="text-xl font-semibold text-blue-600/50">mm</span></div>
                            </div>
                            <div className="flex flex-col gap-2 pt-4 border-t border-blue-100/50">
                              <span className="text-xs font-medium text-neutral-500 uppercase">Window: {data.recent_rainfall.rainfall?.duration_hours}h</span>
                              <span className="text-xs font-medium text-neutral-500 uppercase">Fetched: {new Date(data.recent_rainfall.fetched_at).toLocaleTimeString()}</span>
                            </div>
                          </div>
                        ) : (
                          <p className="text-neutral-500 italic p-4 bg-neutral-50 rounded-xl border border-neutral-100">No rainfall data available</p>
                        )}
                      </div>
                    </div>
                  </>
                ) : null}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
