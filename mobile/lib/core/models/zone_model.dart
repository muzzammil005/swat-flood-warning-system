class CoordinatesModel {
  final double latitude;
  final double longitude;

  const CoordinatesModel({
    required this.latitude,
    required this.longitude,
  });

  factory CoordinatesModel.fromJson(Map<String, dynamic> json) {
    return CoordinatesModel(
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0.0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() => {
        'latitude': latitude,
        'longitude': longitude,
      };
}

class RiskAssessmentModel {
  final String tier;
  final double probability;
  final String explanation;
  final DateTime computedAt;
  final double? combinedRainMm;
  final double? expectedRainMm;
  final double? rainfallAnomalyRatio;
  final List<String> topContributingFeatures;

  const RiskAssessmentModel({
    required this.tier,
    required this.probability,
    required this.explanation,
    required this.computedAt,
    this.combinedRainMm,
    this.expectedRainMm,
    this.rainfallAnomalyRatio,
    this.topContributingFeatures = const [],
  });

  factory RiskAssessmentModel.fromJson(Map<String, dynamic> json) {
    return RiskAssessmentModel(
      tier: (json['tier'] as String?)?.toUpperCase() ?? 'SAFE',
      probability: (json['probability'] as num?)?.toDouble() ?? 0.0,
      explanation: json['explanation'] as String? ?? 'Normal conditions',
      computedAt: json['computed_at'] != null
          ? DateTime.tryParse(json['computed_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      combinedRainMm: (json['combined_rain_mm'] as num?)?.toDouble(),
      expectedRainMm: (json['expected_rain_mm'] as num?)?.toDouble(),
      rainfallAnomalyRatio:
          (json['rainfall_anomaly_ratio'] as num?)?.toDouble(),
      topContributingFeatures: (json['top_contributing_features'] as List?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
    );
  }
}

class ZoneThresholdsModel {
  final double warningLevelMetres;
  final double criticalLevelMetres;
  final double heavyRainThresholdMm;

  const ZoneThresholdsModel({
    required this.warningLevelMetres,
    required this.criticalLevelMetres,
    required this.heavyRainThresholdMm,
  });

  factory ZoneThresholdsModel.fromJson(Map<String, dynamic> json) {
    final warningJson = json['water_warning_level'];
    final criticalJson = json['water_critical_level'];

    return ZoneThresholdsModel(
      warningLevelMetres: warningJson is Map<String, dynamic>
          ? (warningJson['metres'] as num?)?.toDouble() ?? 2.0
          : 2.0,
      criticalLevelMetres: criticalJson is Map<String, dynamic>
          ? (criticalJson['metres'] as num?)?.toDouble() ?? 3.0
          : 3.0,
      heavyRainThresholdMm:
          (json['heavy_rain_threshold_mm'] as num?)?.toDouble() ?? 45.0,
    );
  }
}

class SensorReadingModel {
  final String id;
  final String zoneId;
  final double waterLevelMetres;
  final String source;
  final DateTime timestamp;

  const SensorReadingModel({
    required this.id,
    required this.zoneId,
    required this.waterLevelMetres,
    required this.source,
    required this.timestamp,
  });

  factory SensorReadingModel.fromJson(Map<String, dynamic> json) {
    final wl = json['water_level'];
    return SensorReadingModel(
      id: json['id'] as String? ?? '',
      zoneId: json['zone_id'] as String? ?? '',
      waterLevelMetres: wl is Map<String, dynamic>
          ? (wl['metres'] as num?)?.toDouble() ?? 0.0
          : (wl as num?)?.toDouble() ?? 0.0,
      source: json['source'] as String? ?? 'sensor',
      timestamp: json['timestamp'] != null
          ? DateTime.tryParse(json['timestamp'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

class ZoneModel {
  final String id;
  final String name;
  final CoordinatesModel coordinates;
  final String? upstreamZoneId;
  final RiskAssessmentModel? latestAssessment;
  final ZoneThresholdsModel? thresholds;
  final String sensorHealth;
  final bool isManualOverride;
  final double? currentWaterLevel;
  final double? distanceMeters;

  const ZoneModel({
    required this.id,
    required this.name,
    required this.coordinates,
    this.upstreamZoneId,
    this.latestAssessment,
    this.thresholds,
    this.sensorHealth = 'online',
    this.isManualOverride = false,
    this.currentWaterLevel,
    this.distanceMeters,
  });

  String get riskTier => latestAssessment?.tier ?? 'SAFE';
  double get riskProbability => latestAssessment?.probability ?? 0.0;
  String get explanation => latestAssessment?.explanation ?? 'Normal conditions';

  bool get isWarning {
    if (thresholds == null || currentWaterLevel == null) return false;
    return currentWaterLevel! >= thresholds!.warningLevelMetres &&
        currentWaterLevel! < thresholds!.criticalLevelMetres;
  }

  bool get isCritical {
    if (thresholds == null || currentWaterLevel == null) return false;
    return currentWaterLevel! >= thresholds!.criticalLevelMetres;
  }

  factory ZoneModel.fromJson(Map<String, dynamic> json) {
    final rawCoords = json['coordinates'];
    final coords = rawCoords is Map<String, dynamic>
        ? CoordinatesModel.fromJson(rawCoords)
        : const CoordinatesModel(latitude: 35.2, longitude: 72.4);

    return ZoneModel(
      id: json['id'] as String? ?? json['zone_id'] as String? ?? '',
      name: json['name'] as String? ?? json['zone_name'] as String? ?? 'Zone',
      coordinates: coords,
      upstreamZoneId: json['upstream_zone_id'] as String?,
      latestAssessment: json['latest_assessment'] != null
          ? RiskAssessmentModel.fromJson(
              json['latest_assessment'] as Map<String, dynamic>)
          : null,
      thresholds: json['thresholds'] != null
          ? ZoneThresholdsModel.fromJson(
              json['thresholds'] as Map<String, dynamic>)
          : null,
      sensorHealth: json['sensor_health'] as String? ?? 'online',
      isManualOverride: json['is_manual_override'] as bool? ?? false,
      currentWaterLevel: (json['current_water_level'] as num?)?.toDouble() ??
          (json['latest_sensor_reading']?['water_level']?['metres'] as num?)
              ?.toDouble(),
      distanceMeters: (json['distance_meters'] as num?)?.toDouble(),
    );
  }

  ZoneModel copyWith({
    double? currentWaterLevel,
    double? distanceMeters,
    RiskAssessmentModel? latestAssessment,
  }) {
    return ZoneModel(
      id: id,
      name: name,
      coordinates: coordinates,
      upstreamZoneId: upstreamZoneId,
      latestAssessment: latestAssessment ?? this.latestAssessment,
      thresholds: thresholds,
      sensorHealth: sensorHealth,
      isManualOverride: isManualOverride,
      currentWaterLevel: currentWaterLevel ?? this.currentWaterLevel,
      distanceMeters: distanceMeters ?? this.distanceMeters,
    );
  }
}
