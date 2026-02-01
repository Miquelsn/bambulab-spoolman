import 'package:flutter/foundation.dart';

import 'package:bambulab_spoolman/data/web_socket_service.dart';

class FilamentMappingModel extends ChangeNotifier {
  List<BambuFilament> bambuFilaments = [];
  List<SpoolmanFilament> spoolmanFilaments = [];
  Map<String, String> mapping = {}; // BambuID -> SpoolmanID
  Map<String, List<String>> possibleMatches = {}; // BambuID -> suggested spool IDs

  late WebSocketService webSocketService;

  FilamentMappingModel({required this.webSocketService});

  String? getMappedSpoolman(String bambuId) => mapping[bambuId];

  void mapFilament(String bambuId, String spoolmanId) {
    mapping[bambuId] = spoolmanId;
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
}


class BambuFilament {
  final String id;
  final String name;
  final String type;
  final String vendor;

  BambuFilament({required this.id, required this.name, required this.type, required this.vendor});
}

class SpoolmanFilament {
  final String id;
  final String name;
  final String type;
  final String vendor;

  SpoolmanFilament({required this.id, required this.name, required this.type, required this.vendor});
}
