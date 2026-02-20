import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'web_socket_service.dart';

class DataModel extends ChangeNotifier {
  final WebSocketService webSocketService;

  bool backendStatus = false;
  String lastMessage = "";
  StreamSubscription<String>? _messageSubscription;
  Timer? _connectionCheckTimer;

  List<String> logs = [];
  List<Map<String, dynamic>> tasks = [];

  // Local settings
  String printerIp = "";
  String spoolmanIp = "";
  int spoolmanPort = 0;

  // BambuCloud settings
  String email = "";
  String password = "";

  String bambuLoginStatus = "";
  bool isLoggingIn = false;
  String verificationCode = "";
  bool showVerificationField = false;
  String _pendingTfaKey = "";

  DataModel({required this.webSocketService}) {
    _initWebSocket();
    _startConnectionMonitoring();
  }

  /// Initialize WebSocket subscription
  void _initWebSocket() {
    // Subscribe to messages
    _messageSubscription = webSocketService.messageStream.listen(
      (message) {
        backendStatus = true;
        _processReceivedMessage(message);
      },
      onDone: _handleDisconnection,
      onError: (error) {
        backendStatus = false;
        print("⚠️ WebSocket error: $error");
        _handleDisconnection();
      },
    );

    // Trigger UI update if already connected
    if (webSocketService.isConnected) {
      _onWebSocketConnected();
    }
  }

  /// Send a message via WebSocket
  void sendWebSocketMessage(String message) {
    webSocketService.sendMessage(message);
  }

  /// Update local settings and notify backend
  void updateLocalSettings({
    required String newPrinterIp,
    required String newSpoolmanIp,
    required int newSpoolmanPort,
  }) {
    printerIp = newPrinterIp;
    spoolmanIp = newSpoolmanIp;
    spoolmanPort = newSpoolmanPort;

    sendWebSocketMessage(jsonEncode({
      "type": "update_local_settings",
      "payload": {
        "printer_ip": printerIp,
        "spoolman_ip": spoolmanIp,
        "spoolman_port": spoolmanPort,
      }
    }));

    notifyListeners();
  }

  /// Update BambuCloud credentials and start login
  void updateBambuCredentials({
    required String newEmail,
    required String newPassword,
  }) {
    email = newEmail;
    password = newPassword;
    isLoggingIn = true;
    showVerificationField = false;
    notifyListeners();

    sendWebSocketMessage(jsonEncode({
      "type": "bambu_login",
      "payload": {
        "email": email,
        "password": password,
      }
    }));
  }

  /// Process messages received from WebSocket
  void _processReceivedMessage(String message) {
    lastMessage = message;

    try {
      final decoded = json.decode(message);
      if (decoded is Map<String, dynamic>) {
        final type = decoded['type'];
        final payload = decoded['payload'];

        switch (type) {
          case 'logs':
            if (payload is List && payload.isNotEmpty) {
              logs = List<String>.from(payload.whereType<String>());
            }
            break;

          case 'tasks':
            if (payload is List && payload.isNotEmpty) {
              tasks = List<Map<String, dynamic>>.from(
                  payload.whereType<Map<String, dynamic>>());
            }
            break;

          case 'local_settings':
            if (payload is Map<String, dynamic>) {
              printerIp = payload['printer_ip'] ?? "";
              spoolmanIp = payload['spoolman_ip'] ?? "";
              spoolmanPort = payload['spoolman_port'] ?? 0;
            }
            break;

          case 'bambucloud_settings':
            if (payload is Map<String, dynamic>) {
              email = payload['email'] ?? "";
              password = payload['password'] ?? "";
            }
            break;

          case 'bambucloud_login':
            bambuLoginStatus = payload.toString();
            isLoggingIn = false;
            showVerificationField = bambuLoginStatus == "needs_verification_code";
            if (bambuLoginStatus == "needs_tfa") {
              _pendingTfaKey = decoded['tfa_key'] ?? '';
            }
            break;
        }
      }
    } catch (e) {
      print("Failed to parse WebSocket message: $e");
    }

    notifyListeners();
  }

  /// Send verification code for BambuCloud login
  void sendVerificationCode(String code) {
    verificationCode = code;
    isLoggingIn = true;
    notifyListeners();

    sendWebSocketMessage(jsonEncode({
      "type": "bambu_login",
      "payload": {
        "email": email,
        "password": password,
        "code": verificationCode,
      }
    }));
  }

  /// Send TFA code (authenticator app) for BambuCloud login
  void sendTfaCode(String code) {
    isLoggingIn = true;
    notifyListeners();

    sendWebSocketMessage(jsonEncode({
      "type": "bambu_login",
      "payload": {
        "email": email,
        "password": password,
        "tfa_code": code,
        "tfa_key": _pendingTfaKey,
      }
    }));
  }

  /// Handle WebSocket disconnection
  void _handleDisconnection() {
    backendStatus = false;
    notifyListeners();
    _attemptReconnect();
  }

  /// Start periodic check for WebSocket connection
  void _startConnectionMonitoring() {
    _connectionCheckTimer =
        Timer.periodic(const Duration(seconds: 5), (_) {
      if (!webSocketService.isConnected) {
        _handleDisconnection();
      }
    });
  }

  /// Attempt to reconnect WebSocket
  Future<void> _attemptReconnect() async {
    print("🔄 Attempting to reconnect...");
    await Future.delayed(const Duration(seconds: 3));
    webSocketService.reconnect();
  }

  /// Called when WebSocket is connected
  void _onWebSocketConnected() {
    backendStatus = true;
    notifyListeners();
  }

  /// Add a log locally
  void addLog(String log) {
    logs.add(log);
    if (logs.length > 1000) logs.removeAt(0); // Trim old logs
    notifyListeners();
  }

  @override
  void dispose() {
    _messageSubscription?.cancel();
    _connectionCheckTimer?.cancel();
    super.dispose();
  }
}
