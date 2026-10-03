'use client';

import { useMemo, useState } from 'react';
import { apiClient, type ZoneListResponse } from '@/shared/api';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/shared/ui';

interface ReportIssueFormProps {
  zones: ZoneListResponse[];
}

export function ReportIssueForm({ zones }: ReportIssueFormProps) {
  const [reportType, setReportType] = useState('Flooding');
  const [description, setDescription] = useState('');
  const [reporterName, setReporterName] = useState('');
  const [reporterPhone, setReporterPhone] = useState('');
  const [selectedZoneId, setSelectedZoneId] = useState(zones[0]?.id ?? '');
  const [locationMode, setLocationMode] = useState<'zone' | 'current'>('zone');
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const zoneOptions = useMemo(() => zones, [zones]);

  const handleUseMyLocation = async () => {
    if (!navigator.geolocation) {
      setStatus({ type: 'error', message: 'This browser does not support geolocation.' });
      return;
    }

    setStatus(null);
    setSubmitting(true);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const nearest = await apiClient.getNearestZones(position.coords.latitude, position.coords.longitude, 1);
          const zone = nearest[0];
          if (zone) {
            setSelectedZoneId(zone.id);
            setLocationMode('current');
            setStatus({ type: 'success', message: `Location detected near ${zone.name}.` });
          }
        } catch (error) {
          setStatus({
            type: 'error',
            message: error instanceof Error ? error.message : 'Unable to determine the nearest zone.',
          });
        } finally {
          setSubmitting(false);
        }
      },
      () => {
        setStatus({ type: 'error', message: 'Location permission was denied. Please choose a zone manually.' });
        setSubmitting(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus(null);

    if (!description.trim()) {
      setStatus({ type: 'error', message: 'Please add a short description of the issue.' });
      return;
    }

    if (!selectedZoneId) {
      setStatus({ type: 'error', message: 'Select a zone or use your current location.' });
      return;
    }

    setSubmitting(true);

    try {
      const payload = {
        report_type: reportType,
        description: description.trim(),
        reporter_name: reporterName || undefined,
        reporter_phone: reporterPhone || undefined,
        zone_id: selectedZoneId,
      };

      await apiClient.createReport(payload);
      setStatus({ type: 'success', message: 'Report submitted successfully. It is now pending review.' });
      setDescription('');
      setReporterName('');
      setReporterPhone('');
    } catch (error) {
      setStatus({
        type: 'error',
        message: error instanceof Error ? error.message : 'Unable to submit the report right now.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Report an Issue</CardTitle>
          <div className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">Community alert</div>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm font-medium text-neutral-700">
              Report type
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-neutral-500 focus:outline-none"
              >
                <option>Flooding</option>
                <option>Blocked drainage</option>
                <option>Road hazard</option>
                <option>Evacuation need</option>
                <option>Water level concern</option>
                <option>Other</option>
              </select>
            </label>

            <label className="space-y-2 text-sm font-medium text-neutral-700">
              Zone
              <select
                value={selectedZoneId}
                onChange={(e) => {
                  setSelectedZoneId(e.target.value);
                  setLocationMode('zone');
                }}
                className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-neutral-500 focus:outline-none"
              >
                {zoneOptions.map((zone) => (
                  <option key={zone.id} value={zone.id}>{zone.name}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" variant={locationMode === 'zone' ? 'primary' : 'outline'} size="sm" onClick={() => setLocationMode('zone')}>
              Use zone
            </Button>
            <Button type="button" variant={locationMode === 'current' ? 'primary' : 'outline'} size="sm" onClick={handleUseMyLocation} disabled={submitting}>
              Use my location
            </Button>
          </div>

          <label className="block space-y-2 text-sm font-medium text-neutral-700">
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              placeholder="Describe the condition, urgency, and any nearby landmarks."
              className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-neutral-500 focus:outline-none"
            />
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm font-medium text-neutral-700">
              Contact name (optional)
              <input
                value={reporterName}
                onChange={(e) => setReporterName(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-neutral-500 focus:outline-none"
                placeholder="Your name"
              />
            </label>

            <label className="space-y-2 text-sm font-medium text-neutral-700">
              Phone (optional)
              <input
                value={reporterPhone}
                onChange={(e) => setReporterPhone(e.target.value)}
                className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:border-neutral-500 focus:outline-none"
                placeholder="+92 ..."
              />
            </label>
          </div>

          {status && (
            <div
              className={`rounded-lg border px-3 py-2 text-sm ${
                status.type === 'success'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                  : 'border-red-200 bg-red-50 text-red-700'
              }`}
            >
              {status.message}
            </div>
          )}

          <div className="flex items-center justify-between gap-4 pt-1">
            <p className="text-xs text-neutral-500">
              Reports are submitted to the emergency review queue and marked as pending until approved.
            </p>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit report'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
