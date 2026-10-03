'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, LayersControl } from 'react-leaflet';
import { Icon, DivIcon, LatLng } from 'leaflet';
import { Map, LocateFixed } from 'lucide-react';
import { ZoneListResponse, RiskTier, apiClient } from '@/shared/api';
import { Button } from '@/shared/ui';

interface ZoneMapProps {
  zones: ZoneListResponse[];
  selectedZoneId: string | null;
  onZoneSelect: (zoneId: string | null) => void;
  onViewDetails?: (zoneId: string) => void;
}

// Ensure leaflet uses local marker images
const DefaultIcon = Icon.Default as any;
delete DefaultIcon.prototype._getIconUrl;

const markerIcon2x = 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png';
const markerIcon = 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png';
const markerShadow = 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png';

DefaultIcon.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

// Custom icons for different risk tiers - reuse colors from Badge component
const createRiskIcon = (tier: RiskTier): Icon => {
  // Direct color mapping - ensure these match Tailwind config
  let color: string;
  switch (tier) {
    case 'DANGER': color = '#ef4444'; break;    // risk-danger
    case 'HIGH': color = '#f97316'; break;      // risk-high
    case 'MEDIUM': color = '#f59e0b'; break;    // risk-medium
    case 'LOW': color = '#10b981'; break;       // risk-low
    case 'SAFE': color = '#a3a3a3'; break;      // neutral-400
    default:
      console.warn(`Unknown risk tier: ${tier}, defaulting to gray`);
      color = '#a3a3a3';
  }

  // Simple SVG with explicit fill
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="10" fill="${color}" stroke="white" stroke-width="2"/>
    </svg>
  `.trim().replace(/\s+/g, ' ');

  // Create data URL with proper encoding
  const encoded = encodeURIComponent(svg);
  const dataUrl = `data:image/svg+xml;charset=utf-8,${encoded}`;

  return new Icon({
    iconUrl: dataUrl,
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24],
    className: 'leaflet-risk-marker',
  });
};

// Center on Swat district (approximate center)
const SWAT_CENTER: [number, number] = [35.2, 72.4];
const DEFAULT_ZOOM = 10;

// Component to handle map view changes and resizing
function MapController({ selectedZone, zones }: { selectedZone: ZoneListResponse | null; zones: ZoneListResponse[] }) {
  const map = useMap();

  // Fix Leaflet tile sizing and container dimensions
  useEffect(() => {
    map.invalidateSize();
    const t1 = setTimeout(() => map.invalidateSize(), 150);
    const t2 = setTimeout(() => map.invalidateSize(), 500);

    const handleResize = () => map.invalidateSize();
    window.addEventListener('resize', handleResize);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener('resize', handleResize);
    };
  }, [map]);

  // Adjust view when a zone is selected
  useEffect(() => {
    if (selectedZone && selectedZone.coordinates) {
      map.setView(
        [selectedZone.coordinates.latitude, selectedZone.coordinates.longitude],
        13,
        { animate: true }
      );
    }
  }, [selectedZone, map]);

  return null;
}

// Component for location button and user marker
function LocationControls({ onZoneSelect }: { onZoneSelect: (zoneId: string) => void }) {
  const map = useMap();
  const [userLocation, setUserLocation] = useState<LatLng | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [isLocating, setIsLocating] = useState(false);

  const handleLocate = useCallback(async () => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser');
      return;
    }

    setIsLocating(true);
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        const userLatLng = new LatLng(latitude, longitude);

        setUserLocation(userLatLng);
        map.setView(userLatLng, 13, { animate: true });

        setIsLocating(false);

        // Find nearest zone
        try {
          const nearestZones = await apiClient.getNearestZones(latitude, longitude, 1);
          if (nearestZones.length > 0) {
            onZoneSelect(nearestZones[0].id);
          }
        } catch (err) {
          console.error('Failed to fetch nearest zone:', err);
        }
      },
      (error) => {
        setIsLocating(false);
        switch (error.code) {
          case error.PERMISSION_DENIED:
            setLocationError('Location permission denied. Please enable location services.');
            break;
          case error.POSITION_UNAVAILABLE:
            setLocationError('Location information unavailable.');
            break;
          case error.TIMEOUT:
            setLocationError('Location request timed out.');
            break;
          default:
            setLocationError('Unable to retrieve your location.');
        }

        // Clear error after 5 seconds
        setTimeout(() => setLocationError(null), 5000);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    );
  }, [map, onZoneSelect]);

  // Clear location marker when component unmounts or location changes
  useEffect(() => {
    return () => {
      setUserLocation(null);
    };
  }, []);

  // Create user location marker icon (different from risk markers)
  const userIcon = new DivIcon({
    html: `
      <div style="
        width: 24px;
        height: 24px;
        background: #3b82f6;
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="
          width: 8px;
          height: 8px;
          background: white;
          border-radius: 50%;
        "></div>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    className: 'user-location-marker',
  });

  return (
    <>
      {/* User location marker */}
      {userLocation && (
        <Marker position={userLocation} icon={userIcon}>
          <Popup>
            <div className="p-2">
              <h3 className="font-bold text-lg mb-2">Your Location</h3>
              <p className="text-sm text-neutral-600">
                {userLocation.lat.toFixed(4)}°N, {userLocation.lng.toFixed(4)}°E
              </p>
            </div>
          </Popup>
        </Marker>
      )}

      {/* Custom location control button */}
      <div className="leaflet-top leaflet-right">
        <div className="leaflet-control" style={{ marginTop: '16px', marginRight: '16px' }}>
          <button
            onClick={handleLocate}
            disabled={isLocating}
            className="flex items-center justify-center bg-white hover:bg-neutral-50 text-neutral-700 hover:text-blue-600 border border-neutral-200 rounded-xl shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Use my location"
            style={{ width: '40px', height: '40px' }}
          >
            {isLocating ? (
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <LocateFixed className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      {/* Location error message */}
      {locationError && (
        <div className="leaflet-top leaflet-left">
          <div className="leaflet-control leaflet-bar bg-white border border-amber-300 rounded-lg p-3 shadow-lg max-w-xs z-[1001]">
            <div className="flex items-start">
              <div className="text-amber-500 mr-2 mt-0.5">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-sm text-neutral-700">{locationError}</p>
                <button
                  onClick={() => setLocationError(null)}
                  className="mt-2 text-xs text-blue-600 hover:text-blue-800"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export const ZoneMap: React.FC<ZoneMapProps> = ({ zones, selectedZoneId, onZoneSelect, onViewDetails }) => {
  const [isClient, setIsClient] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const [mapId, setMapId] = useState('zone-map');
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    setIsClient(true);
    setMapId(`zone-map-${Date.now()}`); // Force new DOM element on remount

    // Longer delay to ensure DOM is ready and previous instances are cleaned up
    const timer = setTimeout(() => {
      if (mountedRef.current) {
        setMapReady(true);
      }
    }, 500);
    return () => {
      clearTimeout(timer);
      mountedRef.current = false;
      setMapReady(false);
    };
  }, []);

  const selectedZone = zones.find(z => z.id === selectedZoneId) || null;

  if (!isClient) {
    return (
      <div className="h-96 bg-neutral-100 rounded-lg flex items-center justify-center">
        <div className="text-center text-neutral-500">
          <div className="flex justify-center mb-2">
            <Map className="w-10 h-10 text-neutral-400" />
          </div>
          <p>Loading map...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-96 relative rounded-lg overflow-hidden border border-neutral-200">
      {mapReady && (
        <MapContainer
          key={mapId}
          center={SWAT_CENTER}
          zoom={DEFAULT_ZOOM}
          className="h-full w-full"
          style={{ height: '100%', width: '100%', minHeight: '384px' }}
          scrollWheelZoom={true}
          attributionControl={true}
        >
          {/* Layer Control for switching between Street and Satellite */}
          <LayersControl position="topleft">
            <LayersControl.BaseLayer checked name="Street View">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                maxZoom={19}
              />
            </LayersControl.BaseLayer>
            <LayersControl.BaseLayer name="Satellite View (Real)">
              <TileLayer
                attribution="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                maxZoom={19}
              />
            </LayersControl.BaseLayer>
          </LayersControl>

          {/* Map controller for view changes and sizing */}
          <MapController selectedZone={selectedZone} zones={zones} />

          {/* Location controls and user marker */}
          <LocationControls onZoneSelect={onZoneSelect} />

          {/* Zone markers */}
          {zones.map((zone) => {
            if (!zone.coordinates) return null;

            const riskTier = zone.latest_assessment?.tier || 'SAFE';
            const icon = createRiskIcon(riskTier);
            const isSelected = zone.id === selectedZoneId;

            return (
              <Marker
                key={zone.id}
                position={[zone.coordinates.latitude, zone.coordinates.longitude]}
                icon={icon}
                eventHandlers={{
                  click: () => onZoneSelect(zone.id),
                }}
              />
            );
          })}
        </MapContainer>
      )}

      {/* Map legend - positioned above Leaflet tiles */}
      <div className="absolute bottom-4 right-4 bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-xl border border-neutral-300 max-w-xs z-[1000]">
        <h4 className="font-medium text-neutral-900 mb-2 text-sm">Risk Tier Legend</h4>
        <div className="space-y-1">
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-risk-danger mr-2"></div>
            <span className="text-xs">Danger</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-risk-high mr-2"></div>
            <span className="text-xs">High</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-risk-medium mr-2"></div>
            <span className="text-xs">Medium</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-risk-low mr-2"></div>
            <span className="text-xs">Low</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full bg-neutral-400 mr-2"></div>
            <span className="text-xs">Safe/Unknown</span>
          </div>
        </div>
        <div className="mt-3 pt-2 border-t border-neutral-200">
          <p className="text-xs text-neutral-500">
            Click markers for zone details. Map data © OpenStreetMap contributors.
          </p>
        </div>
      </div>

      {/* Selected Zone Overlay - Fixed over the map */}
      {selectedZone && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-white/95 backdrop-blur-sm rounded-xl p-4 shadow-2xl border border-neutral-200 min-w-[280px] z-[1000] pointer-events-auto">
          <div className="flex justify-between items-start mb-3">
            <div>
              <h3 className="font-bold text-lg text-neutral-900">{selectedZone.name}</h3>
              <span className={`px-2.5 py-1 rounded-full text-xs font-bold inline-block mt-1 ${
                (selectedZone.latest_assessment?.tier || 'SAFE') === 'DANGER' ? 'bg-risk-danger text-white' :
                (selectedZone.latest_assessment?.tier || 'SAFE') === 'HIGH' ? 'bg-risk-high text-white' :
                (selectedZone.latest_assessment?.tier || 'SAFE') === 'MEDIUM' ? 'bg-risk-medium text-white' :
                (selectedZone.latest_assessment?.tier || 'SAFE') === 'LOW' ? 'bg-risk-low text-white' :
                'bg-neutral-400 text-white'
              }`}>
                {selectedZone.latest_assessment?.tier || 'SAFE'}
              </span>
            </div>
            <button 
              onClick={() => onZoneSelect(null)}
              className="text-neutral-400 hover:text-neutral-700 bg-neutral-100 hover:bg-neutral-200 rounded-full p-1 transition-colors"
              title="Close details"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>
          
          <div className="space-y-2 mb-4">
            <div className="flex justify-between text-sm">
              <span className="text-neutral-500">Coordinates</span>
              <span className="font-mono text-neutral-700">
                {selectedZone.coordinates.latitude.toFixed(4)}°N, {selectedZone.coordinates.longitude.toFixed(4)}°E
              </span>
            </div>
            
            {selectedZone.upstream_zone_id && (
              <div className="flex justify-between text-sm">
                <span className="text-neutral-500">Upstream</span>
                <span className="font-medium text-neutral-700 text-right">
                  {zones.find(z => z.id === selectedZone.upstream_zone_id)?.name || selectedZone.upstream_zone_id}
                </span>
              </div>
            )}
            
            {selectedZone.latest_assessment && (
              <div className="flex justify-between text-sm">
                <span className="text-neutral-500">Probability</span>
                <span className="font-bold text-neutral-900">
                  {(selectedZone.latest_assessment.probability * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>
          
          <Button
            variant="primary"
            size="sm"
            onClick={() => onViewDetails ? onViewDetails(selectedZone.id) : onZoneSelect(selectedZone.id)}
            className="w-full shadow-md hover:shadow-lg transition-all"
          >
            View Details
          </Button>
        </div>
      )}

      {/* Loading overlay */}
      {!mapReady && (
        <div className="absolute inset-0 bg-white/80 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-neutral-900 mb-3"></div>
            <p className="text-neutral-600">Loading map...</p>
          </div>
        </div>
      )}
    </div>
  );
};