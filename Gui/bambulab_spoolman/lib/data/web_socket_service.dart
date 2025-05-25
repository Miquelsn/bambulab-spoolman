import 'dart:ui';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;
import 'dart:async';
import 'package:udp/udp.dart';

Future<String?> discoverWebSocketServer({int broadcastPort = 54545}) async {
  final receiver = await UDP.bind(Endpoint.any(port: Port(broadcastPort)));
  final timeout = DateTime.now().add(Duration(seconds: 5));

  await for (final datagram in receiver.asStream(timeout: Duration(seconds: 5))) {
    final data = String.fromCharCodes(datagram!.data);
    if (data.startsWith('WS_SERVER:')) {
      final parts = data.split(':');
      if (parts.length == 3) {
        final ip = parts[1];
        final port = parts[2];
        receiver.close();
        return 'ws://$ip:$port';
      }
    }
    if (DateTime.now().isAfter(timeout)) break;
  }

  receiver.close();
  return null;
}


class WebSocketService {
  bool isConnected = false;
  WebSocketChannel? _channel;
  final StreamController<String> _messageController = StreamController.broadcast(); // ✅ Broadcast stream
  VoidCallback? onConnectedCallback;
  String url = "A";

  WebSocketService({this.onConnectedCallback}) {
    _connect();
  }

  
Future<void> _connect() async {
  try {
    final discoveredUrl = await discoverWebSocketServer(); // 👈 call UDP discovery
    if (discoveredUrl == null) {
      print("❌ Could not discover server.");
      return;
    }
    url = discoveredUrl; // Store the discovered URL
    print("Discovered WebSocket server at: $discoveredUrl");
    _channel = WebSocketChannel.connect(Uri.parse(discoveredUrl));
    isConnected = true;
    print("✅ Connected to $discoveredUrl");
    onConnectedCallback?.call();

    _channel!.stream.listen(
      (message) {
        print("📩 Received message: $message");
        _messageController.add(message);
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
      print("Discovered WebSocket server at: $url");

      _connect();
    }
  }

  void closeConnection() {
    _channel?.sink.close(status.goingAway);
    _messageController.close(); // ✅ Close the stream controller
    isConnected = false;
  }
}
