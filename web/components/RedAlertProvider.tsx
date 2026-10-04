'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { apiClient } from '@/shared/api';

// How long (in milliseconds) an alert is considered "active" since it was sent.
// After this window, it will no longer be shown even if not dismissed.
const ALERT_TTL_MS = 60 * 60 * 1000; // 1 hour

const DISMISSED_ALERTS_KEY = 'swat_flood_dismissed_alerts';
const MAX_STORED_DISMISSALS = 50; // prevent unbounded growth

function getDismissedAlerts(): Set<string> {
  if (typeof window === 'undefined') return new Set();
  try {
    const raw = localStorage.getItem(DISMISSED_ALERTS_KEY);
    const arr: string[] = raw ? JSON.parse(raw) : [];
    return new Set(arr);
  } catch {
    return new Set();
  }
}

function markAlertDismissed(alertId: string) {
  if (typeof window === 'undefined') return;
  try {
    const existing = getDismissedAlerts();
    existing.add(alertId);
    // Trim to cap. Convert to array to slice.
    const arr = Array.from(existing).slice(-MAX_STORED_DISMISSALS);
    localStorage.setItem(DISMISSED_ALERTS_KEY, JSON.stringify(arr));
  } catch {
    // ignore storage errors
  }
}

export function RedAlertProvider({ children }: { children: React.ReactNode }) {
  const [activeAlert, setActiveAlert] = useState<any | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const oscillatorRef = useRef<OscillatorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  // Track which alert id is currently shown so polling doesn't re-trigger while visible
  const shownAlertIdRef = useRef<string | null>(null);

  useEffect(() => {
    const pollAlerts = async () => {
      try {
        const alerts = await apiClient.getAlerts();
        if (!alerts || alerts.length === 0) return;

        const now = Date.now();
        const sorted = [...alerts].sort(
          (a, b) => new Date(b.sent_at).getTime() - new Date(a.sent_at).getTime()
        );
        const newest = sorted[0];

        // 1. Check TTL — if the alert is older than 1 hour, skip it entirely.
        const alertAge = now - new Date(newest.sent_at).getTime();
        if (alertAge > ALERT_TTL_MS) return;

        // 2. Skip if this alert is already being shown.
        if (shownAlertIdRef.current === newest.id) return;

        // 3. Skip if user has already dismissed this specific alert.
        const dismissed = getDismissedAlerts();
        if (dismissed.has(newest.id)) return;

        // 4. Trigger for HIGH/DANGER/EXTREME severity.
        const severity = newest.severity?.toUpperCase();
        if (severity !== 'HIGH' && severity !== 'DANGER' && severity !== 'EXTREME') return;

        // 5. Check subscription preference.
        const isSubscribed = localStorage.getItem('alerts_subscribed') === 'true';
        if (!isSubscribed) return;

        // All checks passed — show the alert.
        shownAlertIdRef.current = newest.id;
        setActiveAlert(newest);
        startSiren();
      } catch (err) {
        console.error('Failed to poll alerts', err);
      }
    };

    const timerId = setInterval(pollAlerts, 10000);
    pollAlerts();
    return () => clearInterval(timerId);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startSiren = useCallback(() => {
    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') ctx.resume();

      if (oscillatorRef.current) {
        oscillatorRef.current.stop();
        oscillatorRef.current.disconnect();
      }
      if (gainNodeRef.current) gainNodeRef.current.disconnect();

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'square';
      osc.frequency.setValueAtTime(600, ctx.currentTime);
      gain.gain.setValueAtTime(0, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(1, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(1, ctx.currentTime + 0.4);
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.5);

      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = setInterval(() => {
        if (ctx.state === 'running') {
          osc.frequency.setValueAtTime(800, ctx.currentTime);
          gain.gain.setValueAtTime(1, ctx.currentTime);
          gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.4);
          setTimeout(() => {
            osc.frequency.setValueAtTime(600, ctx.currentTime);
            gain.gain.setValueAtTime(1, ctx.currentTime);
            gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.4);
          }, 500);
        }
      }, 1000);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      oscillatorRef.current = osc;
      gainNodeRef.current = gain;
    } catch (e) {
      console.warn('Could not play audio', e);
    }
  }, []);

  const stopSiren = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (gainNodeRef.current && audioCtxRef.current) {
      gainNodeRef.current.gain.linearRampToValueAtTime(0, audioCtxRef.current.currentTime + 0.1);
    }
    setTimeout(() => {
      if (oscillatorRef.current) {
        try { oscillatorRef.current.stop(); } catch (e) {}
        oscillatorRef.current.disconnect();
        oscillatorRef.current = null;
      }
    }, 200);
  }, []);

  const handleDismiss = useCallback(() => {
    stopSiren();
    if (activeAlert?.id) {
      markAlertDismissed(activeAlert.id);
    }
    shownAlertIdRef.current = null;
    setActiveAlert(null);
  }, [stopSiren, activeAlert]);

  return (
    <>
      {children}
      {activeAlert && (
        <div className="fixed inset-0 z-[9999] bg-neutral-950/90 flex flex-col items-center justify-center p-6 animate-[pulse_1000ms_ease-in-out_infinite] backdrop-blur-md">
          <div className="max-w-xl w-full bg-neutral-900 border border-red-500/40 rounded-3xl p-8 md:p-10 text-center shadow-[0_0_100px_rgba(239,68,68,0.2)]">
            
            <div className="flex justify-center mb-6">
              <div className="bg-red-500/10 p-4 rounded-full">
                <svg className="w-16 h-16 text-red-500 animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
            </div>
            
            <h1 className="text-3xl md:text-5xl font-black text-white uppercase tracking-wide mb-6">
              CRITICAL EMERGENCY
            </h1>
            
            <div className="bg-neutral-950/50 rounded-2xl p-6 mb-8 border border-red-500/30 text-left relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-red-500"></div>
              <h2 className="text-xl md:text-2xl font-bold text-red-400 mb-3 pl-2">
                {activeAlert.headline}
              </h2>
              <p className="text-base text-neutral-300 leading-relaxed pl-2">
                {activeAlert.description}
              </p>
            </div>

            <button 
              onClick={handleDismiss}
              className="w-full py-4 px-6 bg-red-600 hover:bg-red-500 text-white text-lg font-bold rounded-xl transition-all transform active:scale-95 uppercase tracking-wide shadow-[0_4px_14px_0_rgba(239,68,68,0.39)]"
            >
              Acknowledge & Dismiss
            </button>
            <p className="mt-5 text-neutral-500 text-xs font-medium uppercase tracking-wider">
              By acknowledging this alert, you confirm receipt.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
