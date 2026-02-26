import 'package:flutter/material.dart';

class VetCard extends StatelessWidget {
  final String vetName;
  final String district;
  const VetCard({super.key, required this.vetName, required this.district});

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
