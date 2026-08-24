import 'dart:convert';
import 'package:http/http.dart' as http;

class TordialMeshClient {
  final String baseUrl;

  TordialMeshClient({this.baseUrl = "http://127.0.0.1:8080"});

  Future<Map<String, dynamic>> checkHealth() async {
    final response = await http.get(Uri.parse('$baseUrl/health'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to reach local mesh router daemon');
  }

  Future<Map<String, dynamic>> fetchTbaSpectrum({double tEff = 1.4}) async {
    final response = await http.get(Uri.parse('$baseUrl/api/v1/e8/tba_spectrum?t_eff=$tEff'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to query TBA spectrum');
  }

  Future<Map<String, dynamic>> dispatchBurst({
    required double queueSize,
    required double gradTemp,
    required double qber,
    required double channelLoss,
    required double effectiveStrain,
    required double coherence,
    required double entropy,
    required double phaseDrift,
    int budgetSats = 500,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/e8/dispatch'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'queue_size': queueSize,
        'grad_temp': gradTemp,
        'qber': qber,
        'channel_loss': channelLoss,
        'effective_strain': effectiveStrain,
        'coherence': coherence,
        'entropy': entropy,
        'phase_drift': phaseDrift,
        'budget_sats': budgetSats,
      }),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Burst dispatch failed');
  }
}
