'use client';

import { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { LineChart, CloudRain, Activity } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ChartOptions,
  ChartData,
} from 'chart.js';
import { apiClient, RiskTrendPoint, RiskTier, DailyRainfallRecord } from '@/shared/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface RiskTrendChartProps {
  data?: RiskTrendPoint[];
  zoneName?: string;
  zoneId?: string | null;
}

export const RiskTrendChart: React.FC<RiskTrendChartProps> = ({ 
  data = [], 
  zoneName = 'Swat District', 
  zoneId 
}) => {
  const [activeTab, setActiveTab] = useState<'history' | 'trend'>('history');
  const [historyData, setHistoryData] = useState<DailyRainfallRecord[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Default to zone-kalam if not specified, ensuring panel always sees data
  const effectiveZoneId = zoneId || 'zone-kalam';

  useEffect(() => {
    let isMounted = true;
    if (!effectiveZoneId) return;

    setLoadingHistory(true);
    apiClient.getZoneRainfallHistory(effectiveZoneId)
      .then((res) => {
        if (isMounted && res?.thirty_day_history) {
          setHistoryData(res.thirty_day_history);
        }
      })
      .catch((err) => {
        console.warn(`Could not load rainfall history for ${effectiveZoneId}:`, err);
      })
      .finally(() => {
        if (isMounted) setLoadingHistory(false);
      });

    return () => {
      isMounted = false;
    };
  }, [effectiveZoneId]);

  // ----------------------------------------------------
  // Chart 1: 30-Day Historical Rainfall (Actual vs Baseline)
  // ----------------------------------------------------
  const historyLabels = historyData.map((pt) => {
    const d = new Date(pt.timestamp);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  });

  const historyChartData: ChartData<'line'> = {
    labels: historyLabels,
    datasets: [
      {
        label: 'Actual Rain (mm)',
        data: historyData.map((pt) => pt.actual_rain_mm),
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.12)',
        borderWidth: 2.5,
        fill: true,
        tension: 0.35,
        pointRadius: 2.5,
        pointBackgroundColor: '#2563eb',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 1.5,
        pointHoverRadius: 6,
        yAxisID: 'y',
      },
      {
        label: 'Daily Baseline (mm)',
        data: historyData.map((pt) => pt.daily_baseline_mm),
        borderColor: '#ea580c',
        backgroundColor: 'transparent',
        borderWidth: 2,
        borderDash: [5, 4],
        fill: false,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 4,
        yAxisID: 'y',
      },
    ],
  };

  const historyOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#334155',
          boxWidth: 12,
          font: {
            size: 11,
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
            weight: 500,
          },
          usePointStyle: true,
        },
      },
      title: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.92)',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        padding: 10,
        callbacks: {
          label: (context) => {
            const val = context.parsed.y;
            if (val === null || val === undefined) return '';
            const pt = historyData[context.dataIndex];
            if (context.datasetIndex === 0) {
              const baseline = pt ? pt.daily_baseline_mm : 0;
              const ratio = baseline > 0 ? (val / baseline).toFixed(1) : '1.0';
              return `Actual: ${val.toFixed(2)} mm (${ratio}x baseline)`;
            }
            return `Baseline: ${val.toFixed(2)} mm`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(226, 232, 240, 0.6)',
        },
        ticks: {
          color: '#64748b',
          maxTicksLimit: 8,
          font: {
            size: 10,
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
          },
        },
      },
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        title: {
          display: true,
          text: 'Rainfall (mm)',
          color: '#2563eb',
          font: {
            size: 11,
            weight: 'bold',
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
          },
        },
        beginAtZero: true,
        grid: {
          color: 'rgba(226, 232, 240, 0.6)',
        },
        ticks: {
          color: '#64748b',
          font: {
            size: 10,
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
          },
          callback: (value) => `${value} mm`,
        },
      },
    },
  };

  // ----------------------------------------------------
  // Chart 2: 24h Risk Probability Trend (Fallback / Tab 2)
  // ----------------------------------------------------
  const sortedTrend = [...data].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  const trendChartData: ChartData<'line'> = {
    labels: sortedTrend.map((point) => {
      const date = new Date(point.timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }),
    datasets: [
      {
        label: 'Risk Probability (%)',
        data: sortedTrend.map((point) => point.probability * 100),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2.5,
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#3b82f6',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 1.5,
        pointHoverRadius: 6,
        yAxisID: 'y',
      },
    ],
  };

  const trendOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#334155',
          boxWidth: 12,
          font: {
            size: 11,
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
          },
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.92)',
        callbacks: {
          label: (context) => {
            const val = context.parsed.y;
            return `Risk Probability: ${val?.toFixed(1)}%`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(226, 232, 240, 0.6)' },
        ticks: { color: '#64748b', font: { size: 10 } },
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: 'rgba(226, 232, 240, 0.6)' },
        ticks: {
          color: '#64748b',
          callback: (value) => `${value}%`,
          font: { size: 10 },
        },
      },
    },
  };

  return (
    <div className="h-full w-full flex flex-col">
      {/* Top Header with Tab Switcher */}
      <div className="flex items-center justify-between pb-2 mb-1 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-700 truncate max-w-[140px] sm:max-w-none">
            {zoneName}
          </span>
          {activeTab === 'history' && historyData.length > 0 && (
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
              30-Day History
            </span>
          )}
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center gap-1 bg-slate-100/80 p-0.5 rounded-lg border border-slate-200/60">
          <button
            type="button"
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
              activeTab === 'history'
                ? 'bg-white text-blue-600 shadow-sm font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <CloudRain className="w-3 h-3" />
            <span>Rainfall History</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('trend')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
              activeTab === 'trend'
                ? 'bg-white text-blue-600 shadow-sm font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Activity className="w-3 h-3" />
            <span>Risk Trend</span>
          </button>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div className="flex-1 min-h-0 relative mt-1">
        {activeTab === 'history' ? (
          historyData.length > 0 ? (
            <Line data={historyChartData} options={historyOptions} />
          ) : loadingHistory ? (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-500 border-t-transparent mr-2"></div>
              Loading 30-day rainfall data...
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 text-xs p-4">
              <CloudRain className="w-8 h-8 text-slate-300 mb-2" />
              <p>No historical rainfall recorded for this zone yet</p>
            </div>
          )
        ) : (
          sortedTrend.length > 0 ? (
            <Line data={trendChartData} options={trendOptions} />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 text-xs p-4">
              <LineChart className="w-8 h-8 text-slate-300 mb-2" />
              <p>No 24h risk trend points recorded for this zone yet</p>
            </div>
          )
        )}
      </div>
    </div>
  );
};