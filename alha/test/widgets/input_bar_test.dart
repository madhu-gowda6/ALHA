import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:alha/widgets/input_bar.dart';

void main() {
  group('InputBarState voice capture API', () {
    Widget buildWidget({
      required GlobalKey<InputBarState> key,
      String initialText = '',
    }) {
      return MaterialApp(
        home: Scaffold(
          body: InputBar(
            key: key,
            onSubmit: (_) {},
          ),
        ),
      );
    }

    testWidgets('startVoiceCapture + updateVoiceText replaces voice segment, preserves base', (tester) async {
      final key = GlobalKey<InputBarState>();
      await tester.pumpWidget(buildWidget(key: key));

      // Seed existing text
      key.currentState!.setVoiceText('Hello');
      await tester.pump();

      key.currentState!.startVoiceCapture();
      key.currentState!.updateVoiceText('kya hal hai');
      await tester.pump();

      expect(find.text('Hello kya hal hai'), findsOneWidget);
      // Cursor should be at end
      final controller1 = key.currentState!.controller;
      expect(controller1.selection.baseOffset, equals('Hello kya hal hai'.length));

      // Second partial replaces first (no accumulation)
      key.currentState!.updateVoiceText('kya hal hai aapka');
      await tester.pump();

      expect(find.text('Hello kya hal hai aapka'), findsOneWidget);
      expect(controller1.selection.baseOffset, equals('Hello kya hal hai aapka'.length));
    });

    testWidgets('commitVoiceText finalizes transcript and clears _voiceBase', (tester) async {
      final key = GlobalKey<InputBarState>();
      await tester.pumpWidget(buildWidget(key: key));

      key.currentState!.setVoiceText('Hello');
      await tester.pump();

      key.currentState!.startVoiceCapture();
      key.currentState!.commitVoiceText('world');
      await tester.pump();

      expect(find.text('Hello world'), findsOneWidget);
      final controller = key.currentState!.controller;
      expect(controller.selection.baseOffset, equals('Hello world'.length));

      // After commit, a new updateVoiceText should NOT prepend old base
      key.currentState!.startVoiceCapture(); // base is now 'Hello world'
      key.currentState!.updateVoiceText('test');
      await tester.pump();

      expect(find.text('Hello world test'), findsOneWidget);
    });

    testWidgets('cancelVoiceCapture clears _voiceBase without touching controller text', (tester) async {
      final key = GlobalKey<InputBarState>();
      await tester.pumpWidget(buildWidget(key: key));

      key.currentState!.setVoiceText('Hello');
      await tester.pump();

      key.currentState!.startVoiceCapture();
      // Simulate a partial that dirtied the field
      key.currentState!.updateVoiceText('garbage');
      await tester.pump();
      expect(find.text('Hello garbage'), findsOneWidget);

      key.currentState!.cancelVoiceCapture();
      await tester.pump();

      // After cancel, field still shows the last partial (not restored) — but _voiceBase is cleared.
      // Next session re-captures the current controller text as the new base.
      key.currentState!.startVoiceCapture(); // captures 'Hello garbage' as new base
      key.currentState!.updateVoiceText('world');
      await tester.pump();

      expect(find.text('Hello garbage world'), findsOneWidget);
    });

    testWidgets('cancelVoiceCapture before any partial leaves field unchanged', (tester) async {
      final key = GlobalKey<InputBarState>();
      await tester.pumpWidget(buildWidget(key: key));

      key.currentState!.setVoiceText('Hello');
      await tester.pump();

      key.currentState!.startVoiceCapture();
      key.currentState!.cancelVoiceCapture();
      await tester.pump();

      // Text unchanged — no partial was ever applied
      expect(find.text('Hello'), findsOneWidget);
    });

    testWidgets('rapid partial updates do not accumulate stale text', (tester) async {
      final key = GlobalKey<InputBarState>();
      await tester.pumpWidget(buildWidget(key: key));

      key.currentState!.startVoiceCapture();

      for (final partial in ['नमस्', 'नमस्ते', 'नमस्ते आप']) {
        key.currentState!.updateVoiceText(partial);
        await tester.pump();
      }

      expect(find.text('नमस्ते आप'), findsOneWidget);
    });
  });
}
