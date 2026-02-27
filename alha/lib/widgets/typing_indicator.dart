import 'package:flutter/material.dart';

class TypingIndicator extends StatefulWidget {
  const TypingIndicator({super.key});

  @override
  State<TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator>
    with TickerProviderStateMixin {
  late final List<AnimationController> _controllers;
  late final List<Animation<double>> _animations;
  bool _disposed = false;

  @override
  void initState() {
    super.initState();
    _controllers = List.generate(
      3,
      (i) => AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 400),
      ),
    );
    _animations = _controllers
        .map((c) => Tween<double>(begin: 0, end: 1).animate(
              CurvedAnimation(parent: c, curve: Curves.easeInOut),
            ))
        .toList();

    _startAnimation();
  }

  void _startAnimation() async {
    while (!_disposed && mounted) {
      for (var i = 0; i < 3; i++) {
        if (_disposed || !mounted) return;
        _controllers[i].forward(from: 0);
        await Future.delayed(const Duration(milliseconds: 150));
      }
      if (_disposed || !mounted) return;
      await Future.delayed(const Duration(milliseconds: 400));
      if (_disposed || !mounted) return;
      for (final c in _controllers) {
        c.reverse();
      }
      if (_disposed || !mounted) return;
      await Future.delayed(const Duration(milliseconds: 300));
    }
  }

  @override
  void dispose() {
    _disposed = true;
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
        decoration: BoxDecoration(
          color: Colors.grey.shade200,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(16),
            topRight: Radius.circular(16),
            bottomLeft: Radius.circular(4),
            bottomRight: Radius.circular(16),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) {
            return AnimatedBuilder(
              animation: _animations[i],
              builder: (_, __) => Container(
                margin: const EdgeInsets.symmetric(horizontal: 3),
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: Colors.grey.shade500,
                  shape: BoxShape.circle,
                ),
                transform: Matrix4.translationValues(
                    0, -6 * _animations[i].value, 0),
              ),
            );
          }),
        ),
      ),
    );
  }
}
