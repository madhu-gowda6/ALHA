import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

const Color primaryGreen = Color(0xFF2E7D32);
const Color lightGreen = Color(0xFF4CAF50);
const Color earthBrown = Color(0xFF6D4C41);
const Color creamBackground = Color(0xFFF9F6F0);

ThemeData alhaTheme() {
  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: primaryGreen,
      background: creamBackground,
    ),
    textTheme: GoogleFonts.interTextTheme().copyWith(
      bodyLarge: GoogleFonts.notoSansDevanagari(fontSize: 16),
      bodyMedium: GoogleFonts.notoSansDevanagari(fontSize: 14),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: primaryGreen,
      foregroundColor: Colors.white,
      elevation: 0,
    ),
  );
}
