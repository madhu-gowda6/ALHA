import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/message.dart';

class SymptomInterviewEvent {
  final List<String> questions;
  final List<String> questionsHi;

  const SymptomInterviewEvent({
    required this.questions,
    required this.questionsHi,
  });
}

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

  // Callback set by ChatScreen so notifier can send WS messages
  void Function(Map<String, dynamic>)? _wsSendFn;

  // Guards to prevent duplicate overlay triggers when rapid WS messages arrive
  bool _symptomInterviewPending = false;
  bool _cameraOverlayPending = false;

  // Streams for overlay triggers
  final _symptomInterviewController =
      StreamController<SymptomInterviewEvent>.broadcast();
  final _cameraOverlayController = StreamController<void>.broadcast();

  Stream<SymptomInterviewEvent> get symptomInterviewTrigger =>
      _symptomInterviewController.stream;
  Stream<void> get cameraOverlayTrigger => _cameraOverlayController.stream;

  void setWsSendFn(void Function(Map<String, dynamic>) fn) {
    _wsSendFn = fn;
  }

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

    if (msgs.isNotEmpty &&
        !msgs.last.isUser &&
        msgs.last.type == MessageType.text) {
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

  void _addSystemMessage(String text) {
    final msg = Message(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: text,
      isUser: false,
      timestamp: DateTime.now(),
      type: MessageType.system,
    );
    state = state.copyWith(messages: [...state.messages, msg]);
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
      case 'frontend_action':
        _handleFrontendAction(json);
      case 'diagnosis':
        _handleDiagnosis(json);
    }
  }

  void _handleFrontendAction(Map<String, dynamic> json) {
    final action = json['action'] as String? ?? '';
    switch (action) {
      case 'symptom_interview':
        if (_symptomInterviewPending) return;
        _symptomInterviewPending = true;
        final questions = (json['questions'] as List?)
                ?.map((e) => e as String)
                .toList() ??
            [];
        final questionsHi = (json['questions_hi'] as List?)
                ?.map((e) => e as String)
                .toList() ??
            [];
        if (!_symptomInterviewController.isClosed) {
          _symptomInterviewController.add(SymptomInterviewEvent(
            questions: questions,
            questionsHi: questionsHi,
          ));
        }
      case 'request_image':
        if (_cameraOverlayPending) return;
        _cameraOverlayPending = true;
        if (!_cameraOverlayController.isClosed) {
          _cameraOverlayController.add(null);
        }
    }
  }

  void clearSymptomInterviewPending() => _symptomInterviewPending = false;
  void clearCameraOverlayPending() => _cameraOverlayPending = false;

  void _handleDiagnosis(Map<String, dynamic> json) {
    final softFailure = json['soft_failure'] as bool? ?? false;
    if (softFailure) {
      final msg =
          json['message'] as String? ?? 'Photo not clear. Please try again.';
      final msgHi = json['message_hi'] as String?;
      handleError(msg, msgHi);
      // Re-trigger camera overlay for retry (clear pending so it actually shows)
      _cameraOverlayPending = false;
      if (!_cameraOverlayController.isClosed) {
        _cameraOverlayController.add(null);
        _cameraOverlayPending = true;
      }
      return;
    }

    final diagMsg = Message.fromDiagnosisWs(json);
    state = state.copyWith(
      messages: [...state.messages, diagMsg],
      isStreaming: false,
    );
  }

  void sendImageData(String s3Key, String sessionId) {
    _addSystemMessage('Analyzing image... / छवि का विश्लेषण हो रहा है...');
    _wsSendFn?.call({
      'type': 'image_data',
      's3_key': s3Key,
      'session_id': sessionId,
    });
  }

  void sendSymptomAnswers(
      List<Map<String, String>> answers, String sessionId) {
    // Add a summary bubble showing the farmer's answers
    final summary = answers
        .map((a) => 'Q: ${a['question']}\nA: ${a['answer']}')
        .join('\n\n');
    final msg = Message(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: summary,
      isUser: true,
      timestamp: DateTime.now(),
    );
    state = state.copyWith(
      messages: [...state.messages, msg],
      isStreaming: true,
      currentStreamingText: '',
    );

    _wsSendFn?.call({
      'type': 'symptom_answers',
      'session_id': sessionId,
      'answers': answers,
    });
  }

  void clearMessages() {
    state = const ChatState();
  }

  @override
  void dispose() {
    _symptomInterviewController.close();
    _cameraOverlayController.close();
    super.dispose();
  }
}

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>(
  (ref) => ChatNotifier(),
);
