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
  final bool sessionComplete;

  const ChatState({
    this.messages = const [],
    this.isStreaming = false,
    this.currentStreamingText = '',
    this.sessionComplete = false,
  });

  ChatState copyWith({
    List<Message>? messages,
    bool? isStreaming,
    String? currentStreamingText,
    bool? sessionComplete,
  }) =>
      ChatState(
        messages: messages ?? this.messages,
        isStreaming: isStreaming ?? this.isStreaming,
        currentStreamingText: currentStreamingText ?? this.currentStreamingText,
        sessionComplete: sessionComplete ?? this.sessionComplete,
      );
}

class ChatNotifier extends StateNotifier<ChatState> {
  ChatNotifier() : super(const ChatState());

  // Callback set by ChatScreen so notifier can send WS messages
  void Function(Map<String, dynamic>)? _wsSendFn;

  // Guards to prevent duplicate overlay triggers when rapid WS messages arrive
  bool _symptomInterviewPending = false;
  bool _cameraOverlayPending = false;
  bool _gpsRequestPending = false;
  bool _vetPreferencePending = false;

  // Tracks the latest severity level to gate vet preference card (AC #2, #6).
  // CRITICAL auto-escalates — no vet preference card is shown.
  // HIGH or MEDIUM — vet preference card is shown after vet_found.
  String _lastSeverity = '';

  // Streams for overlay/action triggers
  final _symptomInterviewController =
      StreamController<SymptomInterviewEvent>.broadcast();
  final _cameraOverlayController = StreamController<void>.broadcast();
  final _gpsRequestController = StreamController<void>.broadcast();
  final _vetPreferenceController = StreamController<void>.broadcast();

  Stream<SymptomInterviewEvent> get symptomInterviewTrigger =>
      _symptomInterviewController.stream;
  Stream<void> get cameraOverlayTrigger => _cameraOverlayController.stream;
  Stream<void> get gpsRequestTrigger => _gpsRequestController.stream;
  Stream<void> get vetPreferenceTrigger => _vetPreferenceController.stream;

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
    _finalizeStreamingText();
    final msg = Message.systemMessage(text);
    state = state.copyWith(messages: [...state.messages, msg]);
  }

  /// Finalizes the current streaming text so subsequent tokens start a fresh
  /// message. Call this before inserting any non-text message (severity, vet
  /// card, system message) to prevent the accumulated text from being repeated
  /// in a new bubble after the interruption.
  void _finalizeStreamingText() {
    if (state.currentStreamingText.isNotEmpty) {
      state = state.copyWith(currentStreamingText: '');
    }
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
      case 'severity':
        _handleSeverity(json);
      case 'vet_found':
        _handleVetFound(json);
      case 'notification_sent':
        _handleNotificationSent(json);
      case 'session_complete':
        _handleSessionComplete(json);
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
      case 'request_gps':
        if (_gpsRequestPending) return;
        _gpsRequestPending = true;
        if (!_gpsRequestController.isClosed) {
          _gpsRequestController.add(null);
        }
    }
  }

  void clearSymptomInterviewPending() => _symptomInterviewPending = false;
  void clearCameraOverlayPending() => _cameraOverlayPending = false;
  void clearGpsRequestPending() => _gpsRequestPending = false;
  void clearVetPreferencePending() => _vetPreferencePending = false;

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

    _finalizeStreamingText();
    final diagMsg = Message.fromDiagnosisWs(json);
    state = state.copyWith(
      messages: [...state.messages, diagMsg],
      isStreaming: false,
    );
  }

  void _handleSeverity(Map<String, dynamic> json) {
    final level = json['level'] as String? ?? 'NONE';
    _lastSeverity = level.toUpperCase();
    _finalizeStreamingText();
    final msg = Message.severity(level);
    state = state.copyWith(messages: [...state.messages, msg]);
  }

  void _handleVetFound(Map<String, dynamic> json) {
    _finalizeStreamingText();
    final vet = VetData.fromJson(json);
    final msg = Message.vetFound(vet);
    state = state.copyWith(messages: [...state.messages, msg]);
    // AC #2: CRITICAL auto-escalates — no vet preference card.
    // AC #6: HIGH or MEDIUM show vet preference card after vet_found.
    final showPreference = _lastSeverity == 'HIGH' || _lastSeverity == 'MEDIUM';
    if (showPreference && !_vetPreferencePending && !_vetPreferenceController.isClosed) {
      _vetPreferencePending = true;
      _vetPreferenceController.add(null);
    }
  }

  void _handleNotificationSent(Map<String, dynamic> json) {
    final vetName = json['vet_name'] as String? ?? 'the vet';
    _addSystemMessage(
      'SMS sent to $vetName and you. / आपको और $vetName को SMS भेजा गया।',
    );
  }

  void _handleSessionComplete(Map<String, dynamic> json) {
    _addSystemMessage('Consultation complete. / परामर्श पूरा हुआ।');
    state = state.copyWith(sessionComplete: true);
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

  void sendGpsData(double lat, double lon, String sessionId) {
    _addSystemMessage('Sharing location... / स्थान साझा हो रहा है...');
    _wsSendFn?.call({
      'type': 'gps_data',
      'lat': lat,
      'lon': lon,
      'session_id': sessionId,
    });
    clearGpsRequestPending();
  }

  void sendVetPreference(String choice, String sessionId) {
    final display = choice == 'yes'
        ? 'Yes, connect me / हाँ, जोड़ें'
        : 'No, thank you / नहीं, धन्यवाद';
    final msg = Message(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: display,
      isUser: true,
      timestamp: DateTime.now(),
    );
    state = state.copyWith(
      messages: [...state.messages, msg],
      isStreaming: true,
      currentStreamingText: '',
    );
    _wsSendFn?.call({
      'type': 'vet_preference',
      'choice': choice,
      'session_id': sessionId,
    });
    clearVetPreferencePending();
  }

  void clearMessages() {
    state = const ChatState();
  }

  @override
  void dispose() {
    _symptomInterviewController.close();
    _cameraOverlayController.close();
    _gpsRequestController.close();
    _vetPreferenceController.close();
    super.dispose();
  }
}

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>(
  (ref) => ChatNotifier(),
);
