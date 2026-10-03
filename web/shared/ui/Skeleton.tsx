import React from 'react';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => {
  return (
    <div className={`animate-pulse bg-neutral-200 rounded ${className}`} />
  );
};

export const CardSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-lg border border-neutral-200 shadow-sm p-6">
      <div className="space-y-3">
        <Skeleton className="h-4 w-1/4" />
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  );
};

export const BadgeSkeleton: React.FC = () => {
  return (
    <Skeleton className="h-6 w-20 rounded-full" />
  );
};