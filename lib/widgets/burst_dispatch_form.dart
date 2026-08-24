import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class BurstDispatchForm extends StatefulWidget {
  final String serverUrl;
  final VoidCallback? onDispatched;

  const BurstDispatchForm({
    Key? key,
    this.serverUrl = 'http://127.0.0.1:8080',
    this.onDispatched,
  }) : super(key: key);

  @override
  _BurstDispatchFormState createState() => _BurstDispatchFormState();
}

class _BurstDispatchFormState extends State<BurstDispatchForm> {
  double _queueSize = 4.0;
  double _effectiveStrain = 3.5;
  double _qber = 0.01;
  double _channelLoss = 0.02;
  double _phaseDrift = 0.001;
  int _budgetSats = 500;
  bool _loading = false;
  String? _lastResult;

  Future<void> _sendBurst() async {
    setState(() => _loading = true);
    try {
      final res = await http.post(
        Uri.parse('${widget.serverUrl}/api/v1/e8/dispatch'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'queue_size': _queueSize,
          'grad_temp': 3.0,
          'qber': _qber,
          'channel_loss': _channelLoss,
          'effective_strain': _effectiveStrain,
          'coherence': 0.98,
          'entropy': 0.2,
          'phase_drift': _phaseDrift,
          'budget_sats': _budgetSats,
        }),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final status = data['dispatch']?['decision']?['status'] ?? 'UNKNOWN';
        final root = data['dispatch']?['decision']?['selected_root_index'] ?? 'N/A';
        final txId = data['settlement']?['tx_id'] ?? 'N/A';
        setState(() {
          _lastResult = '✅ Root: $root | Status: $status | TX: $txId';
        });
        widget.onDispatched?.call();
      } else {
        setState(() => _lastResult = '❌ Error ${res.statusCode}');
      }
    } catch (e) {
      setState(() => _lastResult = '❌ Dispatch failed: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: const Color(0xFF0F141C),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'MANUAL TELEMETRY BURST DISPATCH',
            style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 13),
          ),
          const SizedBox(height: 12),
          _buildSlider('Queue Size', _queueSize, 0.0, 10.0, (v) => setState(() => _queueSize = v)),
          _buildSlider('Effective Strain (%)', _effectiveStrain, 0.0, 10.0, (v) => setState(() => _effectiveStrain = v)),
          _buildSlider('QBER (Quantum Error)', _qber, 0.0, 0.2, (v) => setState(() => _qber = v)),
          _buildSlider('Phase Drift', _phaseDrift, -0.015, 0.015, (v) => setState(() => _phaseDrift = v)),
          const SizedBox(height: 12),
          ElevatedButton(
            onPressed: _loading ? null : _sendBurst,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.cyanAccent.shade700,
              foregroundColor: Colors.black,
              minimumSize: const Size.fromHeight(42),
            ),
            child: _loading
                ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                : const Text('DISPATCH E8 BURST', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.1)),
          ),
          if (_lastResult != null) ...[
            const SizedBox(height: 10),
            Text(_lastResult!, style: const TextStyle(color: Colors.cyanAccent, fontSize: 12)),
          ]
        ],
      ),
    );
  }

  Widget _buildSlider(String label, double val, double min, double max, ValueChanged<double> onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(color: Colors.white54, fontSize: 11)),
            Text(val.toStringAsFixed(3), style: const TextStyle(color: Colors.white70, fontSize: 11)),
          ],
        ),
        SliderTheme(
          data: SliderTheme.of(context).copyWith(
            trackHeight: 2,
            thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
          ),
          child: Slider(value: val, min: min, max: max, onChanged: onChanged),
        ),
      ],
    );
  }
}
