import 'package:flutter/material.dart';

class InputBar extends StatelessWidget {
  final void Function(String) onSubmit;
  const InputBar({super.key, required this.onSubmit});

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
