import 'package:latlong2/latlong.dart';
import 'zone_model.dart';

class ClassMetrics {
  final double precision;
  final double recall;
  final double f1Score;

  const ClassMetrics({
    required this.precision,
    required this.recall,
    required this.f1Score,
  });

  factory ClassMetrics.fromJson(Map<String, dynamic> json) {
    return ClassMetrics(
      precision: (json['precision'] as num?)?.toDouble() ?? 0.0,
      recall: (json['recall'] as num?)?.toDouble() ?? 0.0,
      f1Score: (json['f1_score'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() => {
        'precision': precision,
        'recall': recall,
        'f1_score': f1Score,
      };
}

class ModelMetricsResponse {
  final Map<String, ClassMetrics> metrics;

  const ModelMetricsResponse(this.metrics);

  factory ModelMetricsResponse.fromJson(Map<String, dynamic> json) {
    final raw = json['root'] is Map<String, dynamic>
        ? json['root'] as Map<String, dynamic>
        : json;
    final map = <String, ClassMetrics>{};
    raw.forEach((key, value) {
      if (value is Map<String, dynamic>) {
        map[key] = ClassMetrics.fromJson(value);
      }
    });
    return ModelMetricsResponse(map);
  }

  ClassMetrics? get low => metrics['Low'] ?? metrics['LOW'];
  ClassMetrics? get medium => metrics['Medium'] ?? metrics['MEDIUM'];
  ClassMetrics? get high => metrics['High'] ?? metrics['HIGH'];
}

class FeatureImportanceItem {
  final String featureName;
  final double importanceScore;

  const FeatureImportanceItem({
    required this.featureName,
    required this.importanceScore,
  });

  factory FeatureImportanceItem.fromJson(Map<String, dynamic> json) {
    return FeatureImportanceItem(
      featureName: json['feature_name'] as String? ?? '',
      importanceScore: (json['importance_score'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() => {
        'feature_name': featureName,
        'importance_score': importanceScore,
      };
}

class DailyRainfallRecord {
  final DateTime timestamp;
  final double actualRainMm;
  final double dailyBaselineMm;

  const DailyRainfallRecord({
    required this.timestamp,
    required this.actualRainMm,
    required this.dailyBaselineMm,
  });

  factory DailyRainfallRecord.fromJson(Map<String, dynamic> json) {
    return DailyRainfallRecord(
      timestamp: DateTime.tryParse(json['timestamp']?.toString() ?? '') ??
          DateTime.now(),
      actualRainMm: (json['actual_rain_mm'] as num?)?.toDouble() ?? 0.0,
      dailyBaselineMm: (json['daily_baseline_mm'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() => {
        'timestamp': timestamp.toIso8601String(),
        'actual_rain_mm': actualRainMm,
        'daily_baseline_mm': dailyBaselineMm,
      };
}

class HistoricalRainfallResponse {
  final String zoneId;
  final List<DailyRainfallRecord> thirtyDayHistory;

  const HistoricalRainfallResponse({
    required this.zoneId,
    required this.thirtyDayHistory,
  });

  List<DailyRainfallRecord> get history => thirtyDayHistory;

  factory HistoricalRainfallResponse.fromJson(Map<String, dynamic> json) {
    final list = (json['thirty_day_history'] ?? json['history']) as List? ?? [];
    return HistoricalRainfallResponse(
      zoneId: json['zone_id'] as String? ?? '',
      thirtyDayHistory: list
          .map((e) => DailyRainfallRecord.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class InundationExtent {
  final String zoneId;
  final List<CoordinatesModel> estimatedPolygon;
  final String disclaimer;

  const InundationExtent({
    required this.zoneId,
    required this.estimatedPolygon,
    required this.disclaimer,
  });

  List<LatLng> toLatLngList() {
    return estimatedPolygon
        .map((c) => LatLng(c.latitude, c.longitude))
        .toList();
  }

  factory InundationExtent.fromJson(Map<String, dynamic> json) {
    final poly = json['estimated_polygon'] as List? ?? [];
    final coords = <CoordinatesModel>[];
    for (final item in poly) {
      if (item is Map<String, dynamic>) {
        coords.add(CoordinatesModel.fromJson(item));
      } else if (item is List && item.length >= 2) {
        coords.add(CoordinatesModel(
          latitude: (item[0] as num).toDouble(),
          longitude: (item[1] as num).toDouble(),
        ));
      }
    }

    return InundationExtent(
      zoneId: json['zone_id'] as String? ?? '',
      estimatedPolygon: coords,
      disclaimer: json['disclaimer'] as String? ??
          'Approximate estimate, not an exact boundary.',
    );
  }
}
