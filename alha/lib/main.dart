import 'dart:async';
import 'dart:html' as html;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import 'config/theme.dart';
import 'providers/session_provider.dart';
import 'screens/chat_screen.dart';
import 'screens/login_screen.dart';
import 'services/auth_service.dart';

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
      home: const _OfflineGuard(child: _StartupRouter()),
    );
  }
}

/// Detects browser online/offline state and shows a bilingual offline screen.
class _OfflineGuard extends StatefulWidget {
  final Widget child;
  const _OfflineGuard({required this.child});

  @override
  State<_OfflineGuard> createState() => _OfflineGuardState();
}

class _OfflineGuardState extends State<_OfflineGuard> {
  bool _isOffline = !(html.window.navigator.onLine ?? true);
  late final StreamSubscription<html.Event> _offlineSub;
  late final StreamSubscription<html.Event> _onlineSub;

  @override
  void initState() {
    super.initState();
    _offlineSub = html.window.onOffline.listen((_) {
      setState(() => _isOffline = true);
    });
    _onlineSub = html.window.onOnline.listen((_) {
      setState(() => _isOffline = false);
    });
  }

  @override
  void dispose() {
    _offlineSub.cancel();
    _onlineSub.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_isOffline) return widget.child;
    return Scaffold(
      backgroundColor: const Color(0xFFF9F6F0),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.wifi_off_rounded, size: 72, color: Color(0xFF2E7D32)),
            SizedBox(height: 24),
            Text(
              'No internet connection',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 8),
            Text(
              'इंटरनेट कनेक्शन नहीं है',
              style: TextStyle(fontSize: 18),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 16),
            Text(
              'Please check your network and try again.\nकृपया अपना नेटवर्क जांचें और पुनः प्रयास करें।',
              style: TextStyle(fontSize: 14, color: Colors.black54),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

/// Checks for an existing valid JWT on startup and routes accordingly.
class _StartupRouter extends ConsumerStatefulWidget {
  const _StartupRouter();

  @override
  ConsumerState<_StartupRouter> createState() => _StartupRouterState();
}

class _StartupRouterState extends ConsumerState<_StartupRouter> {
  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    final authService = AuthService();
    final loggedIn = await authService.isLoggedIn();
    if (!mounted) return;

    if (loggedIn) {
      final token = await authService.getToken() ?? '';
      var sessionId = await authService.getSessionId() ?? '';
      if (sessionId.isEmpty) {
        sessionId = const Uuid().v4();
        await authService.setSessionId(sessionId);
      }
      ref.read(sessionProvider.notifier).setAuth(token, sessionId);
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const ChatScreen()),
      );
    } else {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}
