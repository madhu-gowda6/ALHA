enum MessageType { text, image, error, system, typing }

class Message {
  final String id;
  final String content;
  final bool isUser;
  final DateTime timestamp;
  final MessageType type;
  final String? language;
  final String? messageHi;
  final String? imageUrl;

  const Message({
    required this.id,
    required this.content,
    required this.isUser,
    required this.timestamp,
    this.type = MessageType.text,
    this.language,
    this.messageHi,
    this.imageUrl,
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
}
