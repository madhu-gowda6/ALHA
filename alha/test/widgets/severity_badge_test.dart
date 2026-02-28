import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:alha/widgets/severity_badge.dart';

void main() {
  group('SeverityBadge', () {
    Widget _wrap(String level) => MaterialApp(
          home: Scaffold(body: SeverityBadge(level: level)),
        );

    testWidgets('CRITICAL renders correct English and Hindi label',
        (tester) async {
      await tester.pumpWidget(_wrap('CRITICAL'));
      expect(find.text('CRITICAL Severity'), findsOneWidget);
      expect(find.text('गंभीर'), findsOneWidget);
    });

    testWidgets('HIGH renders correct label', (tester) async {
      await tester.pumpWidget(_wrap('HIGH'));
      expect(find.text('HIGH Severity'), findsOneWidget);
      expect(find.text('उच्च'), findsOneWidget);
    });

    testWidgets('MEDIUM renders correct label', (tester) async {
      await tester.pumpWidget(_wrap('MEDIUM'));
      expect(find.text('MEDIUM Severity'), findsOneWidget);
      expect(find.text('मध्यम'), findsOneWidget);
    });

    testWidgets('LOW renders correct label', (tester) async {
      await tester.pumpWidget(_wrap('LOW'));
      expect(find.text('LOW Severity'), findsOneWidget);
      expect(find.text('कम'), findsOneWidget);
    });

    testWidgets('NONE renders correct label', (tester) async {
      await tester.pumpWidget(_wrap('NONE'));
      expect(find.text('No Severity'), findsOneWidget);
      expect(find.text('कोई नहीं'), findsOneWidget);
    });

    testWidgets('level is case-insensitive — lowercase critical works',
        (tester) async {
      await tester.pumpWidget(_wrap('critical'));
      expect(find.text('CRITICAL Severity'), findsOneWidget);
    });

    testWidgets('unknown level falls through to NONE display', (tester) async {
      await tester.pumpWidget(_wrap('EXTREME'));
      expect(find.text('No Severity'), findsOneWidget);
    });

    testWidgets('has minimum 48dp height container', (tester) async {
      await tester.pumpWidget(_wrap('HIGH'));
      // Find the Container with minHeight constraint
      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(SeverityBadge),
          matching: find.byType(Container),
        ).first,
      );
      final constraints = container.constraints;
      expect(constraints?.minHeight, greaterThanOrEqualTo(48));
    });

    testWidgets('pill shape — finds DecoratedBox with circular border radius',
        (tester) async {
      await tester.pumpWidget(_wrap('CRITICAL'));
      final decoratedBoxes = tester.widgetList<DecoratedBox>(
        find.descendant(
          of: find.byType(SeverityBadge),
          matching: find.byType(DecoratedBox),
        ),
      );
      final hasPill = decoratedBoxes.any((db) {
        final deco = db.decoration;
        if (deco is BoxDecoration) {
          final br = deco.borderRadius;
          return br != null;
        }
        return false;
      });
      expect(hasPill, true);
    });
  });
}
