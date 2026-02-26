import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/message.dart';

class ChatState {
  final List<Message> messages;
  final bool isStreaming;
  final String currentStreamingText;

  const ChatState({
    this.messages = const [],
    this.isStreaming = false,
    this.currentStreamingText = '',
  });

  ChatState copyWith({
    List<Message>? messages,
    bool? isStreaming,
    String? currentStreamingText,
  }) =>
      ChatState(
        messages: messages ?? this.messages,
        isStreaming: isStreaming ?? this.isStreaming,
        currentStreamingText: currentStreamingText ?? this.currentStreamingText,
      );
}

class ChatNotifier extends StateNotifier<ChatState> {
  ChatNotifier() : super(const ChatState());

  void addUserMessage(String text, {String language = 'en'}) {
    final msg = Message(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: text,
      isUser: true,
      timestamp: DateTime.now(),
      language: language,
    );
    state = state.copyWith(
      messages: [...state.messages, msg],
      isStreaming: true,
      currentStreamingText: '',
    );
  }

  void handleToken(String text) {
    final newText = state.currentStreamingText + text;
    final msgs = List<Message>.from(state.messages);

    if (msgs.isNotEmpty && !msgs.last.isUser && msgs.last.type == MessageType.text) {
      msgs[msgs.length - 1] = msgs.last.copyWith(content: newText);
    } else {
      msgs.add(Message(
        id: 'streaming_${DateTime.now().millisecondsSinceEpoch}',
        content: newText,
        isUser: false,
        timestamp: DateTime.now(),
      ));
    }

    state = state.copyWith(messages: msgs, currentStreamingText: newText);
  }

  void handleResponseComplete() {
    state = state.copyWith(isStreaming: false, currentStreamingText: '');
  }

  void handleError(String message, String? messageHi) {
    final errorContent = messageHi != null ? '$message\n$messageHi' : message;
    final msg = Message(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: errorContent,
      isUser: false,
      timestamp: DateTime.now(),
      type: MessageType.error,
      messageHi: messageHi,
    );
    state = state.copyWith(
      messages: [...state.messages, msg],
      isStreaming: false,
      currentStreamingText: '',
    );
  }

  void handleWsMessage(Map<String, dynamic> json) {
    final type = json['type'] as String? ?? '';
    switch (type) {
      case 'token':
        handleToken(json['text'] as String? ?? '');
      case 'response_complete':
        handleResponseComplete();
      case 'error':
        handleError(
          json['message'] as String? ?? 'Error',
          json['message_hi'] as String?,
        );
    }
  }

  void clearMessages() {
    state = const ChatState();
  }
}

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>(
  (ref) => ChatNotifier(),
);
