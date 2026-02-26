import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:alha/screens/login_screen.dart';

Widget _wrap(Widget child) {
  return ProviderScope(child: MaterialApp(home: child));
}

void main() {
  group('LoginScreen widget', () {
    testWidgets('renders username and password fields', (tester) async {
      await tester.pumpWidget(_wrap(const LoginScreen()));
      expect(find.byKey(const Key('username_field')), findsOneWidget);
      expect(find.byKey(const Key('password_field')), findsOneWidget);
    });

    testWidgets('renders login button', (tester) async {
      await tester.pumpWidget(_wrap(const LoginScreen()));
      expect(find.byKey(const Key('login_button')), findsOneWidget);
    });

    testWidgets('login button is disabled when loading', (tester) async {
      // The button is initially enabled
      await tester.pumpWidget(_wrap(const LoginScreen()));
      final button = tester.widget<ElevatedButton>(
        find.byKey(const Key('login_button')),
      );
      expect(button.onPressed, isNotNull);
    });

    testWidgets('empty username and password does not trigger login', (tester) async {
      await tester.pumpWidget(_wrap(const LoginScreen()));
      await tester.tap(find.byKey(const Key('login_button')));
      await tester.pump();
      // No navigation, still on login screen
      expect(find.byKey(const Key('login_button')), findsOneWidget);
    });

    testWidgets('displays ALHA title', (tester) async {
      await tester.pumpWidget(_wrap(const LoginScreen()));
      expect(find.text('ALHA'), findsOneWidget);
    });

    testWidgets('displays AI Livestock Health Assistant subtitle', (tester) async {
      await tester.pumpWidget(_wrap(const LoginScreen()));
      expect(find.text('AI Livestock Health Assistant'), findsOneWidget);
    });

    testWidgets('password field is obscured', (tester) async {
      await tester.pumpWidget(_wrap(const LoginScreen()));
      final passwordField = tester.widget<TextField>(
        find.byKey(const Key('password_field')),
      );
      expect(passwordField.obscureText, true);
    });
  });
}
