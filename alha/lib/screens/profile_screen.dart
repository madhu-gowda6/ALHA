import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/session_provider.dart';
import '../services/auth_service.dart';
import 'login_screen.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  Map<String, dynamic>? _claims;
  bool _claimsLoaded = false;

  @override
  void initState() {
    super.initState();
    _loadClaims();
  }

  Future<void> _loadClaims() async {
    final claims = await AuthService().getTokenClaims();
    if (mounted) setState(() {
      _claims = claims;
      _claimsLoaded = true;
    });
  }

  Future<void> _logout() async {
    await AuthService().logout();
    if (mounted) {
      ref.read(sessionProvider.notifier).clearAuth(); // F7: inside mounted check
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (_) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profile / प्रोफ़ाइल')),
      body: !_claimsLoaded
          ? const Center(child: CircularProgressIndicator())
          : _claims == null
          ? Center(
              child: Text(
                'Unable to load profile.\nप्रोफ़ाइल लोड नहीं हो सकी',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade600),
              ),
            )
          : Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const SizedBox(height: 24),
                  CircleAvatar(
                    radius: 40,
                    backgroundColor: Colors.green.shade100,
                    child: Icon(Icons.person,
                        size: 40, color: Colors.green.shade700),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _claims!['cognito:username'] as String? ??
                        _claims!['sub'] as String? ??
                        '—',
                    style: const TextStyle(
                        fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.phone, size: 16, color: Colors.grey.shade600),
                      const SizedBox(width: 4),
                      Text(
                        _claims!['phone_number'] as String? ?? '—',
                        style: TextStyle(
                            fontSize: 15, color: Colors.grey.shade700),
                      ),
                    ],
                  ),
                  const Spacer(),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.logout),
                      label: const Text('Logout / लॉगआउट'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red[700],
                        foregroundColor: Colors.white,
                        minimumSize: const Size(0, 52),
                      ),
                      onPressed: _logout,
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
    );
  }
}
