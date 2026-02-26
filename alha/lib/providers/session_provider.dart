import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/websocket_service.dart';

class SessionState {
  final String? sessionId;
  final String? authToken;
  final String language;
  final WsConnectionState connectionState;

  const SessionState({
    this.sessionId,
    this.authToken,
    this.language = 'hi',
    this.connectionState = WsConnectionState.disconnected,
  });

  SessionState copyWith({
    String? sessionId,
    String? authToken,
    String? language,
    WsConnectionState? connectionState,
  }) =>
      SessionState(
        sessionId: sessionId ?? this.sessionId,
        authToken: authToken ?? this.authToken,
        language: language ?? this.language,
        connectionState: connectionState ?? this.connectionState,
      );
}

class SessionNotifier extends StateNotifier<SessionState> {
  SessionNotifier() : super(const SessionState());

  void setAuth(String token, String sessionId) {
    state = state.copyWith(authToken: token, sessionId: sessionId);
  }

  void setLanguage(String language) {
    state = state.copyWith(language: language);
  }

  void setConnectionState(WsConnectionState wsState) {
    state = state.copyWith(connectionState: wsState);
  }

  /// Auto-detect language from message content.
  /// If message contains Devanagari characters → "hi", else "en".
  String detectLanguage(String message) {
    final devanagariRange = RegExp(r'[\u0900-\u097F]');
    return devanagariRange.hasMatch(message) ? 'hi' : 'en';
  }

  void clearAuth() {
    state = const SessionState();
  }
}

final sessionProvider = StateNotifierProvider<SessionNotifier, SessionState>(
  (ref) => SessionNotifier(),
);
