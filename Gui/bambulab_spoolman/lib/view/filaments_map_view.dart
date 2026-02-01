import 'package:flutter/material.dart';
import 'package:bambulab_spoolman/data/filament_model.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import 'package:bambulab_spoolman/data/web_socket_service.dart';

class FilamentsMapView extends StatefulWidget {
  const FilamentsMapView({super.key});

  @override
  State<FilamentsMapView> createState() => _FilamentsMapViewState();
}

class _FilamentsMapViewState extends State<FilamentsMapView> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fetchFilaments();
    });
  }

  void _fetchFilaments() {
    final model = context.read<FilamentMappingModel>();
    final ws = model.webSocketService;

    if (ws.isConnected) {
      ws.sendMessage("get_filaments");
      ws.messageStream.listen((message) {
        final data = jsonDecode(message);
        if (data['type'] == 'filaments_data') {
          final payload = data['payload'];

          final bambuFilaments = (payload['bambuFilaments'] as List)
              .map((e) => BambuFilament(
                    id: e['id'],
                    name: e['name'],
                    type: e['type'],
                    vendor: e['vendor'],
                  ))
              .toList();

          final spoolmanFilaments = (payload['spoolmanFilaments'] as List)
              .map((e) => SpoolmanFilament(
                    id: e['id'],
                    name: e['name'],
                    type: e['type'],
                    vendor: e['vendor'],
                  ))
              .toList();

          final mappings = Map<String, String>.from(payload['mappings']);

          final possibleMatches = Map<String, List<String>>.from(
            (payload['possibleMatches'] as Map).map(
              (k, v) => MapEntry(k, List<String>.from(v)),
            ),
          );

          model.updateFilaments(
            bambuFilaments: bambuFilaments,
            spoolmanFilaments: spoolmanFilaments,
            mappings: mappings,
            possibleMatches: possibleMatches,
          );
        }
      });
    } else {
      ws.reconnect();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<FilamentMappingModel>(
      builder: (context, model, child) {
        return Row(
          children: [
            /// Left: BambuCloud filaments
            Expanded(
              child: ListView.builder(
                itemCount: model.bambuFilaments.length,
                itemBuilder: (context, index) {
                  final bambu = model.bambuFilaments[index];
                  return Card(
                    margin: const EdgeInsets.all(8),
                    child: Padding(
                      padding: const EdgeInsets.all(8.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text("${bambu.name} (${bambu.type})",
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold)),
                          Text("Vendor: ${bambu.vendor}"),
                          const SizedBox(height: 8),
                          DropdownButton<String>(
                            value: model.getMappedSpoolman(bambu.id),
                            hint: const Text("Select Spoolman Filament"),
                            items: model.spoolmanFilaments.isNotEmpty
                                ? model.spoolmanFilaments.map((spool) {
                                    final used =
                                        model.mapping.values.contains(spool.id);
                                    return DropdownMenuItem<String>(
                                      value: spool.id,
                                      enabled: !used,
                                      child: Text(
                                        "${spool.name} (${spool.type}) - ${spool.vendor}" +
                                            (used ? " (used)" : ""),
                                      ),
                                    );
                                  }).toList()
                                : [],
                            onChanged: model.spoolmanFilaments.isNotEmpty
                                ? (spoolId) {
                                    if (spoolId != null) {
                                      model.mapFilament(bambu.id, spoolId);
                                    }
                                  }
                                : null,
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),

            /// Right: Optional: Show Spoolman filaments
            Expanded(
              child: ListView.builder(
                itemCount: model.spoolmanFilaments.length,
                itemBuilder: (context, index) {
                  final spool = model.spoolmanFilaments[index];
                  final mappedBambu = model.mapping.entries
                      .firstWhere((e) => e.value == spool.id,
                          orElse: () => MapEntry("", ""))
                      .key;
                  return ListTile(
                    title:
                        Text("${spool.name} (${spool.type}) - ${spool.vendor}"),
                    subtitle: mappedBambu.isNotEmpty
                        ? Text("Mapped to BambuID: $mappedBambu")
                        : null,
                  );
                },
              ),
            ),
          ],
        );
      },
    );
  }
}
