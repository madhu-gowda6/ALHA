import 'package:flutter/material.dart';

class VoiceButton extends StatefulWidget {
  final bool isListening;
  final void Function() onPressed;

  const VoiceButton({
    super.key,
    required this.onPressed,
    this.isListening = false,
  });

  @override
  State<VoiceButton> createState() => _VoiceButtonState();
}

class _VoiceButtonState extends State<VoiceButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.3).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 48,
      height: 48,
      child: widget.isListening
          ? AnimatedBuilder(
              animation: _pulseAnimation,
              builder: (_, child) => Transform.scale(
                scale: _pulseAnimation.value,
                child: child,
              ),
              child: _buildButton(Colors.red),
            )
          : _buildButton(Colors.grey.shade600),
    );
  }

  Widget _buildButton(Color color) {
    return IconButton(
      icon: Icon(
        widget.isListening ? Icons.mic : Icons.mic_none,
        color: color,
      ),
      onPressed: widget.onPressed,
      tooltip: widget.isListening ? 'Stop listening' : 'Start voice input',
    );
  }
}
