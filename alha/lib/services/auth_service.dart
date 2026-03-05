import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_config.dart';

class AuthException implements Exception {
  final String message;
  final String messageHi;
  AuthException(this.message, this.messageHi);
}

class AuthService {
  static const _tokenKey = 'auth_token';
  static const _sessionIdKey = 'session_id';

  Future<String> login(String username, String password) async {
    final uri = Uri.parse('${AppConfig.apiGatewayUrl}/api/auth/login');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );

    final body = jsonDecode(response.body) as Map<String, dynamic>;

    if (body['success'] == true) {
      final token = (body['data'] as Map<String, dynamic>)['token'] as String;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_tokenKey, token);
      return token;
    } else {
      final error = body['error'] as Map<String, dynamic>? ?? {};
      throw AuthException(
        error['message'] as String? ?? 'Login failed',
        error['message_hi'] as String? ?? 'लॉगिन विफल',
      );
    }
  }

  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  Future<Map<String, dynamic>?> getTokenClaims() async {
    final token = await getToken();
    if (token == null || token.isEmpty) return null;
    try {
      final parts = token.split('.');
      if (parts.length != 3) return null;
      final payload = base64Url.normalize(parts[1]);
      final decoded = utf8.decode(base64Url.decode(payload));
      return jsonDecode(decoded) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  Future<bool> isLoggedIn() async {
    final claims = await getTokenClaims();
    if (claims == null) return false;
    final exp = claims['exp'] as int?;
    if (exp == null) return false;
    return DateTime.now().isBefore(
      DateTime.fromMillisecondsSinceEpoch(exp * 1000),
    );
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_sessionIdKey);
  }

  Future<void> setSessionId(String id) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_sessionIdKey, id);
  }

  Future<String?> getSessionId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_sessionIdKey);
  }
}
