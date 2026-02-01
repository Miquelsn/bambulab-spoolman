import 'dart:async';
import 'package:flutter/foundation.dart' show kIsWeb, VoidCallback;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;

// ignore: deprecated_member_use
import 'dart:html' as html;


// UDP only works on native/mobile (not web)
import 'package:udp/udp.dart';

Future<String?> discoverWebSocketServer({int broadcastPort = 54545}) async {
  final receiver = await UDP.bind(Endpoint.any(port: Port(broadcastPort)));
  final timeout = DateTime.now().add(Duration(seconds: 5));
  print("Discovering....");
  await for (final datagram in receiver.asStream(timeout: Duration(seconds: 5))) {
    print("Here");
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

String getBackendWebSocketUrl({int backendPort = 12346, String path = '/ws'}) {
  final protocol = html.window.location.protocol == 'https:' ? 'wss' : 'ws';
  final host = html.window.location.hostname;
  return '$protocol://$host:$backendPort$path';
}

class WebSocketService {
  bool isConnected = false;
  WebSocketChannel? _channel;
  final StreamController<String> _messageController = StreamController.broadcast();
  VoidCallback? onConnectedCallback;

  WebSocketService({this.onConnectedCallback}) {
    _connect();
  }

  Future<void> _connect() async {
    print("Connecting...");
    try {
      String url;

      if (kIsWeb) {
        // On Flutter web, build URL dynamically from browser location
        url = getBackendWebSocketUrl();
      } else {
        // On native/mobile, use UDP discovery
        final discoveredUrl = await discoverWebSocketServer();
        if (discoveredUrl == null) {
          print("❌ Could not discover WebSocket server.");
          return;
        }
        url = discoveredUrl;
      }

      print("Connecting to $url");
      _channel = WebSocketChannel.connect(Uri.parse(url));
      isConnected = true;
      print("✅ Connected to $url");

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
      print("Failed to connect: $e");
    }
  }

  /// Expose broadcast stream for multiple listeners
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
    _messageController.close();
    isConnected = false;
  }
}
