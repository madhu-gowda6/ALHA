import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'config/theme.dart';
import 'screens/login_screen.dart';

void main() {
  runApp(const ProviderScope(child: AlhaApp()));
}

class AlhaApp extends StatelessWidget {
  const AlhaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ALHA',
      debugShowCheckedModeBanner: false,
      theme: alhaTheme(),
      home: const LoginScreen(),
    );
  }
}
