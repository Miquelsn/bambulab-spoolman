import 'dart:async';
import 'dart:convert';

import 'package:bambulab_spoolman/data/web_socket_service.dart';
import 'package:flutter/foundation.dart';

class FilamentMappingModel extends ChangeNotifier {
  FilamentMappingModel({required this.webSocketService}) {
    _messageSubscription =
        webSocketService.messageStream.listen(_handleMessage);
  }

  final WebSocketService webSocketService;
  StreamSubscription<String>? _messageSubscription;

  List<BambuFilament> bambuFilaments = [];
  List<SpoolmanFilament> spoolmanFilaments = [];
  Map<String, String> mapping = {};
  Map<String, List<String>> possibleMatches = {};
  bool isLoading = false;
  bool isSaving = false;
  String? message;
  bool messageIsError = false;

  void _handleMessage(String messageText) {
    try {
      final decoded = jsonDecode(messageText);
      if (decoded is! Map<String, dynamic>) return;
      final type = decoded['type'];
      final payload = decoded['payload'];
      if ((type == 'filaments_data' || type == 'filament_mapping_updated') &&
          payload is Map) {
        processFilamentData(Map<String, dynamic>.from(payload));
        isSaving = false;
        if (type == 'filament_mapping_updated') {
          message = 'Filament mapping saved.';
          messageIsError = false;
        }
      } else if (type == 'filament_mapping_error' && payload is Map) {
        isSaving = false;
        message =
            payload['message']?.toString() ?? 'The mapping could not be saved.';
        messageIsError = true;
      }
    } catch (error) {
      debugPrint('Error parsing filament data: $error');
      isLoading = false;
      isSaving = false;
      message = 'The backend returned unreadable filament data.';
      messageIsError = true;
    }
    notifyListeners();
  }

  void requestFilaments() {
    _requestFilaments('get_filaments');
  }

  void refreshFilaments() {
    _requestFilaments('refresh_filaments');
  }

  void _requestFilaments(String action) {
    isLoading = true;
    message = null;
    notifyListeners();
    final sent = webSocketService.sendMessage(jsonEncode({
      'action': action,
    }));
    if (!sent) {
      unawaited(_reconnectAndRequest(action));
    }
  }

  Future<void> _reconnectAndRequest(String action) async {
    final connected = await webSocketService.reconnect();
    final sent = connected &&
        webSocketService.sendMessage(jsonEncode({'action': action}));
    if (!sent) {
      isLoading = false;
      message = 'The backend is offline. Reconnect and refresh.';
      messageIsError = true;
      notifyListeners();
    }
  }

  void processFilamentData(Map<String, dynamic> payload) {
    final bambuData = payload['bambuFilaments'];
    final spoolmanData = payload['spoolmanFilaments'];
    final mappingsData = payload['mappings'];
    final matchesData = payload['possibleMatches'];
    bambuFilaments = bambuData is List
        ? bambuData
            .whereType<Map>()
            .map((item) =>
                BambuFilament.fromJson(Map<String, dynamic>.from(item)))
            .where((item) => item.id.isNotEmpty)
            .toList(growable: false)
        : [];
    spoolmanFilaments = spoolmanData is List
        ? spoolmanData
            .whereType<Map>()
            .map((item) =>
                SpoolmanFilament.fromJson(Map<String, dynamic>.from(item)))
            .where((item) => item.id.isNotEmpty)
            .toList(growable: false)
        : [];
    mapping = mappingsData is Map
        ? mappingsData.map(
            (key, value) => MapEntry(key.toString(), value.toString()),
          )
        : {};
    possibleMatches = matchesData is Map
        ? matchesData.map(
            (key, value) => MapEntry(
              key.toString(),
              value is List
                  ? value.map((item) => item.toString()).toList(growable: false)
                  : <String>[],
            ),
          )
        : {};
    isLoading = false;
    final warning = payload['warning']?.toString();
    if (warning != null && warning.isNotEmpty) {
      message = warning;
      messageIsError = true;
    }
  }

  void mapFilament(String bambuId, String spoolmanId) {
    _sendMappingUpdate(bambuId, spoolmanId);
  }

  void unmapFilament(String bambuId) {
    _sendMappingUpdate(bambuId, null);
  }

  void _sendMappingUpdate(String bambuId, String? spoolmanId) {
    isSaving = true;
    message = null;
    notifyListeners();
    final sent = webSocketService.sendMessage(jsonEncode({
      'action': 'update_mapping',
      'bambu_id': bambuId,
      'spoolman_id': spoolmanId,
    }));
    if (!sent) {
      isSaving = false;
      message = 'The backend disconnected before the mapping was saved.';
      messageIsError = true;
      notifyListeners();
    }
  }

  void clearMessage() {
    message = null;
    notifyListeners();
  }

  @override
  void dispose() {
    unawaited(_messageSubscription?.cancel());
    unawaited(webSocketService.closeConnection());
    super.dispose();
  }
}

class BambuFilament {
  const BambuFilament({
    required this.id,
    required this.name,
    required this.type,
    required this.vendor,
  });

  factory BambuFilament.fromJson(Map<String, dynamic> json) {
    return BambuFilament(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Unnamed filament',
      type: json['type']?.toString() ?? '',
      vendor: json['vendor']?.toString() ?? '',
    );
  }

  final String id;
  final String name;
  final String type;
  final String vendor;
}

class SpoolmanFilament {
  const SpoolmanFilament({
    required this.id,
    required this.name,
    required this.type,
    required this.vendor,
  });

  factory SpoolmanFilament.fromJson(Map<String, dynamic> json) {
    return SpoolmanFilament(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Unnamed spool',
      type: json['type']?.toString() ?? '',
      vendor: json['vendor']?.toString() ?? '',
    );
  }

  final String id;
  final String name;
  final String type;
  final String vendor;
}
