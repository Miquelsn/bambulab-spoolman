class LogEvent {
  const LogEvent({
    required this.timestamp,
    required this.level,
    required this.event,
    required this.subsystem,
    required this.message,
    this.printerId,
    this.taskId,
  });

  factory LogEvent.fromJson(Map<String, dynamic> json) {
    return LogEvent(
      timestamp: DateTime.tryParse(json['timestamp']?.toString() ?? ''),
      level: json['level']?.toString().toLowerCase() ?? 'info',
      event: json['event']?.toString() ?? 'service_message',
      subsystem: json['subsystem']?.toString() ?? 'service',
      message: json['message']?.toString() ?? '',
      printerId: _text(json['printer_id']),
      taskId: _text(json['task_id']),
    );
  }

  final DateTime? timestamp;
  final String level;
  final String event;
  final String subsystem;
  final String message;
  final String? printerId;
  final String? taskId;

  bool get isProblem => level == 'error' || level == 'warning';

  String get timeLabel {
    final value = timestamp?.toLocal();
    if (value == null) return 'Time unavailable';
    return '${value.hour.toString().padLeft(2, '0')}:'
        '${value.minute.toString().padLeft(2, '0')}:'
        '${value.second.toString().padLeft(2, '0')}';
  }
}

String? _text(dynamic value) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? null : text;
}
