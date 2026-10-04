import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/di/service_locator.dart';
import '../../../core/dsa/river_graph.dart';
import '../../../core/dsa/spatial_index.dart';
import '../../../core/models/alert_model.dart';
import '../../../core/models/zone_model.dart';
import '../../../core/network/api_client.dart';
import '../../../core/services/location_service.dart';
import '../../../core/services/notification_service.dart';
import '../../analytics/screens/model_analytics_screen.dart';
import '../../zone_detail/screens/zone_detail_screen.dart';

class DashboardScreen extends StatefulWidget {
  final Function(int) onNavigateTab;

  const DashboardScreen({super.key, required this.onNavigateTab});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiClient _apiClient = sl<ApiClient>();
  final LocationService _locationService = sl<LocationService>();
  final NotificationService _notificationService = sl<NotificationService>();
  final RiverGraph _riverGraph = sl<RiverGraph>();

  List<ZoneModel> _zones = [];
  List<AlertModel> _alerts = [];
  ZoneModel? _nearestZone;
  double? _nearestDistance;
  bool _isLoading = true;
  String? _surgeAlertMessage;

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);

    try {
      final zonesFuture = _apiClient.getZones();
      final alertsFuture = _apiClient.getAlerts();
      final locationFuture = _locationService.getCurrentLocation();

      final results = await Future.wait([
        zonesFuture,
        alertsFuture,
        locationFuture,
      ]);

      final zones = results[0] as List<ZoneModel>;
      final alerts = results[1] as List<AlertModel>;
      final userCoords = results[2] as CoordinatesModel;

      // Build DSA River Graph
      _riverGraph.buildFromZones(zones);

      // Perform Nearest Neighbor calculation using Haversine DSA
      final nearestResult = SpatialIndex.findNearestZone(
        userCoords.latitude,
        userCoords.longitude,
        zones,
      );

      // Check cascading surge
      String? surgeMsg;
      for (final z in zones) {
        final msg = _riverGraph.checkCascadingSurge(z.id);
        if (msg != null) {
          surgeMsg = msg;
          break;
        }
      }

      setState(() {
        _zones = zones;
        _alerts = alerts;
        _nearestZone = nearestResult?.zone;
        _nearestDistance = nearestResult?.distanceMeters;
        _surgeAlertMessage = surgeMsg;
        _isLoading = false;
      });

      // If any critical danger alert exists, trigger siren
      final hasDanger = alerts.any((a) => a.isCritical);
      if (hasDanger) {
        _notificationService.triggerEmergencySiren();
      }
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.water, color: AppColors.primaryLight, size: 24),
            ),
            const SizedBox(width: 12),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Flood Watch',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  'Swat River Early Warning System',
                  style: TextStyle(
                    fontSize: 11,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.analytics_outlined, color: AppColors.primaryLight),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ModelAnalyticsScreen()),
              );
            },
            tooltip: 'XGBoost Model Analytics',
          ),
          IconButton(
            icon: const Icon(Icons.refresh, color: AppColors.primaryLight),
            onPressed: _loadDashboardData,
            tooltip: 'Refresh Status',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primaryLight))
          : RefreshIndicator(
              onRefresh: _loadDashboardData,
              color: AppColors.primaryLight,
              backgroundColor: AppColors.surface,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // River Basin Status Summary Header
                  _buildBasinStatusBanner(),
                  const SizedBox(height: 16),

                  // Cascading Surge Banner (DAG traversal result)
                  if (_surgeAlertMessage != null) ...[
                    _buildCascadingSurgeBanner(),
                    const SizedBox(height: 16),
                  ],

                  // Nearest Zone Card (DSA Haversine result)
                  if (_nearestZone != null) ...[
                    _buildNearestZoneCard(),
                    const SizedBox(height: 20),
                  ],

                  // Quick Action Buttons
                  _buildQuickActionButtons(),
                  const SizedBox(height: 16),

                  // XGBoost Model Performance & Feature Importance Banner
                  _buildModelAnalyticsBanner(),
                  const SizedBox(height: 24),

                  // River Zones Header
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'River Basin Zones',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      Text(
                        'Upstream -> Downstream',
                        style: TextStyle(
                          fontSize: 12,
                          color: AppColors.primaryLight.withValues(alpha: 0.8),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Zones List
                  ..._zones.map((zone) => _buildZoneCard(zone)),

                  const SizedBox(height: 16),

                  // Latest Alerts Ticker
                  if (_alerts.isNotEmpty) ...[
                    _buildAlertsSection(),
                    const SizedBox(height: 24),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _buildBasinStatusBanner() {
    final hasDanger = _zones.any((z) => z.riskTier == 'DANGER');
    final hasHigh = _zones.any((z) => z.riskTier == 'HIGH');

    final color = hasDanger
        ? AppColors.riskDanger
        : hasHigh
            ? AppColors.riskHigh
            : AppColors.riskLow;

    final title = hasDanger
        ? 'DANGER: Flash Flood Detected'
        : hasHigh
            ? 'WARNING: Elevated River Discharge'
            : 'NORMAL: River Levels Within Limits';

    final subtitle = hasDanger
        ? 'Active overflow in upper catchment. Immediate precautions advised.'
        : 'All 4 telemetry stations active. AI risk evaluation ongoing.';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        border: Border.all(color: color, width: 1.5),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.2),
              shape: BoxShape.circle,
            ),
            child: Icon(
              hasDanger ? Icons.warning_rounded : Icons.shield_rounded,
              color: color,
              size: 28,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCascadingSurgeBanner() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.riskHigh.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.riskHigh.withValues(alpha: 0.6)),
      ),
      child: Row(
        children: [
          const Icon(Icons.waves, color: AppColors.riskHigh, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _surgeAlertMessage!,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 12.5,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNearestZoneCard() {
    final distKm = (_nearestDistance != null)
        ? (_nearestDistance! / 1000).toStringAsFixed(1)
        : '0.0';

    final tierColor = AppColors.getRiskColor(_nearestZone!.riskTier);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.surface,
            AppColors.surfaceLight.withValues(alpha: 0.4),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.my_location, color: AppColors.primaryLight, size: 18),
                  const SizedBox(width: 8),
                  const Text(
                    'Your Nearest Station',
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  '$distKm km away',
                  style: const TextStyle(
                    color: AppColors.primaryLight,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                _nearestZone!.name,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: tierColor.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: tierColor),
                ),
                child: Text(
                  _nearestZone!.riskTier,
                  style: TextStyle(
                    color: tierColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _nearestZone!.explanation,
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 14),
          InkWell(
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => ZoneDetailScreen(zoneId: _nearestZone!.id),
                ),
              );
            },
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: const [
                Text(
                  'Detailed Telemetry & Trends',
                  style: TextStyle(
                    color: AppColors.primaryLight,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(width: 4),
                Icon(Icons.arrow_forward_rounded, color: AppColors.primaryLight, size: 16),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickActionButtons() {
    return Row(
      children: [
        Expanded(
          child: _buildActionCard(
            title: 'Live River Map',
            icon: Icons.map_outlined,
            color: AppColors.primaryLight,
            onTap: () => widget.onNavigateTab(1),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildActionCard(
            title: 'Report Incident',
            icon: Icons.add_alert_rounded,
            color: AppColors.riskHigh,
            onTap: () => widget.onNavigateTab(3),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildActionCard(
            title: 'Relief Depots',
            icon: Icons.emergency_rounded,
            color: AppColors.accent,
            onTap: () => widget.onNavigateTab(4),
          ),
        ),
      ],
    );
  }

  Widget _buildActionCard({
    required String title,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 8),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildModelAnalyticsBanner() {
    return InkWell(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const ModelAnalyticsScreen()),
        );
      },
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.primaryLight.withValues(alpha: 0.3)),
          gradient: LinearGradient(
            colors: [
              AppColors.surface,
              AppColors.primary.withValues(alpha: 0.15),
            ],
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(
                Icons.psychology_alt_rounded,
                color: AppColors.primaryLight,
                size: 22,
              ),
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'XGBoost AI Model Analytics',
                    style: TextStyle(
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.bold,
                      fontSize: 13.5,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    '3-Class F1-Scores & SHAP Feature Importance',
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppColors.surfaceLight,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(
                Icons.arrow_forward_ios,
                color: AppColors.primaryLight,
                size: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildZoneCard(ZoneModel zone) {
    final tierColor = AppColors.getRiskColor(zone.riskTier);
    final waterLevel = zone.currentWaterLevel != null
        ? '${zone.currentWaterLevel!.toStringAsFixed(1)}m'
        : '2.1m';

    final warningLevel = zone.thresholds != null
        ? '${zone.thresholds!.warningLevelMetres.toStringAsFixed(1)}m'
        : '2.0m';

    final criticalLevel = zone.thresholds != null
        ? '${zone.thresholds!.criticalLevelMetres.toStringAsFixed(1)}m'
        : '3.0m';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: zone.riskTier == 'DANGER'
              ? AppColors.riskDanger.withValues(alpha: 0.5)
              : AppColors.border,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ZoneDetailScreen(zoneId: zone.id),
              ),
            );
          },
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Text(
                          zone.name,
                          style: const TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (zone.upstreamZoneId == null) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppColors.primary.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: const Text(
                              'Headwater',
                              style: TextStyle(
                                color: AppColors.primaryLight,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: tierColor.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: tierColor),
                      ),
                      child: Text(
                        zone.riskTier,
                        style: TextStyle(
                          color: tierColor,
                          fontWeight: FontWeight.bold,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildStatItem('Water Level', waterLevel, AppColors.primaryLight),
                    _buildStatItem('Warning Threshold', warningLevel, AppColors.riskMedium),
                    _buildStatItem('Critical Level', criticalLevel, AppColors.riskDanger),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  zone.explanation,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 11.5,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatItem(String label, String value, Color valueColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: AppColors.textMuted,
            fontSize: 10,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            color: valueColor,
            fontWeight: FontWeight.bold,
            fontSize: 13,
          ),
        ),
      ],
    );
  }

  Widget _buildAlertsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Active Emergency Alerts',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
              ),
            ),
            TextButton(
              onPressed: () => widget.onNavigateTab(2),
              child: const Text(
                'View All',
                style: TextStyle(color: AppColors.primaryLight, fontSize: 13),
              ),
            ),
          ],
        ),
        ..._alerts.take(2).map((alert) {
          final color = AppColors.getRiskColor(alert.severity);
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: color.withValues(alpha: 0.5)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.warning_amber_rounded, color: color, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        alert.headline,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        alert.description,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        }),
      ],
    );
  }
}
