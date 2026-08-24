import 'package:flutter/material.dart';

class PeerHealthMatrixView extends StatelessWidget {
  final List<dynamic> healthyPeers;
  final List<String> allPeers = const [
    'HEADSCALE-ALPHA',
    'HEADSCALE-BETA',
    'HEADSCALE-GAMMA',
    'ALPHA',
    'BETA',
    'GAMMA',
  ];

  const PeerHealthMatrixView({
    Key? key,
    required this.healthyPeers,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14.0),
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
                'E8 MESH PEER FAILOVER MATRIX',
                style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 12),
              ),
              Text(
                '${healthyPeers.length}/${allPeers.length} ACTIVE',
                style: TextStyle(
                  color: healthyPeers.length == allPeers.length ? Colors.greenAccent : Colors.amberAccent,
                  fontWeight: FontWeight.bold,
                  fontSize: 11,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8.0,
            runSpacing: 8.0,
            children: allPeers.map((peer) {
              final isOnline = healthyPeers.contains(peer);
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
                decoration: BoxDecoration(
                  color: isOnline ? Colors.greenAccent.withOpacity(0.12) : Colors.redAccent.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: isOnline ? Colors.greenAccent.withOpacity(0.4) : Colors.redAccent.withOpacity(0.4),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.circle,
                      size: 8,
                      color: isOnline ? Colors.greenAccent : Colors.redAccent,
                    ),
                    const SizedBox(width: 5),
                    Text(
                      peer,
                      style: TextStyle(
                        color: isOnline ? Colors.white : Colors.white54,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
