import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import '../config/app_config.dart';
import '../models/consultation.dart';
import '../services/auth_service.dart';
import '../widgets/severity_badge.dart';

String _animalIcon(String type) {
  switch (type.toLowerCase()) {
    case 'cattle':
      return '🐄';
    case 'poultry':
      return '🐓';
    case 'buffalo':
      return '🐃';
    default:
      return '🐾';
  }
}

String _formatTimestamp(String iso) {
  try {
    final dt = DateTime.parse(iso);
    return DateFormat('dd MMM yyyy, HH:mm').format(dt.toLocal());
  } catch (_) {
    return iso;
  }
}

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Consultation> _consultations = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchHistory();
  }

  Future<void> _fetchHistory() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final token = await AuthService().getToken();
      final uri = Uri.parse('${AppConfig.apiGatewayUrl}/api/history');
      final response = await http.get(uri, headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      });
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      if (body['success'] == true) {
        final list = (body['data'] as List)
            .map((e) => Consultation.fromJson(e as Map<String, dynamic>))
            .toList();
        setState(() {
          _consultations = list;
          _loading = false;
        });
      } else {
        final err = body['error'] as Map<String, dynamic>? ?? {};
        setState(() {
          _error = err['message'] as String? ?? 'Failed to load history';
          _loading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Network error';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    Widget body;
    if (_loading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (_error != null) {
      body = Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '$_error\nइतिहास लोड करने में त्रुटि',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _fetchHistory,
              child: const Text('Retry / पुनः प्रयास करें'),
            ),
          ],
        ),
      );
    } else if (_consultations.isEmpty) {
      body = const Center(
        child: Text(
          'No consultations yet\nअभी तक कोई परामर्श नहीं',
          textAlign: TextAlign.center,
        ),
      );
    } else {
      body = RefreshIndicator(
        onRefresh: _fetchHistory,
        child: ListView.builder(
          itemCount: _consultations.length,
          itemBuilder: (context, index) {
            final c = _consultations[index];
            return ListTile(
              leading: Text(
                _animalIcon(c.animalType),
                style: const TextStyle(fontSize: 28),
              ),
              title: Text(
                c.diseaseName?.isNotEmpty == true
                    ? c.diseaseName!
                    : 'Knowledge Query',
              ),
              subtitle: Text(_formatTimestamp(c.timestamp)),
              trailing: SeverityBadge(level: c.severity ?? 'NONE'),
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => _ConsultationDetail(consultation: c),
                  ),
                );
              },
            );
          },
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('ALHA — History / ALHA — इतिहास'),
      ),
      body: body,
    );
  }
}

class _ConsultationDetail extends StatelessWidget {
  final Consultation consultation;
  const _ConsultationDetail({required this.consultation});

  @override
  Widget build(BuildContext context) {
    List<dynamic> citations = [];
    try {
      citations = jsonDecode(consultation.kbCitations ?? '[]') as List;
    } catch (_) {}

    final vetText = (consultation.vetAssigned?.isNotEmpty == true &&
            consultation.vetAssigned != 'none')
        ? consultation.vetAssigned!
        : 'No vet assigned / कोई पशु चिकित्सक नियुक्त नहीं';

    return Scaffold(
      appBar: AppBar(
        title: Text(consultation.diseaseName?.isNotEmpty == true
            ? consultation.diseaseName!
            : 'Consultation Detail'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  _animalIcon(consultation.animalType),
                  style: const TextStyle(fontSize: 36),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    consultation.diseaseName?.isNotEmpty == true
                        ? consultation.diseaseName!
                        : 'Knowledge Query',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ),
              ],
            ),
            if (consultation.confidenceScore != null) ...[
              const SizedBox(height: 4),
              Text(
                '${consultation.confidenceScore!.toStringAsFixed(1)}% confidence',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
            const SizedBox(height: 12),
            SeverityBadge(level: consultation.severity ?? 'NONE'),
            const SizedBox(height: 16),
            const Divider(),
            _DetailRow(label: 'Vet / पशु चिकित्सक', value: vetText),
            const Divider(),
            if (consultation.treatmentSummary?.isNotEmpty == true) ...[
              Text(
                'Treatment / उपचार',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(consultation.treatmentSummary!),
              const Divider(),
            ],
            if (citations.isNotEmpty) ...[
              Text(
                'Sources / स्रोत',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              ...citations.map((c) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('• '),
                        Expanded(child: Text(c.toString())),
                      ],
                    ),
                  )),
              const Divider(),
            ],
            _DetailRow(
              label: 'Date / दिनांक',
              value: _formatTimestamp(consultation.timestamp),
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;
  const _DetailRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 140,
            child: Text(
              label,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
