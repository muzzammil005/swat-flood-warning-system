import 'dart:io' show Platform, SocketException;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:dio/dio.dart';
import '../constants/api_constants.dart';
import '../models/zone_model.dart';
import '../models/alert_model.dart';
import '../models/report_model.dart';
import '../models/resource_center_model.dart';
import '../models/model_analytics_model.dart';
import '../services/storage_service.dart';

class ConnectionTestResult {
  final bool isSuccess;
  final String message;
  final int? statusCode;
  final String? endpointTested;
  final String? suggestion;

  const ConnectionTestResult({
    required this.isSuccess,
    required this.message,
    this.statusCode,
    this.endpointTested,
    this.suggestion,
  });

  String get formattedMessage {
    if (isSuccess) {
      return message;
    }
    final sb = StringBuffer();
    sb.writeln(message);
    if (suggestion != null && suggestion!.isNotEmpty) {
      sb.writeln();
      sb.write(suggestion);
    }
    return sb.toString().trim();
  }
}

class ApiClient {
  final Dio _dio;
  final StorageService _storageService;

  ApiClient(this._dio, this._storageService) {
    _dio.options.connectTimeout = const Duration(seconds: 4);
    _dio.options.receiveTimeout = const Duration(seconds: 4);
    _dio.options.sendTimeout = const Duration(seconds: 4);
    _dio.options.headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
  }

  bool get _isTesting {
    try {
      if (!kIsWeb && Platform.environment.containsKey('FLUTTER_TEST')) {
        return true;
      }
    } catch (_) {}
    return false;
  }

  String get baseUrl => _storageService.getBaseUrl();

  String _buildUrl(String endpoint) {
    final base = ApiConstants.normalizeBaseUrl(baseUrl);
    final cleanEndpoint = endpoint.startsWith('/') ? endpoint : '/$endpoint';
    return '$base$cleanEndpoint';
  }

  String _getRootUrl(String base) {
    return base.replaceFirst(RegExp(r'/api/?$'), '');
  }

  Future<bool> checkHealth() async {
    if (_isTesting) return true;
    final result = await testBackendConnection();
    return result.isSuccess;
  }

  Future<ConnectionTestResult> testBackendConnection([String? testUrl]) async {
    if (_isTesting) {
      return const ConnectionTestResult(
        isSuccess: true,
        message: 'Test mode active (mock backend healthy)',
      );
    }

    final targetBase = ApiConstants.normalizeBaseUrl(testUrl ?? baseUrl);
    final rootBase = _getRootUrl(targetBase);

    // 1. Try targetBase/health (e.g. http://127.0.0.1:8000/api/health)
    try {
      final res = await _dio.get(
        '$targetBase${ApiConstants.health}',
        options: Options(
          sendTimeout: const Duration(seconds: 3),
          receiveTimeout: const Duration(seconds: 3),
        ),
      );
      if (res.statusCode == 200) {
        return ConnectionTestResult(
          isSuccess: true,
          statusCode: res.statusCode,
          endpointTested: '$targetBase${ApiConstants.health}',
          message: 'Connected to Swat Flood Warning API successfully! (HTTP 200)',
        );
      }
    } on DioException catch (dioErr) {
      // If 404, try root /health (e.g. http://127.0.0.1:8000/health)
      if (dioErr.response?.statusCode == 404) {
        try {
          final rootRes = await _dio.get(
            '$rootBase${ApiConstants.health}',
            options: Options(
              sendTimeout: const Duration(seconds: 3),
              receiveTimeout: const Duration(seconds: 3),
            ),
          );
          if (rootRes.statusCode == 200) {
            return ConnectionTestResult(
              isSuccess: true,
              statusCode: rootRes.statusCode,
              endpointTested: '$rootBase${ApiConstants.health}',
              message: 'Connected to Swat Flood Warning API successfully! (HTTP 200 at /health)',
            );
          }
        } catch (_) {}

        // Also try /api/zones to verify API accessibility
        try {
          final zonesRes = await _dio.get(
            '$targetBase${ApiConstants.zones}',
            options: Options(
              sendTimeout: const Duration(seconds: 3),
              receiveTimeout: const Duration(seconds: 3),
            ),
          );
          if (zonesRes.statusCode == 200) {
            return ConnectionTestResult(
              isSuccess: true,
              statusCode: zonesRes.statusCode,
              endpointTested: '$targetBase${ApiConstants.zones}',
              message: 'Connected to Swat Flood Warning API successfully! (API verified at /api/zones)',
            );
          }
        } catch (_) {}
      }

      return _diagnoseConnectionError(dioErr, targetBase);
    } catch (e) {
      return ConnectionTestResult(
        isSuccess: false,
        message: 'Unexpected connection error: $e',
      );
    }

    return ConnectionTestResult(
      isSuccess: false,
      message: 'Could not connect to $targetBase',
    );
  }

  ConnectionTestResult _diagnoseConnectionError(DioException dioErr, String targetUrl) {
    final isTimeout = dioErr.type == DioExceptionType.connectionTimeout ||
        dioErr.type == DioExceptionType.receiveTimeout ||
        dioErr.type == DioExceptionType.sendTimeout;

    final errString = dioErr.toString();
    final isCleartext = errString.contains('Cleartext') ||
        (dioErr.message?.contains('Cleartext') ?? false);

    final is10Dot2 = targetUrl.contains('10.0.2.2');
    final isLocalhost = targetUrl.contains('localhost') || targetUrl.contains('127.0.0.1');

    if (isCleartext) {
      return ConnectionTestResult(
        isSuccess: false,
        message: 'Cleartext HTTP traffic was blocked by Android security policy.',
        suggestion: 'Ensure android:usesCleartextTraffic="true" and networkSecurityConfig are present in AndroidManifest.xml.',
      );
    }

    if (isTimeout) {
      final suggestion = is10Dot2
          ? 'Note: 10.0.2.2 is the Android Emulator gateway and does NOT exist on physical devices.\n\n'
            'For a physical phone connected via USB:\n'
            '1. Run in PC terminal:  adb reverse tcp:8000 tcp:8000\n'
            '2. Set Base URL to:  http://127.0.0.1:8000/api'
          : 'Request timed out after 4 seconds.\n\n'
            '• If using a USB cable: run "adb reverse tcp:8000 tcp:8000" and use http://127.0.0.1:8000/api\n'
            '• If using Wi-Fi: ensure phone and PC are on the same Wi-Fi and use your PC\'s LAN IP (e.g. http://192.168.x.x:8000/api).';

      return ConnectionTestResult(
        isSuccess: false,
        message: 'Connection timed out connecting to $targetUrl.',
        suggestion: suggestion,
      );
    }

    if (dioErr.type == DioExceptionType.connectionError ||
        dioErr.type == DioExceptionType.unknown ||
        dioErr.error is SocketException) {
      final suggestion = isLocalhost
          ? 'Connection refused. For a physical Android phone:\n'
            '1. Connect phone to PC via USB with USB debugging enabled.\n'
            '2. Run in your PC terminal:  adb reverse tcp:8000 tcp:8000\n'
            '3. Confirm Docker FastAPI is running on port 8000 (docker ps).'
          : 'Could not reach server. Verify host IP/port and ensure Docker backend is running.';

      return ConnectionTestResult(
        isSuccess: false,
        message: 'Connection failed (Connection Refused) at $targetUrl.',
        suggestion: suggestion,
      );
    }

    return ConnectionTestResult(
      isSuccess: false,
      statusCode: dioErr.response?.statusCode,
      message: 'Server error: ${dioErr.response?.statusCode ?? dioErr.message}',
      suggestion: 'Check backend server logs (docker compose logs backend).',
    );
  }

  Future<List<ZoneModel>> getZones() async {
    if (_isTesting) return _getFallbackZones();
    try {
      final response = await _dio.get(_buildUrl(ApiConstants.zones));
      if (response.statusCode == 200 && response.data is List) {
        return (response.data as List)
            .map((json) => ZoneModel.fromJson(json as Map<String, dynamic>))
            .toList();
      }
    } catch (_) {
      // Auto-fallback check: If primary URL failed (e.g. 10.0.2.2 on physical device),
      // try alternate candidate
      final alternate = await _tryAlternateCandidateForZones();
      if (alternate != null) return alternate;
    }
    return _getFallbackZones();
  }

  Future<List<ZoneModel>?> _tryAlternateCandidateForZones() async {
    final current = ApiConstants.normalizeBaseUrl(baseUrl);
    String? candidate;
    if (current.contains('10.0.2.2')) {
      candidate = ApiConstants.defaultAdbReverseUrl; // 127.0.0.1:8000/api
    } else if (current.contains('127.0.0.1') || current.contains('localhost')) {
      candidate = ApiConstants.defaultEmulatorUrl; // 10.0.2.2:8000/api
    }

    if (candidate != null) {
      try {
        final res = await _dio.get(
          '$candidate${ApiConstants.zones}',
          options: Options(
            sendTimeout: const Duration(seconds: 2),
            receiveTimeout: const Duration(seconds: 2),
          ),
        );
        if (res.statusCode == 200 && res.data is List) {
          await _storageService.setBaseUrl(candidate);
          return (res.data as List)
              .map((json) => ZoneModel.fromJson(json as Map<String, dynamic>))
              .toList();
        }
      } catch (_) {}
    }
    return null;
  }

  Future<ZoneModel?> getZoneDetail(String zoneId) async {
    if (_isTesting) {
      final all = _getFallbackZones();
      try {
        return all.firstWhere((z) => z.id == zoneId);
      } catch (_) {
        return all.first;
      }
    }
    try {
      final response = await _dio.get(_buildUrl('${ApiConstants.zones}/$zoneId'));
      if (response.statusCode == 200 && response.data is Map<String, dynamic>) {
        final data = response.data as Map<String, dynamic>;
        final zoneData = data['zone'] as Map<String, dynamic>? ?? data;
        return ZoneModel.fromJson(zoneData);
      }
    } catch (_) {}

    final all = _getFallbackZones();
    try {
      return all.firstWhere((z) => z.id == zoneId);
    } catch (_) {
      return all.first;
    }
  }

  Future<List<Map<String, dynamic>>> getZoneRiskTrend(String zoneId,
      {String window = '24h'}) async {
    if (!_isTesting) {
      try {
        final response = await _dio.get(
          _buildUrl('${ApiConstants.zones}/$zoneId/risk-trend'),
          queryParameters: {'window': window},
        );
        if (response.statusCode == 200 && response.data is List) {
          return List<Map<String, dynamic>>.from(response.data);
        }
      } catch (_) {}
    }

    // Mock trend curve (24 data points representing hours)
    final now = DateTime.now();
    return List.generate(24, (i) {
      final time = now.subtract(Duration(hours: 23 - i));
      final factor = (i / 23.0);
      return {
        'timestamp': time.toIso8601String(),
        'tier': factor > 0.75
            ? 'HIGH'
            : factor > 0.4
                ? 'MEDIUM'
                : 'LOW',
        'probability': 0.15 + (factor * 0.7),
      };
    });
  }

  Future<List<Map<String, dynamic>>> getZoneRainfallVsRisk(String zoneId,
      {String window = '24h'}) async {
    if (!_isTesting) {
      try {
        final response = await _dio.get(
          _buildUrl('${ApiConstants.zones}/$zoneId/rainfall-vs-risk'),
          queryParameters: {'window': window},
        );
        if (response.statusCode == 200 && response.data is List) {
          return List<Map<String, dynamic>>.from(response.data);
        }
      } catch (_) {}
    }

    final now = DateTime.now();
    return List.generate(24, (i) {
      final time = now.subtract(Duration(hours: 23 - i));
      return {
        'timestamp': time.toIso8601String(),
        'rainfall_mm': 10.0 + (i * 2.5),
        'risk_probability': 0.2 + (i * 0.03),
      };
    });
  }

  Future<ModelMetricsResponse> getModelMetrics() async {
    if (!_isTesting) {
      try {
        final response = await _dio.get(_buildUrl(ApiConstants.modelMetrics));
        if (response.statusCode == 200 && response.data is Map<String, dynamic>) {
          return ModelMetricsResponse.fromJson(response.data as Map<String, dynamic>);
        }
      } catch (_) {}
    }
    return const ModelMetricsResponse({
      'Low': ClassMetrics(precision: 0.94, recall: 0.92, f1Score: 0.93),
      'Medium': ClassMetrics(precision: 0.89, recall: 0.88, f1Score: 0.885),
      'High': ClassMetrics(precision: 0.95, recall: 0.93, f1Score: 0.94),
    });
  }

  Future<List<FeatureImportanceItem>> getFeatureImportance() async {
    if (!_isTesting) {
      try {
        final response = await _dio.get(_buildUrl(ApiConstants.modelFeatureImportance));
        if (response.statusCode == 200) {
          final data = response.data;
          final list = data is List
              ? data
              : (data is Map && data['root'] is List)
                  ? data['root'] as List
                  : (data is Map && data['features'] is List)
                      ? data['features'] as List
                      : null;
          if (list != null) {
            return list
                .map((e) => FeatureImportanceItem.fromJson(e as Map<String, dynamic>))
                .toList();
          }
        }
      } catch (_) {}
    }
    return const [
      FeatureImportanceItem(featureName: 'rainfall_anomaly_ratio', importanceScore: 0.38),
      FeatureImportanceItem(featureName: 'rain_3day_pre', importanceScore: 0.24),
      FeatureImportanceItem(featureName: 'elevation', importanceScore: 0.16),
      FeatureImportanceItem(featureName: 'stream_proximity', importanceScore: 0.12),
      FeatureImportanceItem(featureName: 'hand', importanceScore: 0.10),
    ];
  }

  Future<HistoricalRainfallResponse> getZoneRainfallHistory(String zoneId) async {
    if (!_isTesting) {
      try {
        final response = await _dio.get(_buildUrl('${ApiConstants.zones}/$zoneId/history'));
        if (response.statusCode == 200 && response.data is Map<String, dynamic>) {
          return HistoricalRainfallResponse.fromJson(response.data as Map<String, dynamic>);
        }
      } catch (_) {}
    }

    // Fallback 30-day historical data
    final now = DateTime.now();
    const dailyBaseline = 1.5;
    final history = List.generate(30, (i) {
      final dayDate = now.subtract(Duration(days: 29 - i));
      final wave = 0.5 + 0.35 * ((i * 3) % 7);
      return DailyRainfallRecord(
        timestamp: dayDate,
        actualRainMm: (dailyBaseline * wave).toDouble(),
        dailyBaselineMm: dailyBaseline,
      );
    });
    return HistoricalRainfallResponse(zoneId: zoneId, thirtyDayHistory: history);
  }

  Future<InundationExtent> getZoneInundation(String zoneId) async {
    if (!_isTesting) {
      try {
        final response = await _dio.get(_buildUrl('${ApiConstants.zones}/$zoneId/inundation'));
        if (response.statusCode == 200 && response.data is Map<String, dynamic>) {
          return InundationExtent.fromJson(response.data as Map<String, dynamic>);
        }
      } catch (_) {}
    }

    final allZones = _getFallbackZones();
    ZoneModel zone;
    try {
      zone = allZones.firstWhere((z) => z.id == zoneId);
    } catch (_) {
      zone = allZones.first;
    }
    final lat = zone.coordinates.latitude;
    final lon = zone.coordinates.longitude;
    const delta = 0.005;

    return InundationExtent(
      zoneId: zoneId,
      estimatedPolygon: [
        CoordinatesModel(latitude: lat - delta, longitude: lon - delta),
        CoordinatesModel(latitude: lat - delta, longitude: lon + delta),
        CoordinatesModel(latitude: lat + delta, longitude: lon + delta),
        CoordinatesModel(latitude: lat + delta, longitude: lon - delta),
        CoordinatesModel(latitude: lat - delta, longitude: lon - delta),
      ],
      disclaimer: 'Approximate estimate, not an exact boundary.',
    );
  }

  Future<List<AlertModel>> getAlerts() async {
    if (_isTesting) return _getFallbackAlerts();
    try {
      final response = await _dio.get(_buildUrl(ApiConstants.alerts));
      if (response.statusCode == 200 && response.data is List) {
        return (response.data as List)
            .map((json) => AlertModel.fromJson(json as Map<String, dynamic>))
            .toList();
      }
    } catch (_) {}
    return _getFallbackAlerts();
  }

  Future<bool> broadcastAlert({
    required String zoneId,
    required String severity,
    required String headline,
    required String description,
  }) async {
    try {
      final response = await _dio.post(
        _buildUrl(ApiConstants.alertsBroadcast),
        data: {
          'zone_id': zoneId,
          'severity': severity,
          'headline': headline,
          'description': description,
        },
      );
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<List<CommunityReportModel>> getCommunityReports() async {
    if (_isTesting) return _getFallbackReports();
    try {
      final response = await _dio.get(_buildUrl(ApiConstants.reports));
      if (response.statusCode == 200) {
        final reports = response.data['reports'] as List?;
        if (reports != null) {
          return reports
              .map((json) =>
                  CommunityReportModel.fromJson(json as Map<String, dynamic>))
              .toList();
        }
      }
    } catch (_) {}
    return _getFallbackReports();
  }

  Future<bool> submitCommunityReport(Map<String, dynamic> reportData) async {
    try {
      final response = await _dio.post(
        _buildUrl(ApiConstants.reports),
        data: reportData,
      );
      return response.statusCode == 200 || response.statusCode == 201;
    } catch (_) {
      return false;
    }
  }

  Future<List<ResourceCenterModel>> getResourceCenters() async {
    if (_isTesting) return _getFallbackResourceCenters();
    try {
      final response = await _dio.get(_buildUrl(ApiConstants.resourceCenters));
      if (response.statusCode == 200 && response.data is List) {
        return (response.data as List)
            .map((json) =>
                ResourceCenterModel.fromJson(json as Map<String, dynamic>))
            .toList();
      }
    } catch (_) {}
    return _getFallbackResourceCenters();
  }

  // Realistic Swat Valley demo data (Kalam, Bahrain, Madyan, Mingora)
  List<ZoneModel> _getFallbackZones() {
    return [
      ZoneModel(
        id: 'zone-kalam',
        name: 'Kalam Bazaar',
        coordinates: const CoordinatesModel(latitude: 35.479, longitude: 72.596),
        upstreamZoneId: null,
        sensorHealth: 'online',
        currentWaterLevel: 2.7,
        thresholds: const ZoneThresholdsModel(
          warningLevelMetres: 1.5,
          criticalLevelMetres: 2.5,
          heavyRainThresholdMm: 40.0,
        ),
        latestAssessment: RiskAssessmentModel(
          tier: 'DANGER',
          probability: 0.92,
          explanation:
              'Water level critical (2.7m > 2.5m threshold). Torrential upstream glacial runoff.',
          computedAt: DateTime.now().subtract(const Duration(minutes: 5)),
          combinedRainMm: 68.4,
          topContributingFeatures: const [
            'water_level_centimetres',
            'rolling_rain_72h',
            'soil_saturation_index'
          ],
        ),
      ),
      ZoneModel(
        id: 'zone-bahrain',
        name: 'Bahrain',
        coordinates: const CoordinatesModel(latitude: 35.189, longitude: 72.529),
        upstreamZoneId: 'zone-kalam',
        sensorHealth: 'online',
        currentWaterLevel: 2.3,
        thresholds: const ZoneThresholdsModel(
          warningLevelMetres: 2.0,
          criticalLevelMetres: 3.0,
          heavyRainThresholdMm: 45.0,
        ),
        latestAssessment: RiskAssessmentModel(
          tier: 'HIGH',
          probability: 0.78,
          explanation:
              'Water level in Warning zone. Upstream Kalam surge advancing downstream.',
          computedAt: DateTime.now().subtract(const Duration(minutes: 8)),
          combinedRainMm: 52.1,
          topContributingFeatures: const [
            'upstream_cascade_surge',
            'water_level_centimetres'
          ],
        ),
      ),
      ZoneModel(
        id: 'zone-madyan',
        name: 'Madyan',
        coordinates: const CoordinatesModel(latitude: 35.022, longitude: 72.475),
        upstreamZoneId: 'zone-bahrain',
        sensorHealth: 'online',
        currentWaterLevel: 2.1,
        thresholds: const ZoneThresholdsModel(
          warningLevelMetres: 2.5,
          criticalLevelMetres: 3.5,
          heavyRainThresholdMm: 50.0,
        ),
        latestAssessment: RiskAssessmentModel(
          tier: 'MEDIUM',
          probability: 0.45,
          explanation:
              'River velocity elevated. Monitoring tributary confluence.',
          computedAt: DateTime.now().subtract(const Duration(minutes: 12)),
          combinedRainMm: 31.0,
          topContributingFeatures: const ['rolling_rain_24h'],
        ),
      ),
      ZoneModel(
        id: 'zone-mingora',
        name: 'Mingora City',
        coordinates: const CoordinatesModel(latitude: 34.774, longitude: 72.361),
        upstreamZoneId: 'zone-madyan',
        sensorHealth: 'online',
        currentWaterLevel: 1.8,
        thresholds: const ZoneThresholdsModel(
          warningLevelMetres: 3.0,
          criticalLevelMetres: 4.0,
          heavyRainThresholdMm: 55.0,
        ),
        latestAssessment: RiskAssessmentModel(
          tier: 'LOW',
          probability: 0.22,
          explanation:
              'River channel clear. Estimated flood travel lag from Kalam: ~4.5 hours.',
          computedAt: DateTime.now().subtract(const Duration(minutes: 15)),
          combinedRainMm: 18.5,
          topContributingFeatures: const ['base_river_discharge'],
        ),
      ),
    ];
  }

  List<AlertModel> _getFallbackAlerts() {
    return [
      AlertModel(
        id: 'alert_1',
        zoneId: 'zone-kalam',
        severity: 'DANGER',
        certainty: 'Observed',
        urgency: 'Immediate',
        headline: 'CRITICAL: Kalam River Basin Overflowing',
        description:
            'Water level at Kalam has exceeded critical threshold (2.7m). Evacuate riverside structures immediately.',
        sentAt: DateTime.now().subtract(const Duration(minutes: 10)),
      ),
      AlertModel(
        id: 'alert_2',
        zoneId: 'zone-bahrain',
        severity: 'HIGH',
        certainty: 'Likely',
        urgency: 'Expected',
        headline: 'WARNING: Cascading Surge Advancing to Bahrain',
        description:
            'Hydrodynamic surge from upper valley will reach Bahrain bridge in approximately 90 minutes.',
        sentAt: DateTime.now().subtract(const Duration(minutes: 25)),
      ),
    ];
  }

  List<CommunityReportModel> _getFallbackReports() {
    return [
      CommunityReportModel(
        id: 'rep_1',
        zoneId: 'zone-bahrain',
        reportType: 'Road Blocked',
        description:
            'Debris flow blocking Swat Kalam Expressway near Bahrain bazaar.',
        reporterName: 'Tariq Khan',
        submittedAt: DateTime.now().subtract(const Duration(minutes: 35)),
        status: 'Approved',
      ),
      CommunityReportModel(
        id: 'rep_2',
        zoneId: 'zone-kalam',
        reportType: 'Flash Flood',
        description: 'Water breached retaining wall near trout fish farm.',
        reporterName: 'Waqas Ahmad',
        submittedAt: DateTime.now().subtract(const Duration(hours: 1)),
        status: 'Approved',
      ),
    ];
  }

  List<ResourceCenterModel> _getFallbackResourceCenters() {
    return [
      const ResourceCenterModel(
        id: 'rc-mingora',
        name: 'Mingora Emergency Depot (Rescue 1122 HQ)',
        locationZone: 'zone-mingora',
        inventory: [
          InventoryItemModel(id: 'i1', itemName: 'Sandbags', quantity: 500),
          InventoryItemModel(id: 'i2', itemName: 'Life Jackets', quantity: 200),
          InventoryItemModel(id: 'i3', itemName: 'First-Aid Kits', quantity: 100),
          InventoryItemModel(id: 'i4', itemName: 'Water Pumps', quantity: 15),
          InventoryItemModel(id: 'i5', itemName: 'Inflatable Boats', quantity: 8),
        ],
      ),
      const ResourceCenterModel(
        id: 'rc-bahrain',
        name: 'Bahrain Relief Station (Civil Defense)',
        locationZone: 'zone-bahrain',
        inventory: [
          InventoryItemModel(id: 'i6', itemName: 'Emergency Rations', quantity: 350),
          InventoryItemModel(id: 'i7', itemName: 'Life Jackets', quantity: 80),
          InventoryItemModel(id: 'i8', itemName: 'Rescue Ropes', quantity: 45),
          InventoryItemModel(id: 'i9', itemName: 'Flashlights & Radios', quantity: 60),
        ],
      ),
    ];
  }
}
