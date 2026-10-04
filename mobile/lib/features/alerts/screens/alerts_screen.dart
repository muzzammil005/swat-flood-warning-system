import 'package:flutter/material.dart';
import 'package:timeago/timeago.dart' as timeago;
import '../../../core/constants/app_colors.dart';
import '../../../core/di/service_locator.dart';
import '../../../core/models/alert_model.dart';
import '../../../core/network/api_client.dart';
import '../../../core/services/notification_service.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key});

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  final ApiClient _apiClient = sl<ApiClient>();
  final NotificationService _notificationService = sl<NotificationService>();

  List<AlertModel> _alerts = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadAlerts();
  }

  Future<void> _loadAlerts() async {
    setState(() => _isLoading = true);
    try {
      final alerts = await _apiClient.getAlerts();
      // Sort by severity (DANGER > HIGH > MEDIUM > LOW) and date
      alerts.sort((a, b) {
        final sevMap = {'DANGER': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'INFO': 0};
        final sevA = sevMap[a.severity.toUpperCase()] ?? 0;
        final sevB = sevMap[b.severity.toUpperCase()] ?? 0;
        if (sevA != sevB) return sevB.compareTo(sevA);
        return b.sentAt.compareTo(a.sentAt);
      });

      setState(() {
        _alerts = alerts;
        _isLoading = false;
      });
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  void _showBroadcastDialog() {
    final messenger = ScaffoldMessenger.of(context);
    final headlineController = TextEditingController();
    final descController = TextEditingController();
    String selectedZone = 'zone-kalam';
    String selectedSeverity = 'DANGER';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          backgroundColor: AppColors.surface,
          title: const Text(
            'Broadcast Emergency Alert',
            style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.bold),
          ),
          content: SinglefulScrollViewWrapper(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: selectedZone,
                  dropdownColor: AppColors.surface,
                  style: const TextStyle(color: AppColors.textPrimary),
                  decoration: const InputDecoration(
                    labelText: 'Target Zone',
                    labelStyle: TextStyle(color: AppColors.textSecondary),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'zone-kalam', child: Text('Kalam Bazaar')),
                    DropdownMenuItem(value: 'zone-bahrain', child: Text('Bahrain')),
                    DropdownMenuItem(value: 'zone-madyan', child: Text('Madyan')),
                    DropdownMenuItem(value: 'zone-mingora', child: Text('Mingora City')),
                  ],
                  onChanged: (v) => setDialogState(() => selectedZone = v!),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: selectedSeverity,
                  dropdownColor: AppColors.surface,
                  style: const TextStyle(color: AppColors.textPrimary),
                  decoration: const InputDecoration(
                    labelText: 'Severity Tier',
                    labelStyle: TextStyle(color: AppColors.textSecondary),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'DANGER', child: Text('DANGER (Critical Evacuation)')),
                    DropdownMenuItem(value: 'HIGH', child: Text('HIGH (Warning)')),
                    DropdownMenuItem(value: 'MEDIUM', child: Text('MEDIUM (Advisory)')),
                  ],
                  onChanged: (v) => setDialogState(() => selectedSeverity = v!),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: headlineController,
                  style: const TextStyle(color: AppColors.textPrimary),
                  decoration: const InputDecoration(
                    labelText: 'Headline',
                    hintText: 'e.g. Flash Flood Evacuation Notice',
                    labelStyle: TextStyle(color: AppColors.textSecondary),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: descController,
                  maxLines: 3,
                  style: const TextStyle(color: AppColors.textPrimary),
                  decoration: const InputDecoration(
                    labelText: 'Broadcast Instructions',
                    hintText: 'Detailed safety instructions...',
                    labelStyle: TextStyle(color: AppColors.textSecondary),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel', style: TextStyle(color: AppColors.textMuted)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.riskDanger,
                foregroundColor: Colors.white,
              ),
              onPressed: () async {
                if (headlineController.text.trim().isEmpty) return;
                Navigator.pop(ctx);

                final ok = await _apiClient.broadcastAlert(
                  zoneId: selectedZone,
                  severity: selectedSeverity,
                  headline: headlineController.text.trim(),
                  description: descController.text.trim(),
                );

                if (ok) {
                  _loadAlerts();
                  messenger.showSnackBar(
                    const SnackBar(
                      content: Text('Alert broadcasted successfully'),
                      backgroundColor: Colors.green,
                    ),
                  );
                }
              },
              child: const Text('Broadcast'),
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
          'Emergency CAP Alerts',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_alert, color: AppColors.riskDanger),
            tooltip: 'Broadcast Alert',
            onPressed: _showBroadcastDialog,
          ),
          IconButton(
            icon: const Icon(Icons.refresh, color: AppColors.primaryLight),
            onPressed: _loadAlerts,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primaryLight))
          : Column(
              children: [
                // Audio Siren Banner
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  color: AppColors.surface,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: const [
                          Icon(Icons.volume_up, color: AppColors.primaryLight, size: 20),
                          SizedBox(width: 8),
                          Text(
                            'Emergency Siren System',
                            style: TextStyle(
                              color: AppColors.textPrimary,
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.riskDanger,
                          side: const BorderSide(color: AppColors.riskDanger),
                          visualDensity: VisualDensity.compact,
                        ),
                        icon: const Icon(Icons.play_arrow_rounded, size: 18),
                        label: const Text('Test Siren'),
                        onPressed: () {
                          _notificationService.triggerEmergencySiren();
                        },
                      ),
                    ],
                  ),
                ),

                // Alerts List
                Expanded(
                  child: _alerts.isEmpty
                      ? const Center(
                          child: Text(
                            'No active emergency alerts at this time.',
                            style: TextStyle(color: AppColors.textSecondary),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _loadAlerts,
                          color: AppColors.primaryLight,
                          child: ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: _alerts.length,
                            itemBuilder: (context, index) {
                              final alert = _alerts[index];
                              return _buildAlertCard(alert);
                            },
                          ),
                        ),
                ),
              ],
            ),
    );
  }

  Widget _buildAlertCard(AlertModel alert) {
    final color = AppColors.getRiskColor(alert.severity);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.6), width: 1.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    alert.severity.toUpperCase(),
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 11,
                    ),
                  ),
                ),
                Text(
                  timeago.format(alert.sentAt),
                  style: const TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              alert.headline,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 15,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              alert.description,
              style: const TextStyle(
                color: AppColors.textSecondary,
                fontSize: 13,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                _buildChip('Urgency: ${alert.urgency}'),
                const SizedBox(width: 8),
                _buildChip('Certainty: ${alert.certainty}'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChip(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        text,
        style: const TextStyle(color: AppColors.textSecondary, fontSize: 11),
      ),
    );
  }
}

class SinglefulScrollViewWrapper extends StatelessWidget {
  final Widget child;
  const SinglefulScrollViewWrapper({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(child: child);
  }
}
