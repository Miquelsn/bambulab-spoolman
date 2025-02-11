import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;
import 'dart:async';

class WebSocketService {
  bool isConnected = false;
  WebSocketChannel? _channel;
  final StreamController<String> _messageController = StreamController.broadcast(); // ✅ Broadcast stream

  WebSocketService() {
    _connect();
  }

  void _connect() {
    try {
      _channel = WebSocketChannel.connect(Uri.parse("ws://localhost:12345/ws"));
      isConnected = true;
      print("✅ WebSocket connected.");

      _channel!.stream.listen(
        (message) {
          print("📩 Received message: $message");
          _messageController.add(message); // ✅ Send to broadcast stream
        },
        onDone: () {
          isConnected = false;
          print("❌ WebSocket connection closed.");
        },
        onError: (error) {
          isConnected = false;
          print("⚠️ WebSocket error: $error");
        },
      );
    } catch (e) {
      isConnected = false;
      print("⛔ Failed to connect: $e");
    }
  }

  /// ✅ **Expose a broadcast stream for multiple listeners**
  Stream<String> get messageStream => _messageController.stream;

  void sendMessage(String message) {
    if (isConnected) {
      print("📤 Sending: $message");
      _channel?.sink.add(message);
    } else {
      print("⚠️ Cannot send, WebSocket is disconnected.");
    }
  }

  void reconnect() {
    if (!isConnected) {
      print("🔄 Reconnecting WebSocket...");
      _connect();
    }
  }

  void closeConnection() {
    _channel?.sink.close(status.goingAway);
    _messageController.close(); // ✅ Close the stream controller
    isConnected = false;
  }
}
