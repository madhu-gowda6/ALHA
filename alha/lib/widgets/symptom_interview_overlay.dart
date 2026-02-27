import 'package:flutter/material.dart';

class SymptomInterviewOverlay extends StatefulWidget {
  final List<String> questions;
  final List<String> questionsHi;
  final String language;
  final void Function(List<Map<String, String>> answers) onComplete;

  const SymptomInterviewOverlay({
    super.key,
    required this.questions,
    required this.questionsHi,
    required this.language,
    required this.onComplete,
  });

  @override
  State<SymptomInterviewOverlay> createState() =>
      _SymptomInterviewOverlayState();
}

class _SymptomInterviewOverlayState extends State<SymptomInterviewOverlay> {
  int _currentIndex = 0;
  late final List<String> _answers;
  late final TextEditingController _controller;
  String? _validationError;

  @override
  void initState() {
    super.initState();
    _answers = List.filled(widget.questions.length, '');
    _controller = TextEditingController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _saveCurrentAnswer() {
    _answers[_currentIndex] = _controller.text.trim();
  }

  void _goToIndex(int index) {
    _saveCurrentAnswer();
    setState(() {
      _currentIndex = index;
      _controller.text = _answers[index];
      _validationError = null;
    });
  }

  void _onNext() {
    final answer = _controller.text.trim();
    if (answer.isEmpty) {
      setState(() {
        _validationError = widget.language == 'hi'
            ? 'कृपया उत्तर दें'
            : 'Please enter an answer';
      });
      return;
    }
    _answers[_currentIndex] = answer;
    setState(() => _validationError = null);

    if (_currentIndex < widget.questions.length - 1) {
      _goToIndex(_currentIndex + 1);
    }
  }

  void _onDone() {
    final answer = _controller.text.trim();
    if (answer.isEmpty) {
      setState(() {
        _validationError = widget.language == 'hi'
            ? 'कृपया उत्तर दें'
            : 'Please enter an answer';
      });
      return;
    }
    _answers[_currentIndex] = answer;

    // Validate all answers non-empty
    for (int i = 0; i < _answers.length; i++) {
      if (_answers[i].isEmpty) {
        _goToIndex(i);
        setState(() {
          _validationError = widget.language == 'hi'
              ? 'कृपया उत्तर दें'
              : 'Please enter an answer';
        });
        return;
      }
    }

    final result = List.generate(
      widget.questions.length,
      (i) => {'question': widget.questions[i], 'answer': _answers[i]},
    );
    widget.onComplete(result);
    Navigator.of(context).pop();
  }

  Future<bool> _onWillPop() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          widget.language == 'hi'
              ? 'लक्षण साक्षात्कार छोड़ें?'
              : 'Exit symptom interview?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(widget.language == 'hi' ? 'नहीं' : 'No'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(widget.language == 'hi' ? 'हाँ' : 'Yes'),
          ),
        ],
      ),
    );
    return confirmed ?? false;
  }

  String get _currentQuestion => widget.language == 'hi'
      ? (widget.questionsHi.length > _currentIndex
          ? widget.questionsHi[_currentIndex]
          : widget.questions[_currentIndex])
      : widget.questions[_currentIndex];

  @override
  Widget build(BuildContext context) {
    final total = widget.questions.length;
    final isFirst = _currentIndex == 0;
    final isLast = _currentIndex == total - 1;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final shouldPop = await _onWillPop();
        if (shouldPop && context.mounted) Navigator.of(context).pop();
      },
      child: DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.4,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) => Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: SingleChildScrollView(
            controller: scrollController,
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Drag handle
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // Header row: counter + title
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      widget.language == 'hi'
                          ? 'लक्षण जानकारी'
                          : 'Symptom Details',
                      style: const TextStyle(
                          fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.primaryContainer,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        'Q ${_currentIndex + 1} / $total',
                        style: TextStyle(
                          color:
                              Theme.of(context).colorScheme.onPrimaryContainer,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Question text
                Text(
                  _currentQuestion,
                  style: const TextStyle(fontSize: 16),
                ),
                const SizedBox(height: 16),

                // Answer field
                TextField(
                  controller: _controller,
                  maxLines: 4,
                  minLines: 2,
                  decoration: InputDecoration(
                    hintText: widget.language == 'hi'
                        ? 'अपना जवाब लिखें...'
                        : 'Type your answer...',
                    border: const OutlineInputBorder(),
                    errorText: _validationError,
                  ),
                  onChanged: (_) {
                    if (_validationError != null) {
                      setState(() => _validationError = null);
                    }
                  },
                ),
                const SizedBox(height: 20),

                // Progress dots
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(total, (i) {
                    final isCompleted =
                        i < _currentIndex && _answers[i].isNotEmpty;
                    final isCurrent = i == _currentIndex;
                    return Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: Container(
                        width: isCurrent ? 12 : 8,
                        height: isCurrent ? 12 : 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: isCurrent
                              ? Theme.of(context).colorScheme.primary
                              : isCompleted
                                  ? Theme.of(context)
                                      .colorScheme
                                      .primary
                                      .withValues(alpha: 0.5)
                                  : Colors.grey.shade300,
                        ),
                      ),
                    );
                  }),
                ),
                const SizedBox(height: 20),

                // Navigation row
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    TextButton(
                      onPressed: isFirst ? null : () => _goToIndex(_currentIndex - 1),
                      child: Text(widget.language == 'hi' ? 'पिछला' : 'Previous'),
                    ),
                    ElevatedButton(
                      onPressed: isLast ? _onDone : _onNext,
                      child: Text(
                        isLast
                            ? (widget.language == 'hi' ? 'पूर्ण' : 'Done')
                            : (widget.language == 'hi' ? 'अगला' : 'Next'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
