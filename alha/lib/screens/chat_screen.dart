import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import '../providers/chat_provider.dart';
import '../providers/session_provider.dart';
import '../services/speech_service.dart';
import '../services/websocket_service.dart';
import '../widgets/input_bar.dart';
import '../widgets/language_toggle.dart';
import '../widgets/text_bubble.dart';
import '../widgets/typing_indicator.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _wsService = WebSocketService();
  final _speechService = SpeechService();
  final _scrollController = ScrollController();
  final _inputBarKey = GlobalKey<InputBarState>();

  StreamSubscription? _wsSub;
  StreamSubscription? _wsStateSub;
  bool _isListening = false;

  @override
  void initState() {
    super.initState();
    _connect();
  }

  void _connect() {
    final session = ref.read(sessionProvider);
    final token = session.authToken ?? '';

    _wsStateSub = _wsService.connectionStateStream.listen((state) {
      ref.read(sessionProvider.notifier).setConnectionState(state);
      if (state == WsConnectionState.reconnecting) {
        _showReconnectSnackBar();
      }
    });

    _wsSub = _wsService.messages.listen((json) {
      ref.read(chatProvider.notifier).handleWsMessage(json);
      _scrollToBottom();
    });

    _wsService.connect(AppConfig.wsUrl, token);
  }

  void _showReconnectSnackBar() {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Reconnecting... / पुनः जोड़ा जा रहा है...'),
        duration: Duration(seconds: 3),
      ),
    );
  }

  void _sendMessage(String text) {
    final session = ref.read(sessionProvider);
    final language = ref.read(sessionProvider.notifier).detectLanguage(text);
    if (language != session.language) {
      ref.read(sessionProvider.notifier).setLanguage(language);
    }

    ref.read(chatProvider.notifier).addUserMessage(text, language: language);

    _wsService.send({
      'type': 'chat',
      'session_id': session.sessionId ?? '',
      'message': text,
      'language': language,
    });

    _scrollToBottom();
  }

  Future<void> _toggleVoice() async {
    if (_isListening) {
      await _speechService.stopListening();
      setState(() => _isListening = false);
    } else {
      final ok = await _speechService.initialize();
      if (!ok) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Microphone access denied / माइक्रोफ़ोन की अनुमति नहीं मिली',
              ),
            ),
          );
        }
        return;
      }
      setState(() => _isListening = true);
      final lang = ref.read(sessionProvider).language;
      await _speechService.startListening(
        (transcript) {
          setState(() => _isListening = false);
          _inputBarKey.currentState?.setVoiceText(transcript);
        },
        localeId: lang == 'en' ? 'en_US' : 'hi_IN',
        onError: (error) {
          setState(() => _isListening = false);
          if (!mounted) return;
          final isPermission = error.contains('not_allowed') ||
              error.contains('permission') ||
              error.contains('denied');
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                isPermission
                    ? 'Microphone access denied / माइक्रोफ़ोन की अनुमति नहीं मिली'
                    : 'Voice error: $error / आवाज़ त्रुटि हुई',
              ),
            ),
          );
        },
      );
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _wsSub?.cancel();
    _wsStateSub?.cancel();
    _wsService.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final chat = ref.watch(chatProvider);
    final connState = session.connectionState;

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            _ConnectionDot(state: connState),
            const SizedBox(width: 8),
            const Text('ALHA'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () {
              // History screen — Epic 5 (stub)
            },
            tooltip: 'Chat History',
          ),
          LanguageToggle(
            currentLanguage: session.language,
            onChanged: (lang) =>
                ref.read(sessionProvider.notifier).setLanguage(lang),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount:
                  chat.messages.length + (chat.isStreaming ? 1 : 0),
              itemBuilder: (_, i) {
                // Show TypingIndicator as last item while streaming and no text yet
                if (chat.isStreaming &&
                    i == chat.messages.length &&
                    chat.currentStreamingText.isEmpty) {
                  return const TypingIndicator();
                }
                if (i >= chat.messages.length) return const SizedBox.shrink();
                return TextBubble(message: chat.messages[i]);
              },
            ),
          ),
          InputBar(
            key: _inputBarKey,
            onSubmit: _sendMessage,
            disabled: chat.isStreaming,
            onVoicePressed: _toggleVoice,
            isListening: _isListening,
          ),
        ],
      ),
    );
  }
}

class _ConnectionDot extends StatefulWidget {
  final WsConnectionState state;
  const _ConnectionDot({required this.state});

  @override
  State<_ConnectionDot> createState() => _ConnectionDotState();
}

class _ConnectionDotState extends State<_ConnectionDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    Color color;
    bool pulse;
    switch (widget.state) {
      case WsConnectionState.connected:
        color = Colors.greenAccent;
        pulse = false;
      case WsConnectionState.disconnected:
        color = Colors.red;
        pulse = false;
      default:
        color = Colors.greenAccent;
        pulse = true;
    }

    if (!pulse) {
      return _dot(color, 1.0);
    }
    return AnimatedBuilder(
      animation: _controller,
      builder: (_, __) => _dot(color, 0.4 + 0.6 * _controller.value),
    );
  }

  Widget _dot(Color color, double opacity) => Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(
          color: color.withValues(alpha: opacity),
          shape: BoxShape.circle,
        ),
      );
}
