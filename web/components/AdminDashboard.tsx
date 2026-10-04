'use client';

import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { useRouter } from 'next/navigation';
import { apiClient, clearAdminToken, getAdminToken, type CommunityReportResponse, type UserRecord, type ZoneListResponse, type AdminOverrideResponse, type RiskTier } from '@/shared/api';
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '@/shared/ui';

export function AdminDashboard() {
  const router = useRouter();
  const [zones, setZones] = useState<ZoneListResponse[]>([]);
  const [pendingReports, setPendingReports] = useState<CommunityReportResponse[]>([]);
  const [resolvedReports, setResolvedReports] = useState<CommunityReportResponse[]>([]);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [overrides, setOverrides] = useState<AdminOverrideResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [overrideZoneId, setOverrideZoneId] = useState('');
  const [overrideLevel, setOverrideLevel] = useState<RiskTier>('HIGH');
  const [overrideReason, setOverrideReason] = useState('');
  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'admin' as 'admin' | 'responder' });
  const [status, setStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [resettingUser, setResettingUser] = useState<string | null>(null);
  const [resetPasswordValue, setResetPasswordValue] = useState('');
  
  const [broadcastZoneId, setBroadcastZoneId] = useState('');
  const [broadcastHeadline, setBroadcastHeadline] = useState('');
  const [broadcastDescription, setBroadcastDescription] = useState('');

  const handleResetPassword = async (userId: string) => {
    setPending(true);
    
    try {
      await apiClient.resetUserPassword(userId, resetPasswordValue);
      toast.success('Password reset successfully.');
      setResettingUser(null);
      setResetPasswordValue('');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to reset password.');
    } finally {
      setPending(false);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this operator?')) return;
    
    setPending(true);
    
    try {
      await apiClient.deleteUser(userId);
      toast.success('User deleted successfully.');
      await loadData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to delete user.');
    } finally {
      setPending(false);
    }
  };

  useEffect(() => {
    const token = getAdminToken();
    if (!token) {
      router.push('/admin/login');
      return;
    }

    void loadData();
  }, [router]);

  const loadData = async () => {
    try {
      const [zonesRes, reportsRes, usersRes, overridesRes] = await Promise.allSettled([
        apiClient.getZones(),
        apiClient.getReports(),
        apiClient.getUsers(),
        apiClient.getOverrides(),
      ]);

      if (zonesRes.status === 'fulfilled' && zonesRes.value) {
        const rawZones = zonesRes.value;
        const validZones: ZoneListResponse[] = Array.isArray(rawZones)
          ? rawZones
          : ((rawZones as any)?.zones ?? []);
        setZones(validZones);
        if (validZones.length > 0) {
          const firstZoneId = (validZones[0] as any).zone_id || validZones[0].id;
          setOverrideZoneId((prev) => prev || firstZoneId);
          setBroadcastZoneId((prev) => prev || firstZoneId);
        }
      } else if (zonesRes.status === 'rejected') {
        console.error('Failed to load zones:', zonesRes.reason);
      }

      if (reportsRes.status === 'fulfilled' && reportsRes.value) {
        const allReports = reportsRes.value.reports ?? [];
        setPendingReports(allReports.filter((r) => r.status.toLowerCase() === 'pending'));
        setResolvedReports(allReports.filter((r) => r.status.toLowerCase() !== 'pending'));
      }

      if (usersRes.status === 'fulfilled' && usersRes.value) {
        setUsers(Array.isArray(usersRes.value) ? usersRes.value : []);
      }

      if (overridesRes.status === 'fulfilled' && overridesRes.value) {
        setOverrides(Array.isArray(overridesRes.value) ? overridesRes.value : []);
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to load admin data.');
    } finally {
      setLoading(false);
    }
  };

  const handleOverrideSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setPending(true);
    

    try {
      await apiClient.createManualOverride({
        zone_id: overrideZoneId,
        threat_level: overrideLevel,
        reason: overrideReason,
      });

      toast.success('Manual override created successfully.');
      setOverrideReason('');
      await loadData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to create override.');
    } finally {
      setPending(false);
    }
  };

  const handleBroadcastSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setPending(true);
    

    try {
      await apiClient.broadcastAlert({
        zone_id: broadcastZoneId,
        severity: 'HIGH',
        headline: broadcastHeadline,
        description: broadcastDescription,
      });

      toast.success('Emergency Alert Broadcasted Successfully.');
      setBroadcastHeadline('');
      setBroadcastDescription('');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to broadcast alert.');
    } finally {
      setPending(false);
    }
  };

  const handleReportAction = async (reportId: string, action: 'Approved' | 'Rejected') => {
    try {
      const updatedReport = await apiClient.updateReportStatus(reportId, action);
      setPendingReports((current) => current.filter((report) => report.id !== reportId));
      setResolvedReports((current) => [updatedReport, ...current]);
      toast.success(`Report ${action.toLowerCase()} successfully.`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to update report status.');
    }
  };

  const handleCreateUser = async (event: React.FormEvent) => {
    event.preventDefault();
    setPending(true);
    

    try {
      await apiClient.createUser({
        username: newUser.username,
        password: newUser.password,
        role: newUser.role,
      });

      toast.success(`User ${newUser.username} created successfully.`);
      setNewUser({ username: '', password: '', role: 'admin' });
      await loadData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to create user.');
    } finally {
      setPending(false);
    }
  };

  const metricCards = useMemo(
    () => [
      { label: 'Pending reports', value: pendingReports.length },
      { label: 'Total zones', value: zones.length },
      { label: 'Operators', value: users.length },
      { label: 'Active overrides', value: overrides.filter((o) => o.is_active).length },
    ],
    [pendingReports.length, users.length, zones.length, overrides]
  );

  const handleLogout = () => {
    clearAdminToken();
    router.push('/admin/login');
  };

  if (loading) {
    return <div className="rounded-xl border border-neutral-200 bg-white p-8 text-neutral-500">Loading admin dashboard…</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-neutral-500">Operations</p>
          <h1 className="text-3xl font-bold text-neutral-900">Admin control center</h1>
        </div>
        <Button variant="outline" onClick={handleLogout}>Logout</Button>
      </div>

      

      <div className="grid gap-4 md:grid-cols-4">
        {metricCards.map((item) => (
          <Card key={item.label}>
            <CardContent className="space-y-2">
              <p className="text-sm text-neutral-500">{item.label}</p>
              <p className="text-3xl font-bold text-neutral-900">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Active overrides viewer — AD2 endpoint consumer (G4 fix) */}
      <Card>
        <CardHeader>
          <CardTitle>Active and recent manual overrides</CardTitle>
        </CardHeader>
        <CardContent>
          {overrides.length === 0 ? (
            <div className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 p-6 text-center text-neutral-500">
              No overrides on record. Apply an override via the form on the left when a field reading disagrees with the model.
            </div>
          ) : (
            <div className="space-y-3">
              {overrides.map((ov) => (
                <div
                  key={ov.id}
                  className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <Badge tier={ov.threat_level}>{ov.threat_level}</Badge>
                      <h4 className="font-semibold text-neutral-900">{ov.zone_name}</h4>
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs text-neutral-500">
                      <span>
                        by <span className="font-medium text-neutral-700">{ov.created_by_username}</span>
                      </span>
                      <span>
                        created{' '}
                        <span className="font-medium text-neutral-700">
                          {new Date(ov.created_at).toLocaleString()}
                        </span>
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                          ov.is_active
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-neutral-100 text-neutral-600'
                        }`}
                      >
                        {ov.is_active ? 'IN EFFECT' : 'EXPIRED'}
                      </span>
                    </div>
                  </div>
                  <p className="mt-3 text-sm text-neutral-700">
                    <span className="font-medium text-neutral-900">Reason:</span> {ov.reason}
                  </p>
                  {ov.expires_at && (
                    <p className="mt-2 text-xs text-neutral-500">
                      Expires on {new Date(ov.expires_at).toLocaleString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Broadcast Emergency Alert</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleBroadcastSubmit}>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2 text-sm font-medium text-neutral-700">
                    Zone
                    <select value={broadcastZoneId} onChange={(e) => setBroadcastZoneId(e.target.value)} className="w-full rounded-lg border border-red-300 px-3 py-2 text-sm focus:border-red-500 focus:outline-none">
                      {zones && zones.length > 0 ? (
                        zones.map((zone) => {
                          const zoneId = zone.zone_id || zone.id;
                          const zoneName = zone.name || (zone as any).zone_name || zoneId;
                          return (
                            <option key={zoneId} value={zoneId}>
                              {zoneName}
                            </option>
                          );
                        })
                      ) : (
                        <option value="" disabled>Loading zones...</option>
                      )}
                    </select>
                  </label>
                  <label className="space-y-2 text-sm font-medium text-neutral-700">
                    Headline
                    <input
                      type="text"
                      value={broadcastHeadline}
                      onChange={(e) => setBroadcastHeadline(e.target.value)}
                      placeholder="e.g. EVACUATE IMMEDIATELY"
                      className="w-full rounded-lg border border-red-300 px-3 py-2 text-sm focus:border-red-500 focus:outline-none"
                    />
                  </label>
                </div>
                <label className="block space-y-2 text-sm font-medium text-neutral-700">
                  Description
                  <textarea
                    rows={2}
                    value={broadcastDescription}
                    onChange={(e) => setBroadcastDescription(e.target.value)}
                    placeholder="Provide evacuation instructions..."
                    className="w-full rounded-lg border border-red-300 px-3 py-2 text-sm focus:border-red-500 focus:outline-none"
                  />
                </label>
                <div className="flex justify-end">
                  <button 
                    type="submit" 
                    disabled={pending || !broadcastHeadline.trim() || !broadcastDescription.trim()}
                    className="px-6 py-2 rounded-lg font-medium text-sm bg-neutral-900 text-white hover:bg-neutral-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {pending ? 'Broadcasting...' : 'SOUND THE ALARM'}
                  </button>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Manual override</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleOverrideSubmit}>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm font-medium text-neutral-700">
                  Zone
                  <select value={overrideZoneId} onChange={(e) => setOverrideZoneId(e.target.value)} className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none">
                    {zones && zones.length > 0 ? (
                      zones.map((zone) => {
                        const zoneId = zone.zone_id || zone.id;
                        const zoneName = zone.name || (zone as any).zone_name || zoneId;
                        return (
                          <option key={zoneId} value={zoneId}>
                            {zoneName}
                          </option>
                        );
                      })
                    ) : (
                      <option value="" disabled>Loading zones...</option>
                    )}
                  </select>
                </label>

                <label className="space-y-2 text-sm font-medium text-neutral-700">
                  Threat level
                  <select value={overrideLevel} onChange={(e) => setOverrideLevel(e.target.value as RiskTier)} className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none">
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                  </select>
                </label>
              </div>

              <label className="block space-y-2 text-sm font-medium text-neutral-700">
                Reason
                <textarea
                  rows={4}
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Explain the operational reason for this override."
                  className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none"
                />
              </label>

              <div className="flex justify-end">
                <Button type="submit" disabled={pending || !overrideReason.trim()}>
                  {pending ? 'Saving...' : 'Apply override'}
                </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Create operator</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleCreateUser} autoComplete="off">
              <label className="block space-y-2 text-sm font-medium text-neutral-700">
                Username
                <input type="text" autoComplete="new-password" value={newUser.username} onChange={(e) => setNewUser((prev) => ({ ...prev, username: e.target.value }))} className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none" placeholder="operator_name" />
              </label>

              <label className="block space-y-2 text-sm font-medium text-neutral-700">
                Password
                <input type="password" autoComplete="new-password" value={newUser.password} onChange={(e) => setNewUser((prev) => ({ ...prev, password: e.target.value }))} className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none" placeholder="••••••••" />
              </label>

              <label className="block space-y-2 text-sm font-medium text-neutral-700">
                Role
                <select value={newUser.role} onChange={(e) => setNewUser((prev) => ({ ...prev, role: e.target.value as 'admin' | 'responder' }))} className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none">
                  <option value="admin">Admin</option>
                </select>
              </label>

              <div className="flex justify-end">
                <Button type="submit" variant="secondary" disabled={pending || !newUser.username || !newUser.password}>
                  {pending ? 'Creating...' : 'Create user'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>System Operators</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-lg border border-neutral-200">
            <table className="w-full text-left text-sm text-neutral-600">
              <thead className="border-b border-neutral-200 bg-neutral-50 text-xs uppercase text-neutral-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Username</th>
                  <th className="px-4 py-3 font-medium">Role</th>
                  <th className="px-4 py-3 font-medium">Created At</th>
                  <th className="px-4 py-3 text-right font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {users.map((user) => (
                  <tr key={user.id} className="bg-white hover:bg-neutral-50">
                    <td className="px-4 py-3 font-medium text-neutral-900">{user.username}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${user.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">{new Date(user.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right">
                      {resettingUser === user.id ? (
                        <div className="flex items-center justify-end gap-2">
                          <input
                            type="text"
                            placeholder="New password"
                            value={resetPasswordValue}
                            onChange={(e) => setResetPasswordValue(e.target.value)}
                            className="w-32 rounded border border-neutral-300 px-2 py-1 text-xs focus:border-neutral-500 focus:outline-none"
                          />
                          <Button size="sm" onClick={() => handleResetPassword(user.id)} disabled={pending || !resetPasswordValue}>
                            Save
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => { setResettingUser(null); setResetPasswordValue(''); }}>
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-2">
                          <Button size="sm" variant="outline" onClick={() => setResettingUser(user.id)}>
                            Reset Password
                          </Button>
                          <button
                            type="button"
                            onClick={() => handleDeleteUser(user.id)}
                            className="p-1.5 text-neutral-400 hover:text-red-600 rounded-md hover:bg-red-50 transition-colors"
                            title="Delete user"
                            disabled={pending || user.username === 'admin'}
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M3 6h18" />
                              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                            </svg>
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pending community reports</CardTitle>
        </CardHeader>
        <CardContent>
          {pendingReports.length === 0 ? (
            <div className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 p-6 text-center text-neutral-500">
              No pending community reports.
            </div>
          ) : (
            <div className="space-y-3">
              {pendingReports.map((report) => (
                <div key={report.id} className="rounded-lg border border-neutral-200 p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="mb-2 flex items-center gap-2">
                        <strong className="text-neutral-900">{report.report_type}</strong>
                        <Badge tier="MEDIUM" className="px-2 py-0.5 text-[10px]">{report.status}</Badge>
                      </div>
                      <p className="text-sm text-neutral-600">{report.description}</p>
                      {(report.reporter_name || report.reporter_phone) && (
                        <p className="mt-2 text-xs font-medium text-neutral-700">
                          Reported by: {report.reporter_name || 'Anonymous'} {report.reporter_phone ? `(${report.reporter_phone})` : ''}
                        </p>
                      )}
                      <p className="mt-2 text-xs text-neutral-500">Zone: {report.zone_id} • Submitted: {new Date(report.submitted_at).toLocaleString()}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button type="button" size="sm" variant="primary" onClick={() => handleReportAction(report.id, 'Approved')}>
                        Approve
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => handleReportAction(report.id, 'Rejected')}>
                        Reject
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Resolved community reports</CardTitle>
        </CardHeader>
        <CardContent>
          {resolvedReports.length === 0 ? (
            <div className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 p-6 text-center text-neutral-500">
              No resolved community reports yet.
            </div>
          ) : (
            <div className="space-y-3">
              {resolvedReports.map((report) => (
                <div key={report.id} className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 opacity-75">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <div className="mb-2 flex items-center gap-2">
                        <strong className="text-neutral-900">{report.report_type}</strong>
                        <Badge tier={report.status.toLowerCase() === 'approved' ? 'LOW' : 'HIGH'} className="px-2 py-0.5 text-[10px]">{report.status}</Badge>
                      </div>
                      <p className="text-sm text-neutral-600">{report.description}</p>
                      {(report.reporter_name || report.reporter_phone) && (
                        <p className="mt-2 text-xs font-medium text-neutral-700">
                          Reported by: {report.reporter_name || 'Anonymous'} {report.reporter_phone ? `(${report.reporter_phone})` : ''}
                        </p>
                      )}
                      <p className="mt-2 text-xs text-neutral-500">Zone: {report.zone_id} • Submitted: {new Date(report.submitted_at).toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
