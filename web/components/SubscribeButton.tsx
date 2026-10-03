'use client';

import React, { useState, useEffect } from 'react';

export function SubscribeCard() {
  const [isSubscribed, setIsSubscribed] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('alerts_subscribed');
    if (saved === 'true') {
      setIsSubscribed(true);
    }
  }, []);

  return (
    <div className="bg-white rounded-2xl p-4 shadow-sm border border-neutral-200 flex items-center gap-4">
      <div className="flex-shrink-0 bg-red-100 p-3 rounded-full">
        <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
      </div>
      <div className="flex-1">
        <h3 className="font-bold text-neutral-900">Emergency Alerts</h3>
        <p className="text-sm text-neutral-500">Get instantly notified of dangerous floods</p>
      </div>
      <button 
        onClick={() => {
          const next = !isSubscribed;
          setIsSubscribed(next);
          localStorage.setItem('alerts_subscribed', next ? 'true' : 'false');
          if (next) alert('Subscribed to Emergency Alerts!');
        }}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 ${isSubscribed ? 'bg-red-600' : 'bg-neutral-200'}`}
        role="switch"
        aria-checked={isSubscribed}
      >
        <span
          aria-hidden="true"
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${isSubscribed ? 'translate-x-5' : 'translate-x-0'}`}
        />
      </button>
    </div>
  );
}
