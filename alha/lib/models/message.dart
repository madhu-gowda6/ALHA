class Message {
  final String id;
  final String content;
  final bool isUser;
  final DateTime timestamp;
  final String? imageUrl;

  const Message({
    required this.id,
    required this.content,
    required this.isUser,
    required this.timestamp,
    this.imageUrl,
  });
}
