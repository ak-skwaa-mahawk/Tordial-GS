import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class TransactionFeedView extends StatefulWidget {
  final String serverUrl;
  final Duration refreshInterval;

  const TransactionFeedView({
    Key? key,
    this.serverUrl = 'http://127.0.0.1:8080',
    this.refreshInterval = const Duration(seconds: 4),
  }) : super(key: key);

  @override
  _TransactionFeedViewState createState() => _TransactionFeedViewState();
}

class _TransactionFeedViewState extends State<TransactionFeedView> {
  List<Map<String, dynamic>> _recentTxs = [];
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchTransactions();
    _timer = Timer.periodic(widget.refreshInterval, (_) => _fetchTransactions());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchTransactions() async {
    try {
      final res = await http.get(Uri.parse('${widget.serverUrl}/health'));
      if (res.statusCode == 200) {
        // Telemetry poll succeeds; fetch state from router if available
      }
    } catch (_) {}
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
        children: const [
          Text(
            'LEDGER SETTLEMENT ACTIVITY',
            style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 13),
          ),
          SizedBox(height: 8),
          Text(
            'Automated satoshi distribution active over E8 relay highways.',
            style: TextStyle(color: Colors.white38, fontSize: 12),
          ),
        ],
      ),
    );
  }
}
