class PrinterStatus {
  const PrinterStatus({
    required this.id,
    required this.name,
    required this.state,
    required this.progress,
    required this.enabled,
    required this.connected,
    this.model,
    this.taskName,
  });

  factory PrinterStatus.fromJson(Map<String, dynamic> json) {
    return PrinterStatus(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Bambu printer',
      model: _text(json['model']),
      state: json['state']?.toString() ?? 'OFFLINE',
      progress: ((json['progress'] as num?)?.round().clamp(0, 100) ?? 0).toInt(),
      enabled: json['enabled'] != false,
      connected: json['connected'] == true,
      taskName: _text(json['task_name']),
    );
  }

  final String id;
  final String name;
  final String? model;
  final String state;
  final int progress;
  final bool enabled;
  final bool connected;
  final String? taskName;

  bool get isPrinting => state == 'PRINTING' || state == 'PREPARING';
  String get displayState => !enabled
      ? 'Disabled'
      : !connected
          ? 'Offline'
          : state.toLowerCase().replaceFirstMapped(
                RegExp(r'^.'),
                (match) => match.group(0)!.toUpperCase(),
              );
}

String? _text(dynamic value) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? null : text;
}
