import 'dart:async';
import 'package:flutter/foundation.dart';
import 'web_socket_service.dart';

class DataModel extends ChangeNotifier {
  final WebSocketService _webSocketService = WebSocketService();
  bool backendStatus = false;
  String lastMessage = "";
  StreamSubscription<String>? _messageSubscription;
  Timer? _connectionCheckTimer;

  DataModel() {
    // ✅ Subscribe to WebSocket messages safely
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

    // ✅ Start connection monitoring
    _startConnectionMonitoring();
  }

  void sendWebSocketMessage(String message) {
    _webSocketService.sendMessage(message);
  }

  void _processReceivedMessage(String message) {
    lastMessage = message;
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

  @override
  void dispose() {
    _messageSubscription?.cancel(); // ✅ Cancel the subscription properly
    _connectionCheckTimer?.cancel();
    _webSocketService.closeConnection();
    super.dispose();
  }
}
