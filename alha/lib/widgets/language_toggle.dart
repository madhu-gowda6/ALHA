import 'package:flutter/material.dart';

class LanguageToggle extends StatelessWidget {
  final String currentLanguage;
  final void Function(String) onChanged;
  const LanguageToggle({super.key, required this.currentLanguage, required this.onChanged});

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
