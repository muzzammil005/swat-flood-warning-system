'use client';

import { useState, useEffect } from 'react';
import { apiClient, type ZoneListResponse } from '@/shared/api';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/shared/ui';

interface SubmitReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  zones: ZoneListResponse[];
  selectedZoneId: string | null;
}

export function SubmitReportModal({ isOpen, onClose, zones, selectedZoneId }: SubmitReportModalProps) {
  const [reportType, setReportType] = useState('flooding');
  const [description, setDescription] = useState('');
  const [reporterName, setReporterName] = useState('');
  const [reporterPhone, setReporterPhone] = useState('');
  const [zoneId, setZoneId] = useState(selectedZoneId || (zones[0]?.id ?? ''));
  const [status, setStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setReportType('flooding');
      setDescription('');
      setReporterName('');
      setReporterPhone('');
      setZoneId(selectedZoneId || (zones[0]?.id ?? ''));
      setStatus(null);
    }
  }, [isOpen, selectedZoneId, zones]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPending(true);
    setStatus(null);

    try {
      let lat: number | undefined;
      let lng: number | undefined;

      if (!zoneId) {
        // Fetch GPS location
        const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
          if (!navigator.geolocation) {
            reject(new Error('Geolocation is not supported by your browser.'));
          } else {
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 10000 });
          }
        });
        lat = pos.coords.latitude;
        lng = pos.coords.longitude;
      }

      await apiClient.createReport({
        report_type: reportType,
        description,
        reporter_name: reporterName,
        reporter_phone: reporterPhone,
        zone_id: zoneId || undefined,
        latitude: lat,
        longitude: lng,
      });
      setStatus({ type: 'success', message: 'Report submitted successfully. Thank you!' });
      
      // Auto close after 2 seconds on success
      setTimeout(() => {
        onClose();
        setStatus(null);
        setDescription('');
      }, 2000);
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Unable to submit report.';
      setStatus({
        type: 'error',
        message: msg === 'User denied Geolocation' 
          ? 'Please allow location access, or manually select a zone.' 
          : msg,
      });
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Report an Incident</CardTitle>
            <button onClick={onClose} className="text-neutral-500 hover:text-neutral-900">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </CardHeader>
          <CardContent>
            {status && (
              <div className={`mb-4 rounded-lg border px-3 py-2 text-sm ${status.type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-700'}`}>
                {status.message}
              </div>
            )}
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block space-y-2 text-sm font-medium text-neutral-700">
                  Incident Type
                  <select value={reportType} onChange={(e) => setReportType(e.target.value)} className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none">
                    <option value="flooding">Flooding</option>
                    <option value="blocked_drain">Blocked Drain</option>
                    <option value="high_river_level">High River Level</option>
                    <option value="landslide">Landslide / Debris</option>
                    <option value="other">Other</option>
                  </select>
                </label>

                <label className="block space-y-2 text-sm font-medium text-neutral-700">
                  Location (Zone)
                  <select value={zoneId} onChange={(e) => setZoneId(e.target.value)} className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none">
                    <option value="">Use My GPS Location</option>
                    {zones.map((zone) => (
                      <option key={zone.id} value={zone.id}>{zone.name}</option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="block space-y-2 text-sm font-medium text-neutral-700">
                Description
                <textarea
                  required
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the situation in detail..."
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none"
                />
              </label>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="block space-y-2 text-sm font-medium text-neutral-700">
                  Your Name (Optional)
                  <input type="text" autoComplete="off" value={reporterName} onChange={(e) => setReporterName(e.target.value)} className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none" />
                </label>

                <label className="block space-y-2 text-sm font-medium text-neutral-700">
                  Phone (Optional)
                  <input type="tel" autoComplete="off" value={reporterPhone} onChange={(e) => setReporterPhone(e.target.value)} className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none" />
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={pending || !description.trim()}>
                  {pending ? 'Submitting...' : 'Submit Report'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
