// API client for the flood monitoring backend

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH' | 'DANGER' | 'SAFE';

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface WaterLevel {
  metres: number;
}

export interface ZoneThresholds {
  water_warning_level: WaterLevel;
  water_critical_level: WaterLevel;
  heavy_rain_threshold_mm: number;
}

export interface RiskAssessment {
  id?: string;
  zone_id: string;
  tier: RiskTier;
  probability: number;
  explanation: string;
  computed_at: string;
  combined_rain_mm?: number | null;
  expected_rain_mm?: number | null;
  rainfall_anomaly_ratio?: number | null;
  top_contributing_features?: string[] | null;
}

export interface SensorReading {
  id: string;
  zone_id: string;
  water_level: WaterLevel;
  source: string;
  timestamp: string;
}

export interface RainfallWindow {
  millimetres: number;
  duration_hours: number;
}

export interface WeatherSnapshot {
  zone_id: string;
  rainfall: RainfallWindow;
  fetched_at: string;
  ttl_seconds: number;
}

export interface ZoneSummaryResponse {
  danger: number;
  high: number;
  medium: number;
  low: number;
  safe: number;
  total_zones: number;
}

export interface ZoneListResponse {
  id: string;
  name: string;
  coordinates: Coordinates;
  upstream_zone_id?: string;
  latest_assessment?: RiskAssessment;
  thresholds?: ZoneThresholds;
  sensor_health?: 'online' | 'offline';
  is_manual_override?: boolean;
}

export interface ZoneDetailResponse {
  zone: ZoneListResponse;
  recent_readings: SensorReading[];
  risk_history: RiskAssessment[];
  recent_rainfall?: WeatherSnapshot;
  latest_sensor_reading?: SensorReading;
  is_manual_override?: boolean;
}

export interface RiskTrendPoint {
  timestamp: string;
  tier: RiskTier;
  probability: number;
}

export interface RainfallVsRiskPoint {
  timestamp: string;
  rainfall_mm: number;
  risk_probability: number;
}

export interface ResourceCenterItem {
  id: string;
  item_name: string;
  quantity: number;
}

export interface ResourceCenter {
  id: string;
  name: string;
  location_zone: string;
  inventory: ResourceCenterItem[];
}

export interface CommunityReportCreateRequest {
  report_type: string;
  description: string;
  reporter_name?: string;
  reporter_phone?: string;
  zone_id?: string;
  latitude?: number;
  longitude?: number;
}

export interface CommunityReportResponse {
  id: string;
  zone_id: string;
  report_type: string;
  description: string;
  reporter_name?: string | null;
  reporter_phone?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  submitted_at: string;
  status: string;
  admin_notes?: string | null;
}

export interface ReportListResponse {
  reports: CommunityReportResponse[];
  reports_by_zone?: Record<string, CommunityReportResponse[]> | null;
}

export interface AdminOverrideRequest {
  zone_id: string;
  threat_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'DANGER';
  reason: string;
}

export interface UserRecord {
  id: string;
  username: string;
  role: 'admin' | 'responder';
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  role: string;
}

export interface AlertResponse {
  id: string;
  zone_id: string;
  zone_name: string;
  severity: RiskTier;
  certainty: 'Observed' | 'Likely' | 'Possible' | 'Unlikely' | 'Unknown';
  urgency: 'Immediate' | 'Expected' | 'Future' | 'Past' | 'Unknown';
  headline: string;
  description: string;
  instruction?: string | null;
  sent_at: string;
  expires_at?: string | null;
}

export interface AdminOverrideResponse {
  id: string;
  zone_id: string;
  zone_name: string;
  threat_level: RiskTier;
  reason: string;
  created_by_username: string;
  created_at: string;
  expires_at?: string | null;
  is_active: boolean;
}

const ADMIN_TOKEN_KEY = 'swat_flood_admin_token';

export const getAdminToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ADMIN_TOKEN_KEY);
};

export const setAdminToken = (token: string) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(ADMIN_TOKEN_KEY, token);
  }
};

export const clearAdminToken = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
  }
};

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private getAuthHeaders(): Record<string, string> {
    const token = getAdminToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const text = await response.text();
      let message = `API error: ${response.status} ${response.statusText}`;
      try {
        const parsed = JSON.parse(text);
        if (parsed?.detail) {
          message = parsed.detail;
        }
      } catch {
        if (text) message = text;
      }
      throw new Error(message);
    }

    const text = await response.text();
    if (!text) return undefined as T;
    return JSON.parse(text) as T;
  }

  async getZones(): Promise<ZoneListResponse[]> {
    return this.fetch('/zones/');
  }

  async getZoneSummary(): Promise<ZoneSummaryResponse> {
    return this.fetch('/zones/summary');
  }

  async getZoneDetail(zoneId: string): Promise<ZoneDetailResponse> {
    return this.fetch(`/zones/${zoneId}`);
  }

  async getZoneRiskTrend(zoneId: string, window: '24h' | '48h' = '24h'): Promise<RiskTrendPoint[]> {
    return this.fetch(`/zones/${zoneId}/risk-trend?window=${window}`);
  }

  async getZoneRainfallVsRisk(zoneId: string, window: '24h' | '48h' = '24h'): Promise<RainfallVsRiskPoint[]> {
    return this.fetch(`/zones/${zoneId}/rainfall-vs-risk?window=${window}`);
  }

  async getNearestZone(latitude: number, longitude: number): Promise<{ zone_id: string; zone_name: string; coordinates: { latitude: number; longitude: number }; distance_meters: number; zone_details: { name: string; coordinates: { latitude: number; longitude: number }; upstream_zone_id?: string | null } }> {
    return this.fetch(`/zones/nearest?lat=${latitude}&lon=${longitude}`);
  }

  async getNearestZones(latitude: number, longitude: number, limit: number = 1): Promise<Array<{ id: string; name: string; coordinates: { latitude: number; longitude: number }; upstream_zone_id?: string | null }>> {
    const nearest = await this.getNearestZone(latitude, longitude);
    return [
      {
        id: nearest.zone_id,
        name: nearest.zone_name,
        coordinates: nearest.coordinates,
        upstream_zone_id: nearest.zone_details?.upstream_zone_id ?? undefined,
      },
    ].slice(0, limit);
  }

  async getResourceCenters(): Promise<ResourceCenter[]> {
    return this.fetch('/resource-centers');
  }

  async createReport(payload: CommunityReportCreateRequest): Promise<CommunityReportResponse> {
    return this.fetch('/reports', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getReports(status?: 'pending' | 'approved'): Promise<ReportListResponse> {
    const query = status ? `?status=${status}` : '';
    return this.fetch(`/reports${query}`);
  }

  async updateReportStatus(reportId: string, status: 'Approved' | 'Rejected'): Promise<CommunityReportResponse> {
    return this.fetch(`/reports/${reportId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  async login(username: string, password: string): Promise<LoginResponse> {
    return this.fetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async getAlerts(): Promise<AlertResponse[]> {
    return this.fetch('/alerts');
  }

  async broadcastAlert(payload: { zone_id: string; severity?: string; headline: string; description: string }): Promise<any> {
    return this.fetch('/alerts/broadcast', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async createManualOverride(payload: AdminOverrideRequest): Promise<any> {
    return this.fetch('/admin/overrides', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getOverrides(zoneId?: string): Promise<AdminOverrideResponse[]> {
    const query = zoneId ? `?zone_id=${encodeURIComponent(zoneId)}` : '';
    return this.fetch(`/admin/overrides${query}`);
  }

  async getUsers(): Promise<UserRecord[]> {
    return this.fetch('/admin/users');
  }

  async createUser(payload: { username: string; password: string; role: 'admin' | 'responder' }): Promise<any> {
    return this.fetch('/admin/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async resetUserPassword(userId: string, newPassword: string): Promise<any> {
    return this.fetch(`/admin/users/${userId}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ new_password: newPassword }),
    });
  }

  async deleteUser(userId: string): Promise<any> {
    return this.fetch(`/admin/users/${userId}`, {
      method: 'DELETE',
    });
  }
}

export const apiClient = new ApiClient();