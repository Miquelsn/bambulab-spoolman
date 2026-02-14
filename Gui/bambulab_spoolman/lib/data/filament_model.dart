import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:bambulab_spoolman/data/web_socket_service.dart';

class FilamentMappingModel extends ChangeNotifier {
  List<BambuFilament> bambuFilaments = [];
  List<SpoolmanFilament> spoolmanFilaments = [];
  Map<String, String> mapping = {}; // BambuID -> SpoolmanID
  Map<String, List<String>> possibleMatches = {}; // BambuID -> suggested spool IDs
  bool isLoading = false;

  final WebSocketService webSocketService;
  StreamSubscription<String>? _messageSubscription;

  FilamentMappingModel({required this.webSocketService}) {
    _initListener();
  }

  void _initListener() {
    _messageSubscription = webSocketService.messageStream.listen((message) {
      try {
        final data = jsonDecode(message);
        if (data['type'] == 'filaments_data') {
          processFilamentData(data['payload']);
        }
      } catch (e) {
        debugPrint("Error parsing filament data: $e");
      }
    });
  }

  void requestFilaments() {
    isLoading = true;
    notifyListeners();
    webSocketService.sendMessage("get_filaments");
  }

  void processFilamentData(Map<String, dynamic> payload) {
    final bambu = (payload['bambuFilaments'] as List)
        .map((e) => BambuFilament.fromJson(e))
        .toList();

    final spoolman = (payload['spoolmanFilaments'] as List)
        .map((e) => SpoolmanFilament.fromJson(e))
        .toList();

    final mappings = Map<String, String>.from(payload['mappings']);
    
    final matches = (payload['possibleMatches'] as Map).map(
      (k, v) => MapEntry(k.toString(), List<String>.from(v)),
    );

    updateFilaments(
      bambuFilaments: bambu,
      spoolmanFilaments: spoolman,
      mappings: mappings,
      possibleMatches: matches,
    );

    isLoading = false;
    notifyListeners();
  }

  String? getMappedSpoolman(String bambuId) => mapping[bambuId];

  void mapFilament(String bambuId, String spoolmanId) {
    mapping[bambuId] = spoolmanId;
    
    webSocketService.sendMessage(jsonEncode({
      "type": "update_mapping",
      "payload": {"bambu_id": bambuId, "spoolman_id": spoolmanId}
    }));
    
    notifyListeners();
  }

  void unmapFilament(String bambuId) {
    mapping.remove(bambuId);

    webSocketService.sendMessage(jsonEncode({
      "type": "update_mapping",
      "payload": {"bambu_id": bambuId, "spoolman_id": null}
    }));

    notifyListeners();
  }

  void updateFilaments({
    required List<BambuFilament> bambuFilaments,
    required List<SpoolmanFilament> spoolmanFilaments,
    required Map<String, String> mappings,
    required Map<String, List<String>> possibleMatches,
  }) {
    this.bambuFilaments = bambuFilaments;
    this.spoolmanFilaments = spoolmanFilaments;
    this.mapping = mappings;
    this.possibleMatches = possibleMatches;
    notifyListeners();
  }

  @override
  void dispose() {
    _messageSubscription?.cancel();
    super.dispose();
  }
}


class BambuFilament {
  final String id;
  final String name;
  final String type;
  final String vendor;

  BambuFilament({required this.id, required this.name, required this.type, required this.vendor});

  factory BambuFilament.fromJson(Map<String, dynamic> json) {
    return BambuFilament(
      id: json['id'],
      name: json['name'],
      type: json['type'],
      vendor: json['vendor'],
    );
  }
}

class SpoolmanFilament {
  final String id;
  final String name;
  final String type;
  final String vendor;

  SpoolmanFilament({required this.id, required this.name, required this.type, required this.vendor});

  factory SpoolmanFilament.fromJson(Map<String, dynamic> json) {
    return SpoolmanFilament(
      id: json['id'],
      name: json['name'],
      type: json['type'],
      vendor: json['vendor'],
    );
  }
}
