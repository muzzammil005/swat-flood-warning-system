import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/di/service_locator.dart';
import '../../../core/models/model_analytics_model.dart';
import '../../../core/models/zone_model.dart';
import '../../../core/network/api_client.dart';
import '../../../core/services/location_service.dart';
import '../../zone_detail/screens/zone_detail_screen.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final ApiClient _apiClient = sl<ApiClient>();
  final LocationService _locationService = sl<LocationService>();
  final MapController _mapController = MapController();

  List<ZoneModel> _zones = [];
  Map<String, InundationExtent> _inundations = {};
  ZoneModel? _selectedZone;
  LatLng? _userLocation;
  bool _isLoading = true;
  bool _showInundationLayer = true;

  // Swat River flow path (Kalam -> Bahrain -> Madyan -> Mingora)
  final List<LatLng> _swatRiverPath = const [
    LatLng(35.479, 72.596), // Kalam
    LatLng(35.320, 72.560), // Intermediate gorge
    LatLng(35.189, 72.529), // Bahrain
    LatLng(35.105, 72.500), // Intermediate tributary
    LatLng(35.022, 72.475), // Madyan
    LatLng(34.900, 72.410), // Lower basin
    LatLng(34.774, 72.361), // Mingora
  ];

  @override
  void initState() {
    super.initState();
    _loadMapData();
  }

  Future<void> _loadMapData() async {
    setState(() => _isLoading = true);
    try {
      final zones = await _apiClient.getZones();
      final userCoords = await _locationService.getCurrentLocation();

      // Fetch inundation polygon for any zone at HIGH risk
      final inundationMap = <String, InundationExtent>{};
      final highRiskZones = zones.where((z) {
        final tier = z.riskTier.toUpperCase();
        return tier == 'HIGH' || tier == 'DANGER';
      }).toList();

      for (final zone in highRiskZones) {
        try {
          final extent = await _apiClient.getZoneInundation(zone.id);
          inundationMap[zone.id] = extent;
        } catch (e) {
          debugPrint('[MapScreen] Failed to load inundation for ${zone.id}: $e');
        }
      }

      if (!mounted) return;
      setState(() {
        _zones = zones;
        _inundations = inundationMap;
        _userLocation = LatLng(userCoords.latitude, userCoords.longitude);
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  void _recenterBasin() {
    _mapController.move(const LatLng(35.2, 72.4), 10.0);
  }

  void _locateUser() async {
    final coords = await _locationService.getCurrentLocation();
    final userPos = LatLng(coords.latitude, coords.longitude);
    setState(() => _userLocation = userPos);
    _mapController.move(userPos, 13.0);
  }

  LatLng _calculateCentroid(List<LatLng> points) {
    if (points.isEmpty) return const LatLng(35.2, 72.4);
    double latSum = 0;
    double lngSum = 0;
    for (final p in points) {
      latSum += p.latitude;
      lngSum += p.longitude;
    }
    return LatLng(latSum / points.length, lngSum / points.length);
  }

  void _showInundationDisclaimer(InundationExtent extent, ZoneModel zone) {
    // Show floating SnackBar
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: const Color(0xFF1E293B),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 4),
        content: Row(
          children: [
            const Icon(Icons.info_outline, color: Colors.amberAccent, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                '${zone.name} Inundation: ${extent.disclaimer}',
                style: const TextStyle(color: Colors.white, fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );

    // Show detailed Bottom Sheet with disclaimer
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEF4444).withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.warning_amber_rounded,
                      color: Colors.redAccent, size: 24),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Projected Inundation Extent (${zone.name})',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const Text(
                        'XGBoost High-Risk Inundation Forecast',
                        style: TextStyle(
                            fontSize: 11, color: AppColors.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.amber.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.amber.withValues(alpha: 0.5)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.info, color: Colors.amberAccent, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      extent.disclaimer, // "Approximate estimate, not an exact boundary."
                      style: const TextStyle(
                        color: Colors.amberAccent,
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            const Text(
              'The semi-transparent red/orange polygon projected on the GIS map delineates potential riverine runoff inundation. This boundary is mathematically modeled using DEM elevation gradients, 3-day upstream rainfall anomaly ratios, and river flow telemetry.',
              style: TextStyle(
                  color: AppColors.textSecondary, fontSize: 12, height: 1.4),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Understood'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: const Text(
          'Swat River GIS Map',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
        actions: [
          IconButton(
            icon: Icon(
              _showInundationLayer ? Icons.layers : Icons.layers_clear,
              color: _showInundationLayer
                  ? AppColors.primaryLight
                  : AppColors.textMuted,
            ),
            onPressed: () {
              setState(() {
                _showInundationLayer = !_showInundationLayer;
              });
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(_showInundationLayer
                      ? 'Inundation overlay visible'
                      : 'Inundation overlay hidden'),
                  duration: const Duration(seconds: 1),
                ),
              );
            },
            tooltip: 'Toggle Inundation Layer',
          ),
          IconButton(
            icon: const Icon(Icons.refresh, color: AppColors.primaryLight),
            onPressed: _loadMapData,
            tooltip: 'Refresh Map',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.primaryLight))
          : Stack(
              children: [
                FlutterMap(
                  mapController: _mapController,
                  options: const MapOptions(
                    initialCenter: LatLng(35.2, 72.4),
                    initialZoom: 10.0,
                    minZoom: 7.0,
                    maxZoom: 17.0,
                  ),
                  children: [
                    // OpenStreetMap Street & River tiles
                    TileLayer(
                      urlTemplate:
                          'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'com.fyp.swat_flood_warning',
                    ),

                    // Swat River Course Polyline
                    PolylineLayer(
                      polylines: [
                        Polyline(
                          points: _swatRiverPath,
                          strokeWidth: 6.0,
                          color:
                              const Color(0xFF0284C7).withValues(alpha: 0.8),
                        ),
                      ],
                    ),

                    // Inundation Map Overlay (estimated_polygon for HIGH risk zones)
                    if (_showInundationLayer && _inundations.isNotEmpty)
                      PolygonLayer(
                        polygons: _inundations.entries.map((entry) {
                          final extent = entry.value;
                          return Polygon(
                            points: extent.toLatLngList(),
                            color: const Color(0xFFEF4444)
                                .withValues(alpha: 0.35), // semi-transparent red/orange
                            borderColor: const Color(0xFFDC2626),
                            borderStrokeWidth: 2.5,
                          );
                        }).toList(),
                      ),

                    // River Basin Monitoring Stations & Inundation Centroid Badges
                    MarkerLayer(
                      markers: [
                        // User position marker
                        if (_userLocation != null)
                          Marker(
                            point: _userLocation!,
                            width: 36,
                            height: 36,
                            child: Container(
                              decoration: BoxDecoration(
                                color: Colors.blue.withValues(alpha: 0.3),
                                shape: BoxShape.circle,
                              ),
                              child: Center(
                                child: Container(
                                  width: 16,
                                  height: 16,
                                  decoration: const BoxDecoration(
                                    color: Colors.blueAccent,
                                    shape: BoxShape.circle,
                                  ),
                                ),
                              ),
                            ),
                          ),

                        // Inundation Centroid Badges (Tappable with disclaimer)
                        if (_showInundationLayer)
                          ..._inundations.entries.map((entry) {
                            final extent = entry.value;
                            final points = extent.toLatLngList();
                            final centroid = _calculateCentroid(points);
                            final zone = _zones.firstWhere(
                              (z) => z.id == entry.key,
                              orElse: () => _zones.first,
                            );

                            return Marker(
                              point: centroid,
                              width: 140,
                              height: 32,
                              child: GestureDetector(
                                onTap: () =>
                                    _showInundationDisclaimer(extent, zone),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFDC2626),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                        color: Colors.white, width: 1.5),
                                    boxShadow: [
                                      BoxShadow(
                                        color:
                                            Colors.black.withValues(alpha: 0.4),
                                        blurRadius: 6,
                                        offset: const Offset(0, 2),
                                      ),
                                    ],
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: const [
                                      Icon(Icons.warning_amber_rounded,
                                          color: Colors.white, size: 14),
                                      SizedBox(width: 4),
                                      Text(
                                        'Inundation (Tap)',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 10,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          }),

                        // Zone telemetry stations
                        ..._zones.map((zone) {
                          final color = AppColors.getRiskColor(zone.riskTier);
                          final isHigh =
                              zone.riskTier.toUpperCase() == 'HIGH' ||
                                  zone.riskTier.toUpperCase() == 'DANGER';

                          return Marker(
                            point: LatLng(
                              zone.coordinates.latitude,
                              zone.coordinates.longitude,
                            ),
                            width: 60,
                            height: 60,
                            child: GestureDetector(
                              onTap: () {
                                setState(() => _selectedZone = zone);
                              },
                              child: Stack(
                                alignment: Alignment.center,
                                children: [
                                  if (isHigh)
                                    Container(
                                      width: 50,
                                      height: 50,
                                      decoration: BoxDecoration(
                                        shape: BoxShape.circle,
                                        color: color.withValues(alpha: 0.35),
                                      ),
                                    ),
                                  Container(
                                    width: 34,
                                    height: 34,
                                    decoration: BoxDecoration(
                                      color: color,
                                      shape: BoxShape.circle,
                                      border: Border.all(
                                        color: Colors.white,
                                        width: 2.5,
                                      ),
                                      boxShadow: [
                                        BoxShadow(
                                          color: color.withValues(alpha: 0.5),
                                          blurRadius: 8,
                                          spreadRadius: 2,
                                        ),
                                      ],
                                    ),
                                    child: const Center(
                                      child: Icon(
                                        Icons.water_drop,
                                        color: Colors.white,
                                        size: 18,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        }),
                      ],
                    ),
                  ],
                ),

                // Floating Map Controls (Recenter & Locate Me)
                Positioned(
                  top: 16,
                  right: 16,
                  child: Column(
                    children: [
                      FloatingActionButton.small(
                        heroTag: 'recenter_btn',
                        backgroundColor: AppColors.surface,
                        foregroundColor: AppColors.primaryLight,
                        onPressed: _recenterBasin,
                        tooltip: 'Recenter Basin',
                        child: const Icon(Icons.filter_center_focus),
                      ),
                      const SizedBox(height: 8),
                      FloatingActionButton.small(
                        heroTag: 'locate_btn',
                        backgroundColor: AppColors.surface,
                        foregroundColor: AppColors.primaryLight,
                        onPressed: _locateUser,
                        tooltip: 'Locate My Position',
                        child: const Icon(Icons.my_location),
                      ),
                    ],
                  ),
                ),

                // River flow legend
                Positioned(
                  top: 16,
                  left: 16,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: AppColors.surface.withValues(alpha: 0.9),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 14,
                              height: 4,
                              decoration: BoxDecoration(
                                color: AppColors.primary,
                                borderRadius: BorderRadius.circular(2),
                              ),
                            ),
                            const SizedBox(width: 6),
                            const Text(
                              'Swat River Flow Path',
                              style: TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (_showInundationLayer && _inundations.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        GestureDetector(
                          onTap: () {
                            final entry = _inundations.entries.first;
                            final zone = _zones.firstWhere(
                              (z) => z.id == entry.key,
                              orElse: () => _zones.first,
                            );
                            _showInundationDisclaimer(entry.value, zone);
                          },
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: const Color(0xFFEF4444)
                                  .withValues(alpha: 0.92),
                              borderRadius: BorderRadius.circular(8),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.red.withValues(alpha: 0.4),
                                  blurRadius: 6,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: const [
                                Icon(Icons.warning_amber_rounded,
                                    color: Colors.white, size: 14),
                                SizedBox(width: 6),
                                Text(
                                  'HIGH Inundation Overlay (Tap)',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),

                // Selected Zone Bottom Sheet Card
                if (_selectedZone != null)
                  Positioned(
                    bottom: 16,
                    left: 16,
                    right: 16,
                    child: _buildZonePreviewCard(_selectedZone!),
                  ),
              ],
            ),
    );
  }

  Widget _buildZonePreviewCard(ZoneModel zone) {
    final color = AppColors.getRiskColor(zone.riskTier);
    final hasInundation = _inundations.containsKey(zone.id);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color, width: 1.5),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.4),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                zone.name,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                ),
              ),
              IconButton(
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                icon: const Icon(Icons.close,
                    color: AppColors.textMuted, size: 20),
                onPressed: () => setState(() => _selectedZone = null),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: color),
                ),
                child: Text(
                  'Risk: ${zone.riskTier}',
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Text(
                'Water Level: ${zone.currentWaterLevel?.toStringAsFixed(1) ?? '2.1'}m',
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w600,
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            zone.explanation,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 11.5,
            ),
          ),
          if (hasInundation) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                    color: const Color(0xFFEF4444).withValues(alpha: 0.5)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.waves, color: Colors.redAccent, size: 18),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'Projected Inundation Extent Active',
                      style: TextStyle(
                        color: Colors.redAccent,
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  InkWell(
                    onTap: () =>
                        _showInundationDisclaimer(_inundations[zone.id]!, zone),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.redAccent,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        'Disclaimer',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              icon: const Icon(Icons.analytics_outlined, size: 18),
              label: const Text('View Full Station Telemetry'),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => ZoneDetailScreen(zoneId: zone.id),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
