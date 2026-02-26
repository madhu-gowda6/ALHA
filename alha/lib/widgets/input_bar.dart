import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'voice_button.dart';

class InputBar extends StatefulWidget {
  final void Function(String) onSubmit;
  final bool disabled;
  final void Function()? onVoicePressed;
  final bool isListening;

  const InputBar({
    super.key,
    required this.onSubmit,
    this.disabled = false,
    this.onVoicePressed,
    this.isListening = false,
  });

  @override
  State<InputBar> createState() => InputBarState();
}

// Public so ChatScreen can hold a GlobalKey<InputBarState> to call setVoiceText.
class InputBarState extends State<InputBar> {
  final _controller = TextEditingController();
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      setState(() => _hasText = _controller.text.trim().isNotEmpty);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final text = _controller.text.trim();
    if (text.isEmpty || widget.disabled) return;
    _controller.clear();
    widget.onSubmit(text);
  }

  /// Called externally when voice recognition produces a transcript.
  void setVoiceText(String text) {
    _controller.text = text;
    _controller.selection = TextSelection.fromPosition(
      TextPosition(offset: text.length),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Colors.grey.shade200)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          VoiceButton(
            onPressed: widget.onVoicePressed ?? () {},
            isListening: widget.isListening,
          ),
          const SizedBox(width: 4),
          Expanded(
            child: TextField(
              controller: _controller,
              enabled: !widget.disabled,
              maxLines: 4,
              minLines: 1,
              textInputAction: TextInputAction.newline,
              style: GoogleFonts.notoSansDevanagari(fontSize: 15),
              decoration: InputDecoration(
                hintText: 'Type your message... / अपना संदेश लिखें...',
                hintStyle: GoogleFonts.notoSansDevanagari(
                  color: Colors.grey.shade500,
                  fontSize: 14,
                ),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(20),
                  borderSide: BorderSide(color: Colors.grey.shade300),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(20),
                  borderSide: BorderSide(color: Colors.grey.shade300),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(20),
                  borderSide: const BorderSide(color: Color(0xFF2E7D32)),
                ),
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              ),
            ),
          ),
          const SizedBox(width: 4),
          SizedBox(
            width: 48,
            height: 48,
            child: IconButton(
              icon: const Icon(Icons.send_rounded),
              color: (_hasText && !widget.disabled)
                  ? const Color(0xFF2E7D32)
                  : Colors.grey.shade400,
              onPressed: (_hasText && !widget.disabled) ? _submit : null,
              tooltip: 'Send',
            ),
          ),
        ],
      ),
    );
  }
}
