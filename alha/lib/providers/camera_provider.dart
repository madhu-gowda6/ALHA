import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

class CameraState {
  final bool isUploading;
  final double uploadProgress;
  final String? lastS3Key;
  /// Maps s3Key → image bytes so each diagnosis renders its own image,
  /// even when multiple uploads have occurred in the same session.
  final Map<String, Uint8List> imageBytesMap;
  final String? error;

  const CameraState({
    this.isUploading = false,
    this.uploadProgress = 0.0,
    this.lastS3Key,
    this.imageBytesMap = const {},
    this.error,
  });

  CameraState copyWith({
    bool? isUploading,
    double? uploadProgress,
    String? lastS3Key,
    Map<String, Uint8List>? imageBytesMap,
    String? error,
    bool clearError = false,
  }) =>
      CameraState(
        isUploading: isUploading ?? this.isUploading,
        uploadProgress: uploadProgress ?? this.uploadProgress,
        lastS3Key: lastS3Key ?? this.lastS3Key,
        imageBytesMap: imageBytesMap ?? this.imageBytesMap,
        error: clearError ? null : error ?? this.error,
      );
}

class CameraNotifier extends StateNotifier<CameraState> {
  CameraNotifier() : super(const CameraState());

  void setUploading(bool uploading) =>
      state = state.copyWith(isUploading: uploading, clearError: true);

  void setUploadProgress(double progress) =>
      state = state.copyWith(uploadProgress: progress);

  void setLastS3Key(String s3Key) => state = state.copyWith(lastS3Key: s3Key);

  /// Store bytes keyed by s3Key so ImageBubble can retrieve the correct image
  /// even after subsequent uploads have occurred.
  void setImageBytes(String s3Key, Uint8List bytes) {
    final updated = Map<String, Uint8List>.from(state.imageBytesMap)
      ..[s3Key] = bytes;
    state = state.copyWith(imageBytesMap: updated);
  }

  void setError(String? error) => state =
      error == null ? state.copyWith(clearError: true) : state.copyWith(error: error);

  void reset() => state = const CameraState();
}

final cameraProvider = StateNotifierProvider<CameraNotifier, CameraState>(
  (ref) => CameraNotifier(),
);
