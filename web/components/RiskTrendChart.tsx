'use client';

import { Line } from 'react-chartjs-2';
import { LineChart } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  ChartData,
} from 'chart.js';
import { RiskTrendPoint, RiskTier } from '@/shared/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface RiskTrendChartProps {
  data: RiskTrendPoint[];
  zoneName: string;
}

const tierColors: Record<RiskTier, string> = {
  DANGER: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#f59e0b',
  LOW: '#10b981',
  SAFE: '#a3a3a3',
};

export const RiskTrendChart: React.FC<RiskTrendChartProps> = ({ data, zoneName }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full w-full bg-neutral-50/50 rounded-lg">
        <div className="text-center text-neutral-500">
          <div className="flex justify-center mb-2">
            <LineChart className="w-10 h-10 text-neutral-400" />
          </div>
          <p>No risk trend data available</p>
          <p className="text-sm mt-1">Risk assessments will appear here as they're generated</p>
        </div>
      </div>
    );
  }

  // Sort data by timestamp
  const sortedData = [...data].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  const chartData: ChartData<'line'> = {
    labels: sortedData.map(point => {
      const date = new Date(point.timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }),
    datasets: [
      {
        label: 'Risk Probability',
        data: sortedData.map(point => point.probability * 100),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#3b82f6',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointHoverRadius: 7,
        yAxisID: 'y',
      },
    ],
  };

  const options: ChartOptions<'line'> = {
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
          color: '#525252',
          font: {
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
          },
          usePointStyle: true,
        },
      },
      title: {
        display: true,
        text: `Risk Trend: ${zoneName}`,
        color: '#171717',
        font: {
          size: 16,
          family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
          weight: 'bold',
        },
        padding: {
          bottom: 20,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        titleColor: '#171717',
        bodyColor: '#525252',
        borderColor: '#e5e5e5',
        borderWidth: 1,
        padding: 12,
        usePointStyle: true,
        callbacks: {
          label: (context) => {
            const value = context.parsed.y;
            if (value === null || value === undefined) return '';
            
            if (context.datasetIndex === 0) {
              return `Probability: ${value.toFixed(1)}%`;
            } else {
              const point = sortedData[context.dataIndex];
              return `Risk Tier: ${point.tier}`;
            }
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(229, 229, 229, 0.5)',
        },
        ticks: {
          color: '#737373',
          font: {
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
          text: 'Probability (%)',
          color: '#3b82f6',
          font: {
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
            weight: 'bold',
          },
        },
        min: 0,
        max: 100,
        grid: {
          color: 'rgba(229, 229, 229, 0.5)',
        },
        ticks: {
          color: '#737373',
          font: {
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
          },
          callback: (value) => `${value}%`,
        },
      },
    },
  };

  return (
    <div className="h-full w-full relative">
      <Line data={chartData} options={options} />
    </div>
  );
};