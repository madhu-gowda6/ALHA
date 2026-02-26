import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:alha/providers/chat_provider.dart';
import 'package:alha/models/message.dart';

void main() {
  group('ChatNotifier', () {
    late ProviderContainer container;
    late ChatNotifier notifier;

    setUp(() {
      container = ProviderContainer();
      notifier = container.read(chatProvider.notifier);
    });

    tearDown(() {
      container.dispose();
    });

    test('initial state has empty messages', () {
      expect(container.read(chatProvider).messages, isEmpty);
      expect(container.read(chatProvider).isStreaming, false);
    });

    test('addUserMessage appends a user message and starts streaming', () {
      notifier.addUserMessage('Meri gaay beemar hai', language: 'hi');
      final state = container.read(chatProvider);
      expect(state.messages.length, 1);
      expect(state.messages.first.isUser, true);
      expect(state.messages.first.content, 'Meri gaay beemar hai');
      expect(state.messages.first.language, 'hi');
      expect(state.isStreaming, true);
    });

    test('handleToken accumulates tokens into a streaming bubble', () {
      notifier.addUserMessage('test');
      notifier.handleToken('Hello');
      notifier.handleToken(' world');
      final state = container.read(chatProvider);
      // One user message + one streaming AI message
      expect(state.messages.length, 2);
      expect(state.messages.last.isUser, false);
      expect(state.messages.last.content, 'Hello world');
      expect(state.currentStreamingText, 'Hello world');
    });

    test('handleResponseComplete clears streaming flag', () {
      notifier.addUserMessage('test');
      notifier.handleToken('Some text');
      notifier.handleResponseComplete();
      final state = container.read(chatProvider);
      expect(state.isStreaming, false);
      expect(state.currentStreamingText, '');
    });

    test('handleError appends an error message', () {
      notifier.handleError('Something failed', 'कुछ गड़बड़ हो गई');
      final state = container.read(chatProvider);
      expect(state.messages.length, 1);
      expect(state.messages.first.type, MessageType.error);
      expect(state.messages.first.messageHi, 'कुछ गड़बड़ हो गई');
      expect(state.isStreaming, false);
    });

    test('handleWsMessage dispatches token type', () {
      notifier.addUserMessage('test');
      notifier.handleWsMessage({'type': 'token', 'text': 'Hello'});
      expect(container.read(chatProvider).messages.last.content, 'Hello');
    });

    test('handleWsMessage dispatches response_complete', () {
      notifier.addUserMessage('test');
      notifier.handleToken('data');
      notifier.handleWsMessage({'type': 'response_complete'});
      expect(container.read(chatProvider).isStreaming, false);
    });

    test('handleWsMessage dispatches error type', () {
      notifier.handleWsMessage({
        'type': 'error',
        'message': 'Error occurred',
        'message_hi': 'त्रुटि हुई',
      });
      final state = container.read(chatProvider);
      expect(state.messages.last.type, MessageType.error);
    });

    test('clearMessages resets state to empty', () {
      notifier.addUserMessage('test1');
      notifier.addUserMessage('test2');
      notifier.clearMessages();
      expect(container.read(chatProvider).messages, isEmpty);
    });
  });
}
