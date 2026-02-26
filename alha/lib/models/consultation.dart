class Consultation {
  final String sessionId;
  final String farmerPhone;
  final String animalType;
  final String? diseaseName;
  final double? confidenceScore;
  final String? severity;
  final String? treatmentSummary;
  final String timestamp;

  const Consultation({
    required this.sessionId,
    required this.farmerPhone,
    required this.animalType,
    this.diseaseName,
    this.confidenceScore,
    this.severity,
    this.treatmentSummary,
    required this.timestamp,
  });

  factory Consultation.fromJson(Map<String, dynamic> json) => Consultation(
        sessionId: json['session_id'] as String,
        farmerPhone: json['farmer_phone'] as String,
        animalType: json['animal_type'] as String,
        diseaseName: json['disease_name'] as String?,
        confidenceScore: (json['confidence_score'] as num?)?.toDouble(),
        severity: json['severity'] as String?,
        treatmentSummary: json['treatment_summary'] as String?,
        timestamp: json['timestamp'] as String,
      );
}
