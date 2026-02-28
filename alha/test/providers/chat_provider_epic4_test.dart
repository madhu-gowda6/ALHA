/// Epic 4 additions to ChatProvider:
/// severity, vet_found, notification_sent, session_complete WS handlers,
/// sendGpsData, sendVetPreference methods, and new trigger streams.
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:alha/models/message.dart';
import 'package:alha/providers/chat_provider.dart';

void main() {
  group('ChatProvider Epic 4 — VetData model', () {
    test('VetData.fromJson parses all fields', () {
      final vet = VetData.fromJson({
        'name': 'Dr. Ramesh Patel',
        'speciality': 'cattle',
        'distance_km': 3.7,
        'phone': '+919876543210',
      });
      expect(vet.name, 'Dr. Ramesh Patel');
      expect(vet.speciality, 'cattle');
      expect(vet.distanceKm, closeTo(3.7, 0.001));
      expect(vet.phone, '+919876543210');
    });

    test('VetData.fromJson uses defaults for missing fields', () {
      final vet = VetData.fromJson({});
      expect(vet.name, '');
      expect(vet.speciality, '');
      expect(vet.distanceKm, 0.0);
      expect(vet.phone, '');
    });

    test('Message.vetFound builds vetFound type with VetData attached', () {
      final vet = VetData.fromJson({
        'name': 'Dr. Test',
        'speciality': 'poultry',
        'distance_km': 1.2,
        'phone': '+91000',
      });
      final msg = Message.vetFound(vet);
      expect(msg.type, MessageType.vetFound);
      expect(msg.isUser, false);
      expect(msg.vetData, isNotNull);
      expect(msg.vetData!.name, 'Dr. Test');
      expect(msg.vetData!.speciality, 'poultry');
    });

    test('Message.severity builds severity type with level', () {
      for (final level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NONE']) {
        final msg = Message.severity(level);
        expect(msg.type, MessageType.severity);
        expect(msg.severityLevel, level);
        expect(msg.isUser, false);
      }
    });

    test('Message.systemMessage builds system type', () {
      final msg = Message.systemMessage('Consultation complete.');
      expect(msg.type, MessageType.system);
      expect(msg.content, 'Consultation complete.');
      expect(msg.isUser, false);
    });
  });

  group('ChatProvider Epic 4 — WS handlers', () {
    late ProviderContainer container;
    late ChatNotifier notifier;

    setUp(() {
      container = ProviderContainer();
      notifier = container.read(chatProvider.notifier);
    });

    tearDown(() => container.dispose());

    test('severity WS adds severity message to state', () {
      notifier.handleWsMessage({'type': 'severity', 'level': 'HIGH'});
      final msgs = container.read(chatProvider).messages;
      expect(msgs.length, 1);
      expect(msgs.first.type, MessageType.severity);
      expect(msgs.first.severityLevel, 'HIGH');
    });

    test('severity WS with missing level defaults to NONE', () {
      notifier.handleWsMessage({'type': 'severity'});
      final msgs = container.read(chatProvider).messages;
      expect(msgs.first.severityLevel, 'NONE');
    });

    test('vet_found WS adds vetFound message to state', () {
      notifier.handleWsMessage({
        'type': 'vet_found',
        'name': 'Dr. Near',
        'speciality': 'cattle',
        'distance_km': 2.1,
        'phone': '+910001',
      });
      final msgs = container.read(chatProvider).messages;
      expect(msgs.length, 1);
      expect(msgs.first.type, MessageType.vetFound);
      expect(msgs.first.vetData!.name, 'Dr. Near');
    });

    test('notification_sent WS adds system message containing vet name', () {
      notifier.handleWsMessage({
        'type': 'notification_sent',
        'vet_name': 'Dr. Patel',
        'session_id': 's1',
      });
      final msgs = container.read(chatProvider).messages;
      expect(msgs.length, 1);
      expect(msgs.first.type, MessageType.system);
      expect(msgs.first.content, contains('Dr. Patel'));
    });

    test('notification_sent with missing vet_name uses fallback', () {
      notifier.handleWsMessage({'type': 'notification_sent'});
      final msgs = container.read(chatProvider).messages;
      expect(msgs.first.type, MessageType.system);
    });

    test('session_complete WS sets sessionComplete = true', () {
      notifier.handleWsMessage({
        'type': 'session_complete',
        'consultation_id': 'c1',
      });
      expect(container.read(chatProvider).sessionComplete, true);
    });

    test('session_complete WS adds a system message', () {
      notifier.handleWsMessage({'type': 'session_complete'});
      final msgs = container.read(chatProvider).messages;
      expect(msgs.any((m) => m.type == MessageType.system), true);
    });

    test('initial sessionComplete is false', () {
      expect(container.read(chatProvider).sessionComplete, false);
    });

    test('clearMessages resets sessionComplete to false', () {
      notifier.handleWsMessage({'type': 'session_complete'});
      expect(container.read(chatProvider).sessionComplete, true);
      notifier.clearMessages();
      expect(container.read(chatProvider).sessionComplete, false);
    });
  });

  group('ChatProvider Epic 4 — sendGpsData', () {
    late ProviderContainer container;
    late ChatNotifier notifier;

    setUp(() {
      container = ProviderContainer();
      notifier = container.read(chatProvider.notifier);
    });

    tearDown(() => container.dispose());

    test('sends gps_data WS payload with lat, lon, session_id', () {
      final calls = <Map<String, dynamic>>[];
      notifier.setWsSendFn(calls.add);
      notifier.sendGpsData(18.5204, 73.8567, 'sess-gps-1');
      expect(calls.length, 1);
      expect(calls.first['type'], 'gps_data');
      expect(calls.first['lat'], 18.5204);
      expect(calls.first['lon'], 73.8567);
      expect(calls.first['session_id'], 'sess-gps-1');
    });

    test('adds a system message to chat on send', () {
      notifier.setWsSendFn((_) {});
      notifier.sendGpsData(18.0, 73.0, 'sess-gps-2');
      final msgs = container.read(chatProvider).messages;
      expect(msgs.isNotEmpty, true);
      expect(msgs.last.type, MessageType.system);
    });

    test('clears gps pending guard after send', () async {
      notifier.setWsSendFn((_) {});
      // First request_gps primes the guard
      notifier.handleWsMessage({
        'type': 'frontend_action',
        'action': 'request_gps',
      });
      notifier.sendGpsData(18.0, 73.0, 'sess-gps-3');
      // After clearing, a second request_gps should fire trigger again
      bool fired = false;
      notifier.gpsRequestTrigger.listen((_) => fired = true);
      notifier.handleWsMessage({
        'type': 'frontend_action',
        'action': 'request_gps',
      });
      await Future.delayed(Duration.zero);
      expect(fired, true);
    });
  });

  group('ChatProvider Epic 4 — sendVetPreference', () {
    late ProviderContainer container;
    late ChatNotifier notifier;

    setUp(() {
      container = ProviderContainer();
      notifier = container.read(chatProvider.notifier);
    });

    tearDown(() => container.dispose());

    test('yes choice sends vet_preference WS with choice=yes', () {
      final calls = <Map<String, dynamic>>[];
      notifier.setWsSendFn(calls.add);
      notifier.sendVetPreference('yes', 'sess-vp-1');
      expect(calls.first['type'], 'vet_preference');
      expect(calls.first['choice'], 'yes');
      expect(calls.first['session_id'], 'sess-vp-1');
    });

    test('no choice sends vet_preference WS with choice=no', () {
      final calls = <Map<String, dynamic>>[];
      notifier.setWsSendFn(calls.add);
      notifier.sendVetPreference('no', 'sess-vp-2');
      expect(calls.first['choice'], 'no');
    });

    test('adds a user message containing Yes to chat on yes', () {
      notifier.setWsSendFn((_) {});
      notifier.sendVetPreference('yes', 'sess-vp-3');
      final msgs = container.read(chatProvider).messages;
      expect(msgs.any((m) => m.isUser && m.content.contains('Yes')), true);
    });

    test('adds a user message containing No to chat on no', () {
      notifier.setWsSendFn((_) {});
      notifier.sendVetPreference('no', 'sess-vp-4');
      final msgs = container.read(chatProvider).messages;
      expect(msgs.any((m) => m.isUser && m.content.contains('No')), true);
    });

    test('sets isStreaming true after sendVetPreference', () {
      notifier.setWsSendFn((_) {});
      notifier.sendVetPreference('yes', 'sess-vp-5');
      expect(container.read(chatProvider).isStreaming, true);
    });
  });

  group('ChatProvider Epic 4 — trigger streams', () {
    late ProviderContainer container;
    late ChatNotifier notifier;

    setUp(() {
      container = ProviderContainer();
      notifier = container.read(chatProvider.notifier);
    });

    tearDown(() => container.dispose());

    test('frontend_action/request_gps fires gpsRequestTrigger', () async {
      bool fired = false;
      notifier.gpsRequestTrigger.listen((_) => fired = true);
      notifier.handleWsMessage({
        'type': 'frontend_action',
        'action': 'request_gps',
      });
      await Future.delayed(Duration.zero);
      expect(fired, true);
    });

    test('duplicate request_gps does not double-fire (guard)', () async {
      int count = 0;
      notifier.gpsRequestTrigger.listen((_) => count++);
      notifier.handleWsMessage({
        'type': 'frontend_action',
        'action': 'request_gps',
      });
      notifier.handleWsMessage({
        'type': 'frontend_action',
        'action': 'request_gps',
      });
      await Future.delayed(Duration.zero);
      expect(count, 1);
    });

    test('vet_found fires vetPreferenceTrigger', () async {
      bool fired = false;
      notifier.vetPreferenceTrigger.listen((_) => fired = true);
      // AC #6: vet preference card only shows for HIGH or MEDIUM severity.
      // Set severity to HIGH first so the guard passes in _handleVetFound.
      notifier.handleWsMessage({'type': 'severity', 'level': 'HIGH'});
      notifier.handleWsMessage({
        'type': 'vet_found',
        'name': 'Dr. X',
        'speciality': 'cattle',
        'distance_km': 1.0,
        'phone': '+910',
      });
      await Future.delayed(Duration.zero);
      expect(fired, true);
    });

    test('duplicate vet_found does not double-fire vetPreferenceTrigger', () async {
      int count = 0;
      notifier.vetPreferenceTrigger.listen((_) => count++);
      // Set severity to HIGH so both vet_found messages can attempt to fire.
      notifier.handleWsMessage({'type': 'severity', 'level': 'HIGH'});
      notifier.handleWsMessage({
        'type': 'vet_found',
        'name': 'Dr. X',
        'speciality': 'cattle',
        'distance_km': 1.0,
        'phone': '+910',
      });
      notifier.handleWsMessage({
        'type': 'vet_found',
        'name': 'Dr. Y',
        'speciality': 'cattle',
        'distance_km': 2.0,
        'phone': '+910',
      });
      await Future.delayed(Duration.zero);
      expect(count, 1);
    });
  });
}
