import 'dart:async';

import 'package:flutter/foundation.dart' show VoidCallback, kIsWeb;
import 'package:udp/udp.dart';
import 'package:web_socket_channel/status.dart' as status;
import 'package:web_socket_channel/web_socket_channel.dart';

import 'web_location_stub.dart' if (dart.library.html) 'web_location_web.dart'
    as web_location;

Future<String?> discoverWebSocketServer({int broadcastPort = 54545}) async {
  final receiver = await UDP.bind(Endpoint.any(port: Port(broadcastPort)));
  try {
    await for (final datagram
        in receiver.asStream(timeout: const Duration(seconds: 5))) {
      if (datagram == null) continue;
      final data = String.fromCharCodes(datagram.data);
      if (!data.startsWith('WS_SERVER:')) continue;

      final parts = data.split(':');
      if (parts.length == 3) return 'ws://${parts[1]}:${parts[2]}';
    }
  } finally {
    receiver.close();
  }
  return null;
}

String getBackendWebSocketUrl({int backendPort = 12346}) {
  final protocol = web_location.protocol == 'https:' ? 'wss' : 'ws';
  return '$protocol://${web_location.hostname}:$backendPort/';
}

class WebSocketService {
  WebSocketService({
    this.onConnectedCallback,
    this.onDisconnectedCallback,
  }) {
    unawaited(connect());
  }

  final VoidCallback? onConnectedCallback;
  final void Function(Object? error)? onDisconnectedCallback;
  final StreamController<String> _messageController =
      StreamController<String>.broadcast();

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _channelSubscription;
  bool _connecting = false;
  bool _closed = false;
  bool isConnected = false;

  Stream<String> get messageStream => _messageController.stream;

  Future<bool> connect() async {
    if (_closed || isConnected || _connecting) return isConnected;
    _connecting = true;
    Object? connectionError;
    try {
      final String? url =
          kIsWeb ? getBackendWebSocketUrl() : await discoverWebSocketServer();
      if (url == null) {
        connectionError = StateError('The backend could not be discovered.');
        return false;
      }

      final channel = WebSocketChannel.connect(Uri.parse(url));
      await channel.ready;
      if (_closed) {
        await channel.sink.close(status.goingAway);
        return false;
      }

      _channel = channel;
      _channelSubscription = channel.stream.listen(
        (message) => _messageController.add(message.toString()),
        onDone: () => _markDisconnected(),
        onError: _markDisconnected,
        cancelOnError: true,
      );
      isConnected = true;
      onConnectedCallback?.call();
      return true;
    } catch (error) {
      connectionError = error;
      return false;
    } finally {
      _connecting = false;
      if (!isConnected && !_closed) {
        onDisconnectedCallback?.call(connectionError);
      }
    }
  }

  void _markDisconnected([Object? error]) {
    final wasConnected = isConnected;
    isConnected = false;
    _channel = null;
    _channelSubscription = null;
    if (!_closed && (wasConnected || error != null)) {
      onDisconnectedCallback?.call(error);
    }
  }

  bool sendMessage(String message) {
    if (!isConnected) return false;
    _channel?.sink.add(message);
    return true;
  }

  Future<bool> reconnect() async {
    if (_closed || isConnected || _connecting) return isConnected;
    await _channelSubscription?.cancel();
    await _channel?.sink.close(status.goingAway);
    _channelSubscription = null;
    _channel = null;
    return connect();
  }

  Future<void> closeConnection() async {
    _closed = true;
    isConnected = false;
    await _channelSubscription?.cancel();
    await _channel?.sink.close(status.goingAway);
    await _messageController.close();
  }
}
