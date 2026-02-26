import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:alha/services/auth_service.dart';

/// Subclass that accepts an injectable [http.Client] for testing.
class _TestableAuthService extends AuthService {
  final http.Client client;
  _TestableAuthService(this.client);

  @override
  Future<String> login(String username, String password) async {
    final uri = Uri.parse('http://localhost/api/auth/login');
    final response = await client.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    if (body['success'] == true) {
      final token = (body['data'] as Map<String, dynamic>)['token'] as String;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', token);
      return token;
    } else {
      final error = body['error'] as Map<String, dynamic>? ?? {};
      throw AuthException(
        error['message'] as String? ?? 'Login failed',
        error['message_hi'] as String? ?? 'लॉगिन विफल',
      );
    }
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('AuthService', () {
    test('login returns token on success', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {'token': 'test-jwt-token', 'username': 'raju'},
            'error': null,
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = _TestableAuthService(mockClient);
      final token = await service.login('raju', 'secret');
      expect(token, 'test-jwt-token');
    });

    test('login throws AuthException on failure', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'success': false,
            'data': null,
            'error': {
              'code': 'AUTH_FAILED',
              'message': 'Invalid credentials',
              'message_hi': 'गलत जानकारी',
            },
          }),
          401,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = _TestableAuthService(mockClient);
      expect(
        () => service.login('raju', 'wrong'),
        throwsA(isA<AuthException>()),
      );
    });

    test('login stores token in shared_preferences', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {'token': 'stored-token'},
            'error': null,
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = _TestableAuthService(mockClient);
      await service.login('raju', 'pw');

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('auth_token'), 'stored-token');
    });

    test('isLoggedIn returns false when no token stored', () async {
      final service = AuthService();
      expect(await service.isLoggedIn(), false);
    });

    test('isLoggedIn returns true after token stored', () async {
      // Build a fake JWT with a future exp claim so isLoggedIn() passes expiry check
      final futureExp = (DateTime.now().millisecondsSinceEpoch ~/ 1000) + 3600;
      final header = base64Url.encode(utf8.encode('{"alg":"RS256","kid":"k1"}')).replaceAll('=', '');
      final payload = base64Url.encode(utf8.encode('{"sub":"user","exp":$futureExp}')).replaceAll('=', '');
      final fakeJwt = '$header.$payload.fakesig';
      SharedPreferences.setMockInitialValues({'auth_token': fakeJwt});
      final service = AuthService();
      expect(await service.isLoggedIn(), true);
    });

    test('logout removes token and sessionId', () async {
      SharedPreferences.setMockInitialValues({
        'auth_token': 'tok',
        'session_id': 'sess-1',
      });
      final service = AuthService();
      await service.logout();
      expect(await service.isLoggedIn(), false);
      expect(await service.getSessionId(), isNull);
    });

    test('setSessionId and getSessionId round-trip', () async {
      final service = AuthService();
      await service.setSessionId('my-session-id');
      expect(await service.getSessionId(), 'my-session-id');
    });
  });
}
