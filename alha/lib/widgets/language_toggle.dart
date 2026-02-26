import 'package:flutter/material.dart';

class LanguageToggle extends StatelessWidget {
  final String currentLanguage;
  final void Function(String) onChanged;

  const LanguageToggle({
    super.key,
    required this.currentLanguage,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final isHindi = currentLanguage == 'hi';
    return GestureDetector(
      onTap: () => onChanged(isHindi ? 'en' : 'hi'),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.2),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white54),
        ),
        child: Text(
          isHindi ? 'हि' : 'EN',
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.bold,
            fontSize: 14,
          ),
        ),
      ),
    );
  }
}
