enum MessageType { text, image, error, system, typing, diagnosis }

class BboxData {
  final double left;
  final double top;
  final double width;
  final double height;

  const BboxData({
    required this.left,
    required this.top,
    required this.width,
    required this.height,
  });

  factory BboxData.fromJson(Map<String, dynamic> json) => BboxData(
        left: (json['left'] as num?)?.toDouble() ?? 0.0,
        top: (json['top'] as num?)?.toDouble() ?? 0.0,
        width: (json['width'] as num?)?.toDouble() ?? 0.0,
        height: (json['height'] as num?)?.toDouble() ?? 0.0,
      );
}

class DiagnosisData {
  final String? disease;
  final double confidence;
  final BboxData? bbox;
  final String s3Key;

  const DiagnosisData({
    required this.disease,
    required this.confidence,
    required this.bbox,
    required this.s3Key,
  });

  factory DiagnosisData.fromJson(Map<String, dynamic> json) => DiagnosisData(
        disease: json['disease'] as String?,
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
        bbox: json['bbox'] != null
            ? BboxData.fromJson(json['bbox'] as Map<String, dynamic>)
            : null,
        s3Key: json['s3_key'] as String? ?? '',
      );
}

class Message {
  final String id;
  final String content;
  final bool isUser;
  final DateTime timestamp;
  final MessageType type;
  final String? language;
  final String? messageHi;
  final String? imageUrl;
  final DiagnosisData? diagnosisData;

  const Message({
    required this.id,
    required this.content,
    required this.isUser,
    required this.timestamp,
    this.type = MessageType.text,
    this.language,
    this.messageHi,
    this.imageUrl,
    this.diagnosisData,
  });

  Message copyWith({String? content}) => Message(
        id: id,
        content: content ?? this.content,
        isUser: isUser,
        timestamp: timestamp,
        type: type,
        language: language,
        messageHi: messageHi,
        imageUrl: imageUrl,
        diagnosisData: diagnosisData,
      );

  factory Message.fromWsMessage(Map<String, dynamic> json) {
    final msgType = json['type'] as String? ?? '';
    switch (msgType) {
      case 'error':
        return Message(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          content: json['message'] as String? ?? 'Error',
          isUser: false,
          timestamp: DateTime.now(),
          type: MessageType.error,
          messageHi: json['message_hi'] as String?,
        );
      default:
        return Message(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          content: json['text'] as String? ?? '',
          isUser: false,
          timestamp: DateTime.now(),
          type: MessageType.text,
        );
    }
  }

  factory Message.fromDiagnosisWs(Map<String, dynamic> json) => Message(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        content: json['disease'] as String? ?? '',
        isUser: false,
        timestamp: DateTime.now(),
        type: MessageType.diagnosis,
        diagnosisData: DiagnosisData.fromJson(json),
      );
}
