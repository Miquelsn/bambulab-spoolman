import 'dart:async';
import 'package:flutter/foundation.dart';
import 'web_socket_service.dart';
import 'dart:convert';

class DataModel extends ChangeNotifier {
  late final WebSocketService _webSocketService;
  bool backendStatus = false;
  String lastMessage = "";
  StreamSubscription<String>? _messageSubscription;
  Timer? _connectionCheckTimer;
  List<String> logs = []; // Add this in your DataModel
  List<Map<String, dynamic>> tasks = [];

  DataModel() {
    _webSocketService = WebSocketService(
      onConnectedCallback: _onWebSocketConnected,
    );
    _messageSubscription = _webSocketService.messageStream.listen(
      (message) {
        print("📩 Message received: $message");
        backendStatus = true;
        _processReceivedMessage(message);
      },
      onDone: _handleDisconnection,
      onError: (error) {
        print("⚠️ WebSocket error: $error");
        _handleDisconnection();
      },
    );

    _startConnectionMonitoring();
  }

  void sendWebSocketMessage(String message) {
    _webSocketService.sendMessage(message);
  }

  void _processReceivedMessage(String message) {
    lastMessage = message;

    try {
      final decoded = json.decode(message);

      if (decoded is Map<String, dynamic>) {
        final type = decoded['type'];
        final payload = decoded['payload'];

        if (type == 'logs' &&
            payload is List &&
            payload.isNotEmpty &&
            payload.first is String) {
          logs = List<String>.from(payload);
          //print("📝 Logs updated: ${logs.length} lines");
        } else if (type == 'tasks' &&
            payload is List &&
            payload.isNotEmpty &&
            payload.first is Map) {
          tasks = List<Map<String, dynamic>>.from(payload);
          //print("✅ Tasks updated: ${tasks.length} items");
        }
      }
    } catch (e) {
      print(" Failed to parse WebSocket message: $e");
    }

    notifyListeners();
  }

  void _handleDisconnection() {
    backendStatus = false;
    notifyListeners();
    _attemptReconnect();
  }

  void _startConnectionMonitoring() {
    _connectionCheckTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (!_webSocketService.isConnected) {
        _handleDisconnection();
      }
    });
  }

  void _attemptReconnect() async {
    print("🔄 Attempting to reconnect...");
    await Future.delayed(const Duration(seconds: 3));
    _webSocketService.reconnect();
  }

  void _onWebSocketConnected() {
    backendStatus = true;
    notifyListeners(); // 👈 force UI update
  }

  void addLog(String log) {
    logs.add(log);
    if (logs.length > 1000) logs.removeAt(0); // Trim old logs
    notifyListeners();
  }

  @override
  void dispose() {
    _messageSubscription?.cancel(); // ✅ Cancel the subscription properly
    _connectionCheckTimer?.cancel();
    _webSocketService.closeConnection();
    super.dispose();
  }
}
