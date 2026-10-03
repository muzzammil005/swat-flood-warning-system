'use client';

import { Line } from 'react-chartjs-2';
import { CloudRain } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  ChartData,
} from 'chart.js';
import { RainfallVsRiskPoint } from '@/shared/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface RainfallVsRiskChartProps {
  data: RainfallVsRiskPoint[];
  zoneName: string;
}

export const RainfallVsRiskChart: React.FC<RainfallVsRiskChartProps> = ({ data, zoneName }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full w-full bg-neutral-50/50 rounded-lg">
        <div className="text-center text-neutral-500">
          <div className="flex justify-center mb-2">
            <CloudRain className="w-10 h-10 text-neutral-400" />
          </div>
          <p>No rainfall vs risk data available</p>
          <p className="text-sm mt-1">Rainfall and risk correlation data will appear here</p>
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
        label: 'Rainfall (mm)',
        data: sortedData.map(point => point.rainfall_mm),
        borderColor: '#0ea5e9',
        backgroundColor: 'rgba(14, 165, 233, 0.1)',
        borderWidth: 2.5,
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#0ea5e9',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointHoverRadius: 7,
        yAxisID: 'y',
        type: 'line' as const,
      },
      {
        label: 'Risk Probability',
        data: sortedData.map(point => point.risk_probability * 100),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderWidth: 2.5,
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#ef4444',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointHoverRadius: 7,
        yAxisID: 'y1',
        type: 'line' as const,
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
        text: `Rainfall vs Risk: ${zoneName}`,
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
              return `Rainfall: ${value.toFixed(1)}mm`;
            } else {
              return `Risk: ${value.toFixed(1)}%`;
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
          text: 'Rainfall (mm)',
          color: '#0ea5e9',
          font: {
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
            weight: 'bold',
          },
        },
        grid: {
          color: 'rgba(229, 229, 229, 0.5)',
        },
        ticks: {
          color: '#737373',
          font: {
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
          },
          callback: (value) => `${value}mm`,
        },
        beginAtZero: true,
      },
      y1: {
        type: 'linear',
        display: true,
        position: 'right',
        title: {
          display: true,
          text: 'Risk Probability (%)',
          color: '#ef4444',
          font: {
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
            weight: 'bold',
          },
        },
        grid: {
          drawOnChartArea: false,
        },
        ticks: {
          color: '#737373',
          font: {
            family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
          },
          callback: (value) => `${value}%`,
        },
        min: 0,
        max: 100,
        beginAtZero: true,
      },
    },
  };

  return (
    <div className="h-full w-full relative">
      <Line data={chartData} options={options} />
    </div>
  );
};