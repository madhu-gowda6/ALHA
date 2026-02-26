import 'package:flutter/material.dart';

class TextBubble extends StatelessWidget {
  final String text;
  final bool isUser;
  const TextBubble({super.key, required this.text, required this.isUser});

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
