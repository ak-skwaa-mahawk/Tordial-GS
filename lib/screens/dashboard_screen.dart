import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../widgets/e8_highway_matrix.dart';
import '../widgets/burst_dispatch_form.dart';
import '../widgets/peer_health_matrix.dart';

class DashboardScreen extends StatefulWidget {
  final String wsUrl;
  final String serverUrl;

  const DashboardScreen({
    Key? key,
    this.wsUrl = 'ws://127.0.0.1:8080/ws/telemetry',
    this.serverUrl = 'http://127.0.0.1:8080',
  }) : super(key: key);

  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Map<String, dynamic> _liveData = {};
  bool _connected = false;

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
  }

  void _connectWebSocket() {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(widget.wsUrl));
      _subscription = _channel?.stream.listen(
        (message) {
          final data = jsonDecode(message);
          setState(() {
            _liveData = data;
            _connected = true;
          });
        },
        onError: (_) => _reconnect(),
        onDone: () => _reconnect(),
      );
    } catch (_) {
      _reconnect();
    }
  }

  void _reconnect() {
    setState(() => _connected = false);
    _subscription?.cancel();
    _channel?.sink.close();
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) _connectWebSocket();
    });
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _channel?.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final nodeId = _liveData['node_id'] ?? 'CONNECTING...';
    final totalLoad = (_liveData['total_queue_load'] as num?)?.toStringAsFixed(3) ?? '0.000';
    final casimir = (_liveData['casimir_energy'] as num?)?.toStringAsFixed(4) ?? '0.0000';
    final healthyPeers = _liveData['healthy_peers'] as List<dynamic>? ?? [];

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
              child: Row(
                children: [
                  Icon(Icons.bolt, size: 14, color: _connected ? Colors.greenAccent : Colors.redAccent),
                  const SizedBox(width: 4),
                  Text(
                    nodeId,
                    style: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 12),
                  ),
                ],
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
                    title: 'TBA QUEUE LOAD (LIVE)',
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
            PeerHealthMatrixView(healthyPeers: healthyPeers),
            const SizedBox(height: 16),
            E8HighwayMatrixView(serverUrl: widget.serverUrl),
            const SizedBox(height: 16),
            BurstDispatchForm(serverUrl: widget.serverUrl),
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
