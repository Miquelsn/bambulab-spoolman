class PrinterConfiguration {
  const PrinterConfiguration({
    required this.id,
    required this.name,
    required this.ip,
    required this.enabled,
    required this.connected,
    required this.hasAccessCode,
    this.model,
  });

  factory PrinterConfiguration.fromJson(Map<String, dynamic> json) {
    return PrinterConfiguration(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Bambu printer',
      model: _text(json['model']),
      ip: json['ip']?.toString() ?? '',
      enabled: json['enabled'] != false,
      connected: json['connected'] == true,
      hasAccessCode: json['has_access_code'] == true,
    );
  }

  final String id;
  final String name;
  final String? model;
  final String ip;
  final bool enabled;
  final bool connected;
  final bool hasAccessCode;
}

String? _text(dynamic value) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? null : text;
}
