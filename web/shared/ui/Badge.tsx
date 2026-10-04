import React from 'react';

export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH';

interface BadgeProps {
  tier: RiskTier;
  children?: React.ReactNode;
  className?: string;
}

const tierColors: Record<RiskTier, string> = {
  LOW: 'bg-emerald-500/10 text-emerald-700 border border-emerald-200',
  MEDIUM: 'bg-amber-500/10 text-amber-700 border border-amber-200',
  HIGH: 'bg-orange-500/10 text-orange-700 border border-orange-200',
};

const defaultLabels: Record<RiskTier, string> = {
  LOW: 'Low Risk',
  MEDIUM: 'Medium Risk',
  HIGH: 'High Risk',
};

export const Badge: React.FC<BadgeProps> = ({ tier, children, className = '' }) => {
  const normalizedTier = (tier?.toUpperCase() as RiskTier) in tierColors ? (tier.toUpperCase() as RiskTier) : 'LOW';
  const label = children || defaultLabels[normalizedTier] || defaultLabels.LOW;
  const colorClass = tierColors[normalizedTier] || tierColors.LOW;
  
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colorClass} ${className}`}>
      {label}
    </span>
  );
};