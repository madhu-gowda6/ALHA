class Consultation {
  final String sessionId;
  final String farmerPhone;
  final String animalType;
  final String? diseaseName;
  final double? confidenceScore;
  final String? severity;
  final String? vetAssigned;
  final String? vetPhone;
  final String? treatmentSummary;
  final String? kbCitations;
  final String timestamp;

  const Consultation({
    required this.sessionId,
    required this.farmerPhone,
    required this.animalType,
    this.diseaseName,
    this.confidenceScore,
    this.severity,
    this.vetAssigned,
    this.vetPhone,
    this.treatmentSummary,
    this.kbCitations,
    required this.timestamp,
  });

  factory Consultation.fromJson(Map<String, dynamic> json) => Consultation(
        sessionId: json['session_id'] as String? ?? json['consultation_id'] as String? ?? '',
        farmerPhone: json['farmer_phone'] as String? ?? '',
        animalType: json['animal_type'] as String? ?? '',
        diseaseName: json['disease_name'] as String?,
        confidenceScore: (json['confidence_score'] as num?)?.toDouble(),
        severity: json['severity'] as String?,
        vetAssigned: json['vet_assigned'] as String?,
        vetPhone: json['vet_phone'] as String?,
        treatmentSummary: json['treatment_summary'] as String?,
        kbCitations: json['kb_citations'] as String?,
        timestamp: json['timestamp'] as String? ?? '',
      );
}
