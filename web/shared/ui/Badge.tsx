import React from 'react';

export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH' | 'DANGER' | 'SAFE';

interface BadgeProps {
  tier: RiskTier;
  children?: React.ReactNode;
  className?: string;
}

const tierColors: Record<RiskTier, string> = {
  LOW: 'bg-emerald-500/10 text-emerald-700 border border-emerald-200',
  MEDIUM: 'bg-amber-500/10 text-amber-700 border border-amber-200',
  HIGH: 'bg-orange-500/10 text-orange-700 border border-orange-200',
  DANGER: 'bg-red-500 text-white shadow-[0_0_15px_rgba(239,68,68,0.5)] border border-red-500',
  SAFE: 'bg-slate-500/10 text-slate-700 border border-slate-200',
};

const defaultLabels: Record<RiskTier, string> = {
  LOW: 'Low Risk',
  MEDIUM: 'Medium Risk',
  HIGH: 'High Risk',
  DANGER: 'Danger',
  SAFE: 'Safe',
};

export const Badge: React.FC<BadgeProps> = ({ tier, children, className = '' }) => {
  const label = children || defaultLabels[tier];
  
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${tierColors[tier]} ${className}`}>
      {label}
    </span>
  );
};