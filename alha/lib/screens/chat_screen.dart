import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../config/app_config.dart';
import '../models/message.dart';
import '../providers/camera_provider.dart';
import '../providers/chat_provider.dart';
import '../providers/session_provider.dart';
import '../services/auth_service.dart';
import '../services/location_service.dart';
import '../services/transcribe_service.dart';
import '../services/websocket_service.dart';
import '../widgets/camera_overlay.dart';
import '../widgets/image_bubble.dart';
import '../widgets/input_bar.dart';
import '../widgets/language_toggle.dart';
import '../widgets/severity_badge.dart';
import '../widgets/symptom_interview_overlay.dart';
import '../widgets/text_bubble.dart';
import 'history_screen.dart';
import 'profile_screen.dart';
import '../widgets/typing_indicator.dart';
import '../widgets/vet_card.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _wsService = WebSocketService();
  final _transcribeService = TranscribeService();
  final _locationService = LocationService();
  final _scrollController = ScrollController();
  final _inputBarKey = GlobalKey<InputBarState>();

  StreamSubscription? _wsSub;
  StreamSubscription? _wsStateSub;
  StreamSubscription? _symptomSub;
  StreamSubscription? _cameraSub;
  StreamSubscription? _gpsSub;
  StreamSubscription? _vetPrefSub;
  bool _isListening = false;
  bool _showGpsRequest = false;
  bool _showVetPreference = false;

  @override
  void initState() {
    super.initState();
    _connect();
  }

  void _connect() {
    final session = ref.read(sessionProvider);
    final token = session.authToken ?? '';

    // Wire WS send callback into chatProvider
    ref.read(chatProvider.notifier).setWsSendFn(_wsService.send);

    _wsStateSub = _wsService.connectionStateStream.listen((state) {
      ref.read(sessionProvider.notifier).setConnectionState(state);
      if (state == WsConnectionState.reconnecting) {
        _showReconnectSnackBar();
      } else if (state == WsConnectionState.connected) {
        if (mounted) ScaffoldMessenger.of(context).hideCurrentSnackBar();
      }
    });

    _wsSub = _wsService.messages.listen((json) {
      // transcript messages are handled by TranscribeService directly
      if ((json['type'] as String?) == 'transcript') return;
      ref.read(chatProvider.notifier).handleWsMessage(json);
      _scrollToBottom();
    });

    // Listen to overlay trigger streams
    _symptomSub = ref
        .read(chatProvider.notifier)
        .symptomInterviewTrigger
        .listen(_showSymptomOverlay);

    _cameraSub = ref
        .read(chatProvider.notifier)
        .cameraOverlayTrigger
        .listen((_) => _showCameraOverlay());

    _gpsSub = ref
        .read(chatProvider.notifier)
        .gpsRequestTrigger
        .listen((_) {
      // Show inline GPS card — geolocation MUST be called from a user gesture
      // (button tap) for Chrome to show the permission dialog.
      if (mounted) setState(() => _showGpsRequest = true);
      _scrollToBottom();
    });

    _vetPrefSub = ref
        .read(chatProvider.notifier)
        .vetPreferenceTrigger
        .listen((_) {
      if (mounted) setState(() => _showVetPreference = true);
    });

    _wsService.connect(AppConfig.wsUrl, token);
  }

  Future<void> _startNewSession() async {
    // Cancel WS-level subscriptions
    await _wsSub?.cancel();
    await _wsStateSub?.cancel();
    _wsService.disconnect();

    // Cancel chatProvider subs so _connect() re-subscribes without duplicates (F1)
    await _symptomSub?.cancel();
    await _cameraSub?.cancel();
    await _gpsSub?.cancel();
    await _vetPrefSub?.cancel();

    // Reset local overlay state (F3)
    if (mounted) setState(() {
      _showGpsRequest = false;
      _showVetPreference = false;
    });

    // New session ID
    final newId = const Uuid().v4();
    await AuthService().setSessionId(newId);

    if (!mounted) return; // guard after async (F2)

    // Reset providers
    ref.read(sessionProvider.notifier).setSessionId(newId);
    ref.read(chatProvider.notifier).clearMessages();

    // Reconnect — re-subscribes all streams fresh
    _connect();
  }

  void _showSymptomOverlay(SymptomInterviewEvent event) {
    if (!mounted) return;
    final session = ref.read(sessionProvider);
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      isDismissible: false,
      builder: (_) => SymptomInterviewOverlay(
        questions: event.questions,
        questionsHi: event.questionsHi,
        language: session.language,
        onComplete: (answers) => ref
            .read(chatProvider.notifier)
            .sendSymptomAnswers(answers, session.sessionId ?? ''),
      ),
    ).then((_) {
      if (mounted) {
        ref.read(chatProvider.notifier).clearSymptomInterviewPending();
      }
    });
  }

  void _showCameraOverlay() {
    if (!mounted) return;
    final session = ref.read(sessionProvider);
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      isDismissible: false,
      builder: (_) => CameraOverlay(
        sessionId: session.sessionId ?? '',
        authToken: session.authToken ?? '',
        language: session.language,
        onImageUploaded: (s3Key) => ref
            .read(chatProvider.notifier)
            .sendImageData(s3Key, session.sessionId ?? ''),
        onAnalyzingMessage: () {},
      ),
    ).then((_) {
      if (mounted) {
        ref.read(chatProvider.notifier).clearCameraOverlayPending();
      }
    });
  }

  Future<void> _handleGpsRequest() async {
    if (!mounted) return;
    setState(() => _showGpsRequest = false);
    final session = ref.read(sessionProvider);
    final result = await _locationService.getCurrentLocation();
    if (!mounted) return;
    if (result.success) {
      ref.read(chatProvider.notifier).sendGpsData(
            result.lat!,
            result.lon!,
            session.sessionId ?? '',
          );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result.errorMessage ?? 'Location unavailable'),
          duration: const Duration(seconds: 5),
        ),
      );
      ref.read(chatProvider.notifier).clearGpsRequestPending();
    }
  }

  void _showReconnectSnackBar() {
    if (!mounted) return;
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Reconnecting... / पुनः जोड़ा जा रहा है...'),
        duration: Duration(minutes: 1),
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
    final session = ref.read(sessionProvider);
    if (_isListening) {
      await _transcribeService.stopCapture(
        wsService: _wsService,
        sessionId: session.sessionId ?? '',
      );
      _inputBarKey.currentState?.cancelVoiceCapture();
      setState(() => _isListening = false);
    } else {
      setState(() => _isListening = true);
      _inputBarKey.currentState?.startVoiceCapture();
      final ok = await _transcribeService.startCapture(
        wsService: _wsService,
        sessionId: session.sessionId ?? '',
        language: session.language == 'en' ? 'en-US' : 'hi-IN',
        onTranscript: (text, isFinal) {
          if (!mounted) return;
          if (isFinal) {
            _inputBarKey.currentState?.commitVoiceText(text);
            // Re-capture the committed text as the base for the next segment.
            _inputBarKey.currentState?.startVoiceCapture();
          } else {
            _inputBarKey.currentState?.updateVoiceText(text);
          }
        },
      );
      if (!ok) {
        _inputBarKey.currentState?.cancelVoiceCapture();
        setState(() => _isListening = false);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Microphone access denied / माइक्रोफ़ोन की अनुमति नहीं मिली',
            ),
          ),
        );
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
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
    _symptomSub?.cancel();
    _cameraSub?.cancel();
    _gpsSub?.cancel();
    _vetPrefSub?.cancel();
    _transcribeService.dispose();
    _wsService.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Widget _buildMessageItem(int i, ChatState chat, String language) {
    // Show TypingIndicator as last item while streaming and no text yet
    if (chat.isStreaming &&
        i == chat.messages.length &&
        chat.currentStreamingText.isEmpty) {
      return const TypingIndicator();
    }
    if (i >= chat.messages.length) return const SizedBox.shrink();

    final msg = chat.messages[i];

    if (msg.type == MessageType.diagnosis && msg.diagnosisData != null) {
      final cameraState = ref.watch(cameraProvider);
      return ImageBubble(
        diagnosisData: msg.diagnosisData!,
        imageBytes: cameraState.imageBytesMap[msg.diagnosisData!.s3Key],
        language: language,
      );
    }

    if (msg.type == MessageType.severity && msg.severityLevel != null) {
      return SeverityBadge(level: msg.severityLevel!);
    }

    if (msg.type == MessageType.vetFound && msg.vetData != null) {
      return VetCard(
        name: msg.vetData!.name,
        speciality: msg.vetData!.speciality,
        distanceKm: msg.vetData!.distanceKm,
        phone: msg.vetData!.phone,
      );
    }

    return TextBubble(message: msg);
  }

  Widget _buildNewSessionBanner() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.green.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.green.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Consultation complete. Start a new one?\n'
            'परामर्श पूरा हुआ। नया शुरू करें?',
            style: TextStyle(
              fontWeight: FontWeight.w600,
              color: Colors.green.shade900,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              icon: const Icon(Icons.add_comment_outlined),
              label: const Text('New Consultation / नई परामर्श'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green[700],
                foregroundColor: Colors.white,
                minimumSize: const Size(0, 48),
              ),
              onPressed: _startNewSession,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGpsRequestCard() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.location_on, color: Colors.blue.shade700, size: 22),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'We need your location to find the nearest vet.\n'
                  'सबसे नज़दीकी पशु चिकित्सक खोजने के लिए आपका स्थान चाहिए।',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: Colors.blue.shade900,
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              icon: const Icon(Icons.my_location),
              label: const Text('Share Location / स्थान साझा करें'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue[700],
                foregroundColor: Colors.white,
                minimumSize: const Size(0, 48),
              ),
              // Called from button tap → user gesture → Chrome shows permission dialog
              onPressed: _handleGpsRequest,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVetPreferenceCard(String sessionId) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.green.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.green.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Connect with this vet? / इस पशु चिकित्सक से जोड़ें?',
            style: TextStyle(
              fontWeight: FontWeight.w600,
              color: Colors.green.shade900,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green[700],
                    foregroundColor: Colors.white,
                  ),
                  onPressed: () {
                    setState(() => _showVetPreference = false);
                    ref
                        .read(chatProvider.notifier)
                        .sendVetPreference('yes', sessionId);
                  },
                  child: const Text('Yes / हाँ'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.green[700],
                    side: BorderSide(color: Colors.green.shade400),
                  ),
                  onPressed: () {
                    setState(() => _showVetPreference = false);
                    ref
                        .read(chatProvider.notifier)
                        .sendVetPreference('no', sessionId);
                  },
                  child: const Text('No / नहीं'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final chat = ref.watch(chatProvider);
    final connState = session.connectionState;
    final inputDisabled = chat.isStreaming;

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
            icon: const Icon(Icons.person_outline),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ProfileScreen()),
            ),
            tooltip: 'Profile',
          ),
          IconButton(
            icon: const Icon(Icons.add_comment_outlined),
            onPressed: _startNewSession,
            tooltip: 'New Consultation',
          ),
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const HistoryScreen()),
              );
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
              itemCount: chat.messages.length + (chat.isStreaming ? 1 : 0),
              itemBuilder: (_, i) =>
                  _buildMessageItem(i, chat, session.language),
            ),
          ),
          if (chat.sessionComplete) _buildNewSessionBanner(),
          if (_showGpsRequest) _buildGpsRequestCard(),
          if (_showVetPreference)
            _buildVetPreferenceCard(session.sessionId ?? ''),
          InputBar(
            key: _inputBarKey,
            onSubmit: _sendMessage,
            disabled: inputDisabled,
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
