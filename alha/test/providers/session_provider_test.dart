import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:alha/providers/session_provider.dart';
import 'package:alha/services/websocket_service.dart';

void main() {
  group('SessionNotifier', () {
    late ProviderContainer container;
    late SessionNotifier notifier;

    setUp(() {
      container = ProviderContainer();
      notifier = container.read(sessionProvider.notifier);
    });

    tearDown(() {
      container.dispose();
    });

    test('initial state has defaults', () {
      final state = container.read(sessionProvider);
      expect(state.sessionId, isNull);
      expect(state.authToken, isNull);
      expect(state.language, 'hi');
      expect(state.connectionState, WsConnectionState.disconnected);
    });

    test('setAuth stores token and sessionId', () {
      notifier.setAuth('jwt-abc', 'sess-123');
      final state = container.read(sessionProvider);
      expect(state.authToken, 'jwt-abc');
      expect(state.sessionId, 'sess-123');
    });

    test('setLanguage updates language', () {
      notifier.setLanguage('en');
      expect(container.read(sessionProvider).language, 'en');
    });

    test('setConnectionState updates connectionState', () {
      notifier.setConnectionState(WsConnectionState.connected);
      expect(
        container.read(sessionProvider).connectionState,
        WsConnectionState.connected,
      );
    });

    test('setSessionId updates sessionId without touching authToken', () {
      notifier.setAuth('my-token', 'old-sess');
      notifier.setSessionId('new-sess-uuid');
      final state = container.read(sessionProvider);
      expect(state.sessionId, 'new-sess-uuid');
      expect(state.authToken, 'my-token'); // unchanged
    });

    test('clearAuth resets to initial state', () {
      notifier.setAuth('tok', 'sid');
      notifier.clearAuth();
      final state = container.read(sessionProvider);
      expect(state.authToken, isNull);
      expect(state.sessionId, isNull);
    });

    group('detectLanguage', () {
      test('detects Hindi from Devanagari text', () {
        expect(notifier.detectLanguage('मेरी गाय बीमार है'), 'hi');
      });

      test('detects English from Latin text', () {
        expect(notifier.detectLanguage('My cow is sick'), 'en');
      });

      test('detects Hindi when mixed Devanagari present', () {
        expect(notifier.detectLanguage('My gaay is बीमार'), 'hi');
      });

      test('returns en for empty string', () {
        expect(notifier.detectLanguage(''), 'en');
      });
    });
  });
}
