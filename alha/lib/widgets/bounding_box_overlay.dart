import 'package:flutter/material.dart';

class BoundingBoxOverlay extends StatelessWidget {
  final List<Map<String, dynamic>> boxes;
  const BoundingBoxOverlay({super.key, required this.boxes});

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
