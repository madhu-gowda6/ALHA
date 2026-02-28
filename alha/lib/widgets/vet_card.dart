import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../platform/phone_launcher.dart';

class VetCard extends StatelessWidget {
  final String name;
  final String speciality;
  final double distanceKm;
  final String phone;

  const VetCard({
    super.key,
    required this.name,
    required this.speciality,
    required this.distanceKm,
    required this.phone,
  });

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.green.shade200),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.06),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.local_hospital, color: Colors.green[700], size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    name,
                    style: GoogleFonts.notoSans(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                      color: Colors.black87,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            _infoRow('Speciality / विशेषता', speciality),
            _infoRow(
              'Distance / दूरी',
              '${distanceKm.toStringAsFixed(1)} km',
            ),
            const SizedBox(height: 8),
            GestureDetector(
              onTap: () => launchPhoneCall(phone),
              child: Row(
                children: [
                  Icon(Icons.phone, color: Colors.green[700], size: 18),
                  const SizedBox(width: 6),
                  Text(
                    phone,
                    style: GoogleFonts.notoSans(
                      color: Colors.green[700],
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                      decoration: TextDecoration.underline,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'कॉल करें',
                    style: GoogleFonts.notoSansDevanagari(
                      color: Colors.green[700],
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Text(
            '$label: ',
            style: GoogleFonts.notoSansDevanagari(
              fontSize: 12,
              color: Colors.black54,
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: GoogleFonts.notoSans(
                fontSize: 13,
                color: Colors.black87,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
