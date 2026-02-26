import 'package:flutter_test/flutter_test.dart';

import 'package:alha/models/message.dart';

void main() {
  group('Message', () {
    test('default type is text', () {
      final msg = Message(
        id: '1',
        content: 'hello',
        isUser: true,
        timestamp: DateTime.now(),
      );
      expect(msg.type, MessageType.text);
    });

    test('copyWith updates content only', () {
      final original = Message(
        id: '42',
        content: 'old',
        isUser: false,
        timestamp: DateTime(2024, 1, 1),
        language: 'hi',
      );
      final copy = original.copyWith(content: 'new');
      expect(copy.content, 'new');
      expect(copy.id, '42');
      expect(copy.language, 'hi');
      expect(copy.isUser, false);
    });

    test('fromWsMessage parses error type', () {
      final msg = Message.fromWsMessage({
        'type': 'error',
        'message': 'Something went wrong',
        'message_hi': 'कुछ गड़बड़ हो गई',
      });
      expect(msg.type, MessageType.error);
      expect(msg.content, 'Something went wrong');
      expect(msg.messageHi, 'कुछ गड़बड़ हो गई');
      expect(msg.isUser, false);
    });

    test('fromWsMessage parses token type as text message', () {
      final msg = Message.fromWsMessage({
        'type': 'token',
        'text': 'Meri gaay beemar hai',
      });
      expect(msg.type, MessageType.text);
      expect(msg.content, 'Meri gaay beemar hai');
    });

    test('fromWsMessage handles missing fields gracefully', () {
      final msg = Message.fromWsMessage({'type': 'error'});
      expect(msg.content, 'Error');
      expect(msg.messageHi, isNull);
    });
  });
}
