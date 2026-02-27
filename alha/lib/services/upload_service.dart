import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'dart:convert';

import '../config/app_config.dart';

class UploadUrlResult {
  final String uploadUrl;
  final String s3Key;

  const UploadUrlResult({required this.uploadUrl, required this.s3Key});
}

class UploadException implements Exception {
  final String message;
  final String messageHi;

  const UploadException({required this.message, required this.messageHi});

  @override
  String toString() => 'UploadException: $message';
}

class UploadService {
  Future<UploadUrlResult> getPresignedUrl(
      String sessionId, String authToken) async {
    final uri =
        Uri.parse('${AppConfig.apiGatewayUrl}/api/upload-url');
    final response = await http
        .post(
          uri,
          headers: {
            'Authorization': 'Bearer $authToken',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({'session_id': sessionId}),
        )
        .timeout(
          const Duration(seconds: 15),
          onTimeout: () => throw const UploadException(
            message: 'Request timed out. Please try again.',
            messageHi: 'अनुरोध का समय समाप्त हो गया। कृपया पुनः प्रयास करें।',
          ),
        );

    if (response.statusCode != 200) {
      throw const UploadException(
        message: 'Failed to get upload URL. Please try again.',
        messageHi: 'अपलोड URL प्राप्त करने में विफल। कृपया पुनः प्रयास करें।',
      );
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final data = body['data'] as Map<String, dynamic>?;
    if (data == null || body['success'] != true) {
      throw const UploadException(
        message: 'Upload URL response invalid. Please try again.',
        messageHi: 'अपलोड URL अमान्य है। कृपया पुनः प्रयास करें।',
      );
    }

    return UploadUrlResult(
      uploadUrl: data['upload_url'] as String,
      s3Key: data['s3_key'] as String,
    );
  }

  Future<bool> uploadImage(String uploadUrl, Uint8List bytes) async {
    final response = await http
        .put(
          Uri.parse(uploadUrl),
          body: bytes,
          headers: {'Content-Type': 'image/jpeg'},
        )
        .timeout(
          const Duration(seconds: 30),
          onTimeout: () => throw const UploadException(
            message: 'Upload timed out. Please try again.',
            messageHi: 'अपलोड का समय समाप्त हो गया। कृपया पुनः प्रयास करें।',
          ),
        );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw UploadException(
        message:
            'Image upload failed (${response.statusCode}). Please try again.',
        messageHi:
            'छवि अपलोड विफल (${response.statusCode})। कृपया पुनः प्रयास करें।',
      );
    }
    return true;
  }
}
