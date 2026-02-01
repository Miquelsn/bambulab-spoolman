import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:bambulab_spoolman/data/data_model.dart';


class LogTerminalView extends StatefulWidget {
  const LogTerminalView({super.key});

  @override
  State<LogTerminalView> createState() => _LogTerminalViewState();
}

class _LogTerminalViewState extends State<LogTerminalView> {
  Timer? _logTimer;

  @override
  void initState() {
    super.initState();
    _startLogPolling();
  }

  void _startLogPolling() {
    _logTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (mounted) {
        print("Requesting logs...");
        Provider.of<DataModel>(context, listen: false)
            .sendWebSocketMessage("get_logs");
      }
    });
  }

  @override
  void dispose() {
    _logTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DataModel>(
      builder: (context, dataModel, child) {
        final logs = dataModel.logs.reversed.toList();

        return Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.black,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.grey.shade700),
          ),
          constraints: const BoxConstraints(
            maxHeight: 300,
            minWidth: 400,
          ),
          child: ListView.builder(
            reverse: true,
            itemCount: logs.length,
            itemBuilder: (context, index) {
              return Text(
                logs[index],
                style: const TextStyle(
                  fontFamily: 'Courier',
                  color: Colors.greenAccent,
                  fontSize: 12,
                ),
              );
            },
          ),
        );
      },
    );
  }
}
