import 'package:flutter_test/flutter_test.dart';

import 'package:alha/services/websocket_service.dart';

void main() {
  group('WebSocketService', () {
    test('initial connectionState is disconnected', () {
      final service = WebSocketService();
      expect(service.connectionState, WsConnectionState.disconnected);
      service.dispose();
    });

    test('disconnect sets state to disconnected', () {
      final service = WebSocketService();
      service.disconnect();
      expect(service.connectionState, WsConnectionState.disconnected);
      service.dispose();
    });

    test('send does nothing when not connected', () {
      // Should not throw when sending while disconnected
      final service = WebSocketService();
      expect(
        () => service.send({'type': 'chat', 'message': 'hello'}),
        returnsNormally,
      );
      service.dispose();
    });

    test('messages stream is broadcast (multiple listeners allowed)', () async {
      final service = WebSocketService();
      final stream = service.messages;
      final sub1 = stream.listen((_) {});
      final sub2 = stream.listen((_) {});
      // Both subscriptions should not throw
      await sub1.cancel();
      await sub2.cancel();
      service.dispose();
    });

    test('connectionStateStream is broadcast', () async {
      final service = WebSocketService();
      final stream = service.connectionStateStream;
      final sub1 = stream.listen((_) {});
      final sub2 = stream.listen((_) {});
      await sub1.cancel();
      await sub2.cancel();
      service.dispose();
    });

    test('dispose closes streams without error', () {
      final service = WebSocketService();
      expect(() => service.dispose(), returnsNormally);
    });

    test('WsConnectionState enum has all expected values', () {
      expect(WsConnectionState.values, contains(WsConnectionState.disconnected));
      expect(WsConnectionState.values, contains(WsConnectionState.connecting));
      expect(WsConnectionState.values, contains(WsConnectionState.connected));
      expect(WsConnectionState.values, contains(WsConnectionState.reconnecting));
    });
  });
}
