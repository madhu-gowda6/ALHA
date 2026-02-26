import 'package:flutter/material.dart';

class VoiceButton extends StatelessWidget {
  final void Function() onPressed;
  const VoiceButton({super.key, required this.onPressed});

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
