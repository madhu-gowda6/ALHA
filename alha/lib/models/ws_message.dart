class WsMessage {
  final String type;
  final String sessionId;
  final Map<String, dynamic>? payload;

  const WsMessage({
    required this.type,
    required this.sessionId,
    this.payload,
  });

  factory WsMessage.fromJson(Map<String, dynamic> json) => WsMessage(
        type: json['type'] as String,
        sessionId: json['session_id'] as String,
        payload: json['payload'] as Map<String, dynamic>?,
      );

  Map<String, dynamic> toJson() => {
        'type': type,
        'session_id': sessionId,
        if (payload != null) 'payload': payload,
      };
}
