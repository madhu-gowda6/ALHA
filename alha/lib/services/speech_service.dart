import 'package:speech_to_text/speech_to_text.dart';

class SpeechService {
  final SpeechToText _speech = SpeechToText();
  bool _initialized = false;


  void Function(String)? _onError;

  Future<bool> initialize() async {
    if (_initialized) return true;
    _initialized = await _speech.initialize(
      // _onError before each listen() call routes errors to the right handler.
      onError: (error) => _onError?.call(error.errorMsg),
      onStatus: (status) {},
    );
    return _initialized;
  }

  bool get isListening => _speech.isListening;

  Future<void> startListening(
    void Function(String transcript) onResult, {
    String localeId = 'hi_IN',
    void Function(String error)? onError,
  }) async {
    _onError = onError;
    if (!_initialized) await initialize();
    if (!_initialized) return;

    await _speech.listen(
      onResult: (result) {
        if (result.finalResult) {
          onResult(result.recognizedWords);
        }
      },
      localeId: localeId,
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      listenOptions: SpeechListenOptions(partialResults: false),
    );
  }

  Future<void> stopListening() async {
    await _speech.stop();
  }
}
