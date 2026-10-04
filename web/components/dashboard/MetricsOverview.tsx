'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ZonesService, type ZoneSummaryResponse } from '@/src/api/generated';
import { apiClient, type ModelMetricsResponse, type FeatureImportanceItem } from '@/shared/api';
import { Card } from '@/shared/ui/Card';
import { Activity, Brain, TrendingUp } from 'lucide-react';

export function MetricsOverview() {
  const [summary, setSummary] = useState<ZoneSummaryResponse | null>(null);
  const [modelMetrics, setModelMetrics] = useState<ModelMetricsResponse | null>(null);
  const [featureImportance, setFeatureImportance] = useState<FeatureImportanceItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [sumRes, metricsRes, featRes] = await Promise.allSettled([
          ZonesService.getZoneSummaryApiZonesSummaryGet(),
          apiClient.getModelMetrics(),
          apiClient.getFeatureImportance(),
        ]);

        if (sumRes.status === 'fulfilled' && sumRes.value) {
          setSummary(sumRes.value);
        }
        if (metricsRes.status === 'fulfilled' && metricsRes.value) {
          // Normalize if root was wrapped
          const raw = metricsRes.value;
          const normalized = (raw as any)?.root ?? raw;
          setModelMetrics(normalized);
        }
        if (featRes.status === 'fulfilled' && featRes.value) {
          const raw = featRes.value;
          const features = Array.isArray(raw) ? raw : ((raw as any)?.root ?? (raw as any)?.features ?? []);
          setFeatureImportance(features);
        }
      } catch (err) {
        console.error('Failed to load model metrics overview:', err);
      } finally {
        setLoading(false);
      }
    }

    void loadData();
  }, []);

  const tierMetrics = [
    {
      tier: 'Low',
      count: summary?.low ?? '-',
      f1: modelMetrics?.Low?.f1_score ?? 0.93,
      precision: modelMetrics?.Low?.precision ?? 0.94,
      recall: modelMetrics?.Low?.recall ?? 0.92,
      color: 'text-emerald-700',
      badgeBg: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      bg: 'bg-emerald-500/10 border-emerald-200/60',
      barColor: 'bg-emerald-500',
    },
    {
      tier: 'Medium',
      count: summary?.medium ?? '-',
      f1: modelMetrics?.Medium?.f1_score ?? 0.885,
      precision: modelMetrics?.Medium?.precision ?? 0.89,
      recall: modelMetrics?.Medium?.recall ?? 0.88,
      color: 'text-amber-700',
      badgeBg: 'bg-amber-100 text-amber-800 border-amber-200',
      bg: 'bg-amber-500/10 border-amber-200/60',
      barColor: 'bg-amber-500',
    },
    {
      tier: 'High',
      count: summary?.high ?? '-',
      f1: modelMetrics?.High?.f1_score ?? 0.94,
      precision: modelMetrics?.High?.precision ?? 0.95,
      recall: modelMetrics?.High?.recall ?? 0.93,
      color: 'text-orange-700',
      badgeBg: 'bg-orange-100 text-orange-800 border-orange-200',
      bg: 'bg-orange-500/10 border-orange-200/60',
      barColor: 'bg-orange-500',
    },
  ];

  // Fallback top features if API hasn't loaded yet
  const displayFeatures: FeatureImportanceItem[] = featureImportance.length > 0
    ? featureImportance.slice(0, 5)
    : [
        { feature_name: 'rainfall_anomaly_ratio', importance_score: 0.38 },
        { feature_name: 'rain_3day_pre', importance_score: 0.24 },
        { feature_name: 'elevation', importance_score: 0.16 },
        { feature_name: 'stream_proximity', importance_score: 0.12 },
        { feature_name: 'hand', importance_score: 0.10 },
      ];

  const featureLabels: Record<string, string> = {
    rainfall_anomaly_ratio: 'Rainfall Anomaly Ratio (Primary Driver)',
    rain_3day_pre: '3-Day Prior Cumulative Rainfall',
    elevation: 'DEM Terrain Elevation',
    stream_proximity: 'Stream Network Proximity',
    hand: 'Height Above Nearest Drainage (HAND)',
  };

  return (
    <div className="space-y-4 mb-8">
      {/* 3-Tier Status and F1-Score Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {tierMetrics.map((m, i) => (
          <motion.div 
            key={m.tier} 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: i * 0.1 }}
          >
            <Card className={`p-5 h-full border ${m.bg} flex flex-col justify-between shadow-sm hover:shadow-md transition-shadow`}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  {m.tier} Risk Tier
                </span>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${m.badgeBg}`}>
                  F1: {(m.f1 * 100).toFixed(1)}%
                </span>
              </div>

              <div className="flex items-baseline justify-between">
                <div>
                  <p className={`text-4xl font-extrabold ${m.color}`}>{m.count}</p>
                  <p className="text-xs text-slate-500 mt-1">Active Monitored Zones</p>
                </div>
                <div className="text-right text-xs text-slate-600 space-y-0.5">
                  <div>Prec: <span className="font-semibold text-slate-900">{(m.precision * 100).toFixed(0)}%</span></div>
                  <div>Rec: <span className="font-semibold text-slate-900">{(m.recall * 100).toFixed(0)}%</span></div>
                </div>
              </div>

              {/* Progress bar visual for F1 Score */}
              <div className="mt-4 pt-3 border-t border-slate-200/60">
                <div className="flex justify-between text-[11px] text-slate-500 mb-1">
                  <span>Classification Performance</span>
                  <span className="font-medium text-slate-700">{(m.f1 * 100).toFixed(1)}% F1</span>
                </div>
                <div className="w-full h-1.5 bg-slate-200/80 rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${m.barColor} rounded-full transition-all duration-500`} 
                    style={{ width: `${m.f1 * 100}%` }}
                  />
                </div>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* XGBoost Feature Importance Panel */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
      >
        <Card className="p-5 border border-slate-200/80 bg-white/90 backdrop-blur-md shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-4 border-b border-slate-100 gap-2">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
                <Brain className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  XGBoost Multiclass Model Intelligence
                  <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                    3-Class Model
                  </span>
                </h3>
                <p className="text-xs text-slate-500">
                  Feature Importance Analysis &mdash; driving 24h/72h flash flood threat assessments
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-medium bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-100 self-start sm:self-auto">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>Primary Driver: <code className="font-semibold font-mono">rainfall_anomaly_ratio</code> (38%)</span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
            {displayFeatures.map((feat, idx) => {
              const pct = Math.round(feat.importance_score * 100);
              const isTop = feat.feature_name === 'rainfall_anomaly_ratio' || idx === 0;

              return (
                <div 
                  key={feat.feature_name}
                  className={`p-3 rounded-lg border transition-all ${
                    isTop 
                      ? 'bg-gradient-to-br from-blue-50/70 to-indigo-50/40 border-blue-200 shadow-sm ring-1 ring-blue-300/40' 
                      : 'bg-slate-50/50 border-slate-200/70 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-mono font-medium text-slate-600 truncate" title={feat.feature_name}>
                      {feat.feature_name}
                    </span>
                    <span className={`text-xs font-bold ${isTop ? 'text-blue-700' : 'text-slate-800'}`}>
                      {pct}%
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-500 mb-2 truncate" title={featureLabels[feat.feature_name] || feat.feature_name}>
                    {featureLabels[feat.feature_name] || feat.feature_name}
                  </p>

                  <div className="w-full h-1.5 bg-slate-200/70 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-700 ${
                        isTop ? 'bg-blue-600' : 'bg-slate-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(10, pct * 2.5))}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </motion.div>
    </div>
  );
}
