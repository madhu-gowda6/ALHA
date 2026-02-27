import 'package:flutter/material.dart';

import '../models/message.dart';

class BoundingBoxOverlay extends StatelessWidget {
  final BboxData bbox;
  final Size imageSize;

  const BoundingBoxOverlay({
    super.key,
    required this.bbox,
    required this.imageSize,
  });

  @override
  Widget build(BuildContext context) => CustomPaint(
        size: imageSize,
        painter: _BboxPainter(bbox: bbox),
      );
}

class _BboxPainter extends CustomPainter {
  final BboxData bbox;

  const _BboxPainter({required this.bbox});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.red
      ..strokeWidth = 3.0
      ..style = PaintingStyle.stroke;

    final rect = Rect.fromLTWH(
      bbox.left * size.width,
      bbox.top * size.height,
      bbox.width * size.width,
      bbox.height * size.height,
    );

    canvas.drawRect(rect, paint);
  }

  @override
  bool shouldRepaint(_BboxPainter oldDelegate) =>
      oldDelegate.bbox.left != bbox.left ||
      oldDelegate.bbox.top != bbox.top ||
      oldDelegate.bbox.width != bbox.width ||
      oldDelegate.bbox.height != bbox.height;
}
