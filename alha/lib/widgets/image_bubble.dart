import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../models/message.dart';
import 'bounding_box_overlay.dart';

// Disease label → display name mapping (English + Hindi)
const _diseaseNames = {
  'lumpy_skin_disease': ('Lumpy Skin Disease', 'लम्पी स्किन रोग'),
  'newcastle_disease': ('Newcastle Disease', 'रानीखेत रोग'),
  'foot_and_mouth_disease': ('Foot and Mouth Disease', 'खुरपका-मुंहपका रोग'),
  'blackleg': ('Blackleg', 'काला पांव'),
  'anthrax': ('Anthrax', 'एंथ्रेक्स (तिल्ली ज्वर)'),
  'brucellosis': ('Brucellosis', 'ब्रुसेलोसिस'),
};

class ImageBubble extends StatelessWidget {
  final DiagnosisData diagnosisData;
  final Uint8List? imageBytes;
  final String language;

  const ImageBubble({
    super.key,
    required this.diagnosisData,
    this.imageBytes,
    this.language = 'en',
  });

  String _diseaseLabel() {
    final disease = diagnosisData.disease;
    if (disease == null) return language == 'hi' ? 'अज्ञात रोग' : 'Unknown disease';
    final names = _diseaseNames[disease];
    if (names == null) return disease;
    return language == 'hi' ? names.$2 : names.$1;
  }

  String _confidenceLabel() {
    final pct = diagnosisData.confidence.toStringAsFixed(0);
    return language == 'hi' ? '$pct% निश्चितता' : '$pct% confidence';
  }

  @override
  Widget build(BuildContext context) {
    final bytes = imageBytes;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            constraints: const BoxConstraints(maxWidth: 300),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              color: Colors.black12,
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: bytes != null
                  ? _ImageWithBbox(bytes: bytes, diagnosisData: diagnosisData)
                  : _PlaceholderImage(language: language),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${_diseaseLabel()} — ${_confidenceLabel()}',
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }
}

class _ImageWithBbox extends StatefulWidget {
  final Uint8List bytes;
  final DiagnosisData diagnosisData;

  const _ImageWithBbox({required this.bytes, required this.diagnosisData});

  @override
  State<_ImageWithBbox> createState() => _ImageWithBboxState();
}

class _ImageWithBboxState extends State<_ImageWithBbox> {
  @override
  Widget build(BuildContext context) {
    final image = Image.memory(
      widget.bytes,
      fit: BoxFit.contain,
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        return Stack(
          children: [
            image,
            if (widget.diagnosisData.bbox != null)
              Positioned.fill(
                child: LayoutBuilder(
                  builder: (context, innerConstraints) {
                    final size = Size(
                      innerConstraints.maxWidth,
                      innerConstraints.maxHeight,
                    );
                    return BoundingBoxOverlay(
                      bbox: widget.diagnosisData.bbox!,
                      imageSize: size,
                    );
                  },
                ),
              ),
          ],
        );
      },
    );
  }
}

class _PlaceholderImage extends StatelessWidget {
  final String language;
  const _PlaceholderImage({required this.language});

  @override
  Widget build(BuildContext context) => Container(
        width: 200,
        height: 150,
        color: Colors.grey.shade200,
        child: Center(
          child: Text(
            language == 'hi' ? 'छवि अनुपलब्ध' : 'Image unavailable',
            style: const TextStyle(color: Colors.grey),
          ),
        ),
      );
}
