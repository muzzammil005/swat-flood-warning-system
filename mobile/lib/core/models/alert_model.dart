class AlertModel {
  final String id;
  final String zoneId;
  final String severity;
  final String certainty;
  final String urgency;
  final String headline;
  final String description;
  final DateTime sentAt;

  const AlertModel({
    required this.id,
    required this.zoneId,
    required this.severity,
    required this.certainty,
    required this.urgency,
    required this.headline,
    required this.description,
    required this.sentAt,
  });

  bool get isCritical => severity.toUpperCase() == 'DANGER';

  factory AlertModel.fromJson(Map<String, dynamic> json) {
    return AlertModel(
      id: json['id'] as String? ?? 'alert_${DateTime.now().millisecondsSinceEpoch}',
      zoneId: json['zone_id'] as String? ?? '',
      severity: (json['severity'] as String?)?.toUpperCase() ?? 'INFO',
      certainty: json['certainty'] as String? ?? 'Observed',
      urgency: json['urgency'] as String? ?? 'Immediate',
      headline: json['headline'] as String? ?? 'Flood Alert',
      description: json['description'] as String? ?? '',
      sentAt: json['sent_at'] != null
          ? DateTime.tryParse(json['sent_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'zone_id': zoneId,
        'severity': severity,
        'certainty': certainty,
        'urgency': urgency,
        'headline': headline,
        'description': description,
        'sent_at': sentAt.toIso8601String(),
      };
}
