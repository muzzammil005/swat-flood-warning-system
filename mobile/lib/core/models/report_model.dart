class CommunityReportModel {
  final String id;
  final String zoneId;
  final String reportType;
  final String description;
  final String? reporterName;
  final String? reporterPhone;
  final double? latitude;
  final double? longitude;
  final DateTime submittedAt;
  final String status;
  final String? adminNotes;

  const CommunityReportModel({
    required this.id,
    required this.zoneId,
    required this.reportType,
    required this.description,
    this.reporterName,
    this.reporterPhone,
    this.latitude,
    this.longitude,
    required this.submittedAt,
    required this.status,
    this.adminNotes,
  });

  factory CommunityReportModel.fromJson(Map<String, dynamic> json) {
    return CommunityReportModel(
      id: json['id'] as String? ?? 'rep_${DateTime.now().millisecondsSinceEpoch}',
      zoneId: json['zone_id'] as String? ?? '',
      reportType: json['report_type'] as String? ?? 'General Observation',
      description: json['description'] as String? ?? '',
      reporterName: json['reporter_name'] as String?,
      reporterPhone: json['reporter_phone'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      submittedAt: json['submitted_at'] != null
          ? DateTime.tryParse(json['submitted_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      status: json['status'] as String? ?? 'Pending',
      adminNotes: json['admin_notes'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'zone_id': zoneId,
        'report_type': reportType,
        'description': description,
        'reporter_name': reporterName,
        'reporter_phone': reporterPhone,
        'latitude': latitude,
        'longitude': longitude,
      };
}
