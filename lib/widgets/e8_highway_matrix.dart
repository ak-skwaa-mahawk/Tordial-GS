import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class E8HighwayMatrixView extends StatefulWidget {
  final String serverUrl;
  final Duration refreshInterval;

  const E8HighwayMatrixView({
    Key? key,
    this.serverUrl = 'http://127.0.0.1:8080',
    this.refreshInterval = const Duration(seconds: 2),
  }) : super(key: key);

  @override
  _E8HighwayMatrixViewState createState() => _E8HighwayMatrixViewState();
}

class _E8HighwayMatrixViewState extends State<E8HighwayMatrixView> {
  List<double> _queueDepths = List.filled(240, 0.0);
  Timer? _poller;
  int _activeCount = 0;
  bool _connected = false;

  @override
  void initState() {
    super.initState();
    _fetchHighwayData();
    _poller = Timer.periodic(widget.refreshInterval, (_) => _fetchHighwayData());
  }

  @override
  void dispose() {
    _poller?.cancel();
    super.dispose();
  }

  Future<void> _fetchHighwayData() async {
    try {
      final res = await http.get(Uri.parse('${widget.serverUrl}/api/v1/e8/highways'));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        setState(() {
          _queueDepths = List<double>.from(data['queue_depths'].map((x) => (x as num).toDouble()));
          _activeCount = data['active_highways'];
          _connected = true;
        });
      }
    } catch (_) {
      setState(() => _connected = false);
    }
  }

  Color _getHighwayColor(double depth) {
    if (depth <= 0.05) return Colors.grey.shade900;
    if (depth < 0.3) return Colors.blue.shade700;
    if (depth < 0.7) return Colors.cyanAccent.shade700;
    if (depth < 1.5) return Colors.amber.shade600;
    return Colors.deepOrangeAccent;
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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'E8 ROOT HIGHWAYS (240)',
                style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 13),
              ),
              Row(
                children: [
                  Icon(Icons.circle, size: 10, color: _connected ? Colors.greenAccent : Colors.redAccent),
                  const SizedBox(width: 6),
                  Text(
                    '$_activeCount Active',
                    style: const TextStyle(color: Colors.white54, fontSize: 12),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 16,
              mainAxisSpacing: 3,
              crossAxisSpacing: 3,
            ),
            itemCount: 240,
            itemBuilder: (context, idx) {
              final depth = _queueDepths[idx];
              return AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                decoration: BoxDecoration(
                  color: _getHighwayColor(depth),
                  borderRadius: BorderRadius.circular(2),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
