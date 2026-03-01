import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';

import '../config/theme.dart';
import '../models/message.dart';

class TextBubble extends StatelessWidget {
  final Message message;

  const TextBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    final isError = message.type == MessageType.error;

    final bgColor = isError
        ? Colors.red.shade50
        : isUser
            ? primaryGreen
            : Colors.white;
    final textColor = isUser ? Colors.white : Colors.black87;
    final borderRadius = BorderRadius.only(
      topLeft: const Radius.circular(16),
      topRight: const Radius.circular(16),
      bottomLeft: isUser ? const Radius.circular(16) : const Radius.circular(4),
      bottomRight: isUser ? const Radius.circular(4) : const Radius.circular(16),
    );

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.85,
        ),
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: borderRadius,
            border: isError ? Border.all(color: Colors.red.shade200) : null,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.06),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              isUser
                  ? Text(
                      message.content,
                      style: GoogleFonts.notoSansDevanagari(
                        color: textColor,
                        fontSize: 15,
                      ),
                    )
                  : MarkdownBody(
                      data: message.content,
                      shrinkWrap: true,
                      softLineBreak: true,
                      styleSheet: _buildStyleSheet(context, textColor, isError),
                    ),
              const SizedBox(height: 4),
              Text(
                _formatTime(message.timestamp),
                style: TextStyle(
                  color: isUser ? Colors.white70 : Colors.black38,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  MarkdownStyleSheet _buildStyleSheet(
      BuildContext context, Color textColor, bool isError) {
    final base = GoogleFonts.notoSansDevanagari(
      color: isError ? Colors.red.shade800 : textColor,
      fontSize: 15,
    );
    return MarkdownStyleSheet.fromTheme(Theme.of(context)).copyWith(
      p: base,
      h1: base.copyWith(fontSize: 18, fontWeight: FontWeight.bold),
      h2: base.copyWith(fontSize: 16, fontWeight: FontWeight.bold),
      h3: base.copyWith(fontSize: 15, fontWeight: FontWeight.bold),
      strong: base.copyWith(fontWeight: FontWeight.bold),
      em: base.copyWith(fontStyle: FontStyle.italic),
      listBullet: base,
      tableHead: base.copyWith(fontWeight: FontWeight.bold),
      tableBody: base,
      tableBorder: TableBorder.all(color: Colors.grey.shade300, width: 1),
      tableHeadAlign: TextAlign.left,
      tableCellsPadding:
          const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      blockquote: base.copyWith(color: Colors.grey.shade700),
      code: GoogleFonts.robotoMono(
        fontSize: 13,
        backgroundColor: Colors.grey.shade100,
        color: Colors.black87,
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}
