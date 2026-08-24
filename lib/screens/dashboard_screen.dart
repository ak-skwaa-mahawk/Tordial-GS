import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../widgets/e8_highway_matrix.dart';
import '../widgets/burst_dispatch_form.dart';

class DashboardScreen extends StatefulWidget {
  final String serverUrl;

  const DashboardScreen({
    Key? key,
    this.serverUrl = 'http://127.0.0.1:8080',
  }) : super(key: key);

  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic> _health = {};
  Map<String, dynamic> _tbaSpectrum = {};
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchData();
    _timer = Timer.periodic(const Duration(seconds: 3), (_) => _fetchData());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchData() async {
    try {
      final healthRes = await http.get(Uri.parse('${widget.serverUrl}/health'));
      if (healthRes.statusCode == 200) {
        setState(() => _health = jsonDecode(healthRes.body));
      }

      final tbaRes = await http.get(Uri.parse('${widget.serverUrl}/api/v1/e8/tba_spectrum?t_eff=1.4'));
      if (tbaRes.statusCode == 200) {
        setState(() => _tbaSpectrum = jsonDecode(tbaRes.body));
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final nodeId = _health['node_id'] ?? 'CONNECTING...';
    final totalLoad = _tbaSpectrum['total_queue_load']?.toStringAsFixed(3) ?? '0.000';
    final casimir = _tbaSpectrum['ground_state_energy']?.toStringAsFixed(4) ?? '0.0000';

    return Scaffold(
      backgroundColor: const Color(0xFF0A0E14),
      appBar: AppBar(
        title: const Text('TORDIAL SOVEREIGN NODE', style: TextStyle(letterSpacing: 1.2, fontSize: 16)),
        backgroundColor: const Color(0xFF0F141C),
        elevation: 0,
        actions: [
          Center(
            child: Padding(
              padding: const EdgeInsets.only(right: 16.0),
              child: Text(
                nodeId,
                style: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 12),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: _MetricCard(
                    title: 'TBA QUEUE LOAD',
                    value: totalLoad,
                    color: Colors.blueAccent,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _MetricCard(
                    title: 'CASIMIR ENERGY',
                    value: casimir,
                    color: Colors.amberAccent,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            E8HighwayMatrixView(serverUrl: widget.serverUrl),
            const SizedBox(height: 16),
            BurstDispatchForm(
              serverUrl: widget.serverUrl,
              onDispatched: _fetchData,
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final Color color;

  const _MetricCard({
    required this.title,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14.0),
      decoration: BoxDecoration(
        color: const Color(0xFF0F141C),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(color: Colors.white54, fontSize: 11, fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          Text(value, style: TextStyle(color: color, fontSize: 18, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
