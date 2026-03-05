import 'dart:async';
import 'dart:js_interop';

import 'websocket_service.dart';

// ---------------------------------------------------------------------------
// JS interop — functions injected by web/index.html
// ---------------------------------------------------------------------------

@JS('alhaStartAudioCapture')
external JSPromise<JSBoolean> _jsStartCapture(int sampleRate, JSFunction callback);

@JS('alhaStopAudioCapture')
external void _jsStopCapture();

// ---------------------------------------------------------------------------
// TranscribeService
// ---------------------------------------------------------------------------

/// Streams microphone audio over the existing WebSocket to the ECS agent,
/// which pipes it to Amazon Transcribe Streaming and returns transcripts.
///
/// Message protocol (JSON over the chat WebSocket):
///   Flutter → Agent  {"type": "voice_start",  "session_id", "language"}
///   Flutter → Agent  {"type": "voice_audio",  "session_id", "data": "<base64 PCM>"}
///   Flutter → Agent  {"type": "voice_stop",   "session_id"}
///   Agent → Flutter  {"type": "transcript",   "session_id", "text", "is_final": bool}
class TranscribeService {
  StreamSubscription<Map<String, dynamic>>? _transcriptSub;
  bool _capturing = false;

  bool get isCapturing => _capturing;

  /// Start microphone capture and a server-side Transcribe session.
  ///
  /// [onTranscript] fires for every partial and final segment.
  /// Returns `false` if the microphone could not be opened.
  Future<bool> startCapture({
    required WebSocketService wsService,
    required String sessionId,
    required String language,
    required void Function(String text, bool isFinal) onTranscript,
  }) async {
    // Subscribe to incoming transcript messages before sending voice_start so
    // we don't miss the first result if the agent is very fast.
    _transcriptSub = wsService.messages
        .where((m) => m['type'] == 'transcript' && m['session_id'] == sessionId)
        .listen((m) {
      final text = (m['text'] as String?) ?? '';
      final isFinal = (m['is_final'] as bool?) ?? false;
      if (text.isNotEmpty) onTranscript(text, isFinal);
    });

    // Tell the agent to open a Transcribe session.
    wsService.send({'type': 'voice_start', 'session_id': sessionId, 'language': language});

    // Open the browser microphone and start streaming chunks.
    try {
      final jsCallback = ((JSString b64) {
        wsService.send({
          'type': 'voice_audio',
          'session_id': sessionId,
          'data': b64.toDart,
        });
      }).toJS;

      final jsResult = await _jsStartCapture(16000, jsCallback).toDart;
      _capturing = jsResult.toDart;
    } catch (e) {
      await _transcriptSub?.cancel();
      _transcriptSub = null;
      wsService.send({'type': 'voice_stop', 'session_id': sessionId});
      return false;
    }

    if (!_capturing) {
      await _transcriptSub?.cancel();
      _transcriptSub = null;
      wsService.send({'type': 'voice_stop', 'session_id': sessionId});
    }
    return _capturing;
  }

  /// Stop microphone capture and close the server-side Transcribe session.
  Future<void> stopCapture({
    required WebSocketService wsService,
    required String sessionId,
  }) async {
    if (!_capturing) return;
    _capturing = false;
    _jsStopCapture();
    wsService.send({'type': 'voice_stop', 'session_id': sessionId});
    // Keep _transcriptSub alive briefly so trailing final results arrive,
    // then cancel after 3 s.
    Future.delayed(const Duration(seconds: 3), () async {
      await _transcriptSub?.cancel();
      _transcriptSub = null;
    });
  }

  /// Release all resources (call from widget dispose).
  Future<void> dispose() async {
    _capturing = false;
    try {
      _jsStopCapture();
    } catch (_) {}
    await _transcriptSub?.cancel();
    _transcriptSub = null;
  }
}
