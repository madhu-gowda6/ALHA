import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class SeverityBadge extends StatelessWidget {
  final String level;

  const SeverityBadge({super.key, required this.level});

  @override
  Widget build(BuildContext context) {
    final (bgColor, textColor, label, labelHi) = _resolve(level);

    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: GoogleFonts.notoSans(
                color: textColor,
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
            Text(
              labelHi,
              style: GoogleFonts.notoSansDevanagari(
                color: textColor.withValues(alpha: 0.85),
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }

  static (Color, Color, String, String) _resolve(String level) {
    switch (level.toUpperCase()) {
      case 'CRITICAL':
        return (Colors.red[700]!, Colors.white, 'CRITICAL Severity', 'गंभीर');
      case 'HIGH':
        return (Colors.orange[700]!, Colors.white, 'HIGH Severity', 'उच्च');
      case 'MEDIUM':
        return (Colors.amber[600]!, Colors.black87, 'MEDIUM Severity', 'मध्यम');
      case 'LOW':
        return (Colors.green[600]!, Colors.white, 'LOW Severity', 'कम');
      case 'NONE':
      default:
        return (Colors.grey[400]!, Colors.black87, 'No Severity', 'कोई नहीं');
    }
  }
}
