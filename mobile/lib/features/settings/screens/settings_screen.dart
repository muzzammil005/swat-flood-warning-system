import 'package:flutter/material.dart';
import '../../../core/constants/api_constants.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/di/service_locator.dart';
import '../../../core/network/api_client.dart';
import '../../../core/services/notification_service.dart';
import '../../../core/services/storage_service.dart';
import '../../analytics/screens/model_analytics_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final StorageService _storageService = sl<StorageService>();
  final ApiClient _apiClient = sl<ApiClient>();
  final NotificationService _notificationService = sl<NotificationService>();

  late TextEditingController _urlController;
  bool _soundEnabled = true;
  bool _vibrationEnabled = true;
  bool _isTestingConnection = false;
  String? _connectionStatus;
  bool? _connectionSuccess;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: _storageService.getBaseUrl());
    _soundEnabled = _storageService.getSoundEnabled();
    _vibrationEnabled = _storageService.getVibrationEnabled();
  }

  Future<void> _testConnection() async {
    setState(() {
      _isTestingConnection = true;
      _connectionStatus = null;
      _connectionSuccess = null;
    });

    final target = _urlController.text.trim();
    final result = await _apiClient.testBackendConnection(target);

    setState(() {
      _isTestingConnection = false;
      _connectionSuccess = result.isSuccess;
      _connectionStatus = result.formattedMessage;
    });
  }

  void _saveUrl(String url) async {
    final normalized = ApiConstants.normalizeBaseUrl(url);
    _urlController.text = normalized;
    await _storageService.setBaseUrl(normalized);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Updated backend URL to $normalized'),
        backgroundColor: AppColors.primary,
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
          'Settings & FYP Architecture',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Backend Server URL Config
          _buildServerConfigCard(),
          const SizedBox(height: 16),

          // Alert & Hardware Feedback Config
          _buildHardwareConfigCard(),
          const SizedBox(height: 16),

          // XGBoost AI Model Performance & Feature Importance
          _buildAnalyticsShortcutCard(),
          const SizedBox(height: 16),

          // FYP Technical Architecture & Defense Summary
          _buildFypArchitectureCard(),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildServerConfigCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.dns_rounded, color: AppColors.primaryLight, size: 20),
              SizedBox(width: 8),
              Text(
                'FastAPI Backend Server URL',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Configure the endpoint for your testing environment (Emulator, Desktop, or Physical Device over Wi-Fi):',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _urlController,
            style: const TextStyle(color: AppColors.textPrimary),
            decoration: InputDecoration(
              filled: true,
              fillColor: AppColors.surfaceLight,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: BorderSide.none,
              ),
              suffixIcon: IconButton(
                icon: const Icon(Icons.check, color: AppColors.primaryLight),
                onPressed: () => _saveUrl(_urlController.text.trim()),
              ),
            ),
          ),
          const SizedBox(height: 10),

          // Quick Presets
          const Text(
            'Quick Presets:',
            style: TextStyle(color: AppColors.textMuted, fontSize: 11),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              ActionChip(
                backgroundColor: AppColors.surfaceLight,
                avatar: const Icon(Icons.usb, size: 14, color: AppColors.primaryLight),
                label: const Text('USB: adb reverse (127.0.0.1)',
                    style: TextStyle(color: AppColors.primaryLight, fontSize: 11, fontWeight: FontWeight.bold)),
                onPressed: () => _saveUrl(ApiConstants.defaultAdbReverseUrl),
              ),
              ActionChip(
                backgroundColor: AppColors.surfaceLight,
                label: const Text('Android Emulator (10.0.2.2)',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 11)),
                onPressed: () => _saveUrl(ApiConstants.defaultEmulatorUrl),
              ),
              ActionChip(
                backgroundColor: AppColors.surfaceLight,
                label: const Text('Desktop/Web (localhost)',
                    style: TextStyle(color: AppColors.accent, fontSize: 11)),
                onPressed: () => _saveUrl(ApiConstants.defaultDesktopUrl),
              ),
              ActionChip(
                backgroundColor: AppColors.surfaceLight,
                label: const Text('Wi-Fi LAN (192.168.1.100)',
                    style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
                onPressed: () => _saveUrl(ApiConstants.defaultPhoneLanUrl),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Physical device adb reverse guide
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppColors.surfaceLight,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Icon(Icons.info_outline_rounded, color: AppColors.primaryLight, size: 16),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Physical Device USB Setup:\n'
                    '1. Connect phone with USB Debugging enabled.\n'
                    '2. Run on PC: adb reverse tcp:8000 tcp:8000\n'
                    '3. Select "USB: adb reverse" preset above & tap Test.',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 11, height: 1.35),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Test Connection Button
          SizedBox(
            width: double.infinity,
            height: 42,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.primaryLight,
                side: const BorderSide(color: AppColors.primaryLight),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              onPressed: _isTestingConnection ? null : _testConnection,
              icon: _isTestingConnection
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: AppColors.primaryLight),
                    )
                  : const Icon(Icons.network_check_rounded, size: 18),
              label: const Text('Test Backend Connection'),
            ),
          ),

          if (_connectionStatus != null) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: (_connectionSuccess ?? false)
                    ? Colors.green.withValues(alpha: 0.15)
                    : AppColors.riskDanger.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _connectionStatus!,
                style: TextStyle(
                  color: (_connectionSuccess ?? false)
                      ? Colors.greenAccent
                      : AppColors.riskDanger,
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildHardwareConfigCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.notifications_active, color: AppColors.primaryLight, size: 20),
              SizedBox(width: 8),
              Text(
                'Emergency Siren & Haptic Alerts',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Audio Siren Alarm',
                style: TextStyle(color: AppColors.textPrimary, fontSize: 14)),
            subtitle: const Text('Play alarm ringtone when a DANGER alert is active',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 11)),
            value: _soundEnabled,
            activeThumbColor: AppColors.primaryLight,
            onChanged: (v) {
              setState(() => _soundEnabled = v);
              _storageService.setSoundEnabled(v);
            },
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Haptic Vibration Pattern',
                style: TextStyle(color: AppColors.textPrimary, fontSize: 14)),
            subtitle: const Text('Vibrate phone with emergency cadence',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 11)),
            value: _vibrationEnabled,
            activeThumbColor: AppColors.primaryLight,
            onChanged: (v) {
              setState(() => _vibrationEnabled = v);
              _storageService.setVibrationEnabled(v);
            },
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.surfaceLight,
                    foregroundColor: AppColors.textPrimary,
                  ),
                  icon: const Icon(Icons.play_circle_filled, size: 16),
                  label: const Text('Play Siren', style: TextStyle(fontSize: 12)),
                  onPressed: () => _notificationService.triggerEmergencySiren(),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.surfaceLight,
                    foregroundColor: AppColors.riskDanger,
                  ),
                  icon: const Icon(Icons.stop_circle, size: 16),
                  label: const Text('Stop Siren', style: TextStyle(fontSize: 12)),
                  onPressed: () => _notificationService.stopEmergencySiren(),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAnalyticsShortcutCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.query_stats_rounded, color: AppColors.primaryLight, size: 20),
              SizedBox(width: 8),
              Text(
                'AI Model Analytics & Metrics',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Inspect dynamic 3-class F1-scores, precision, recall, and SHAP feature importance from the XGBoost classification backend.',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
          ),
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
              icon: const Icon(Icons.psychology_alt, size: 18),
              label: const Text('View XGBoost Performance & Features'),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const ModelAnalyticsScreen()),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFypArchitectureCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(
            children: [
              Icon(Icons.school, color: AppColors.primaryLight, size: 20),
              SizedBox(width: 8),
              Text(
                'FYP System Architecture & DSA',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          SizedBox(height: 12),
          Text(
            '• River Basin DAG: Swat river is modeled as a Directed Acyclic Graph (Kalam -> Bahrain -> Madyan -> Mingora) for hydrodynamic cascading surge escalation.\n\n'
            '• Spatial Index & Haversine Metric: Client-side spatial computation finds the user\'s nearest river station in O(N) time with spherical great-circle geometry.\n\n'
            '• LightGBM ML Risk Prediction: Machine learning engine evaluates multi-day rolling precipitation, water gauge sensors, and soil saturation with SHAP feature interpretability.\n\n'
            '• Clean Architecture: Decoupled domain entities, reactive service locator (get_it), and offline-first fallback guarantees system reliability during network failure.',
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 12,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}
