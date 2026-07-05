class FilamentUsage {
  const FilamentUsage({
    required this.id,
    required this.weight,
    this.name,
    this.type,
    this.vendor,
    this.spoolId,
    this.spoolName,
    this.spoolType,
    this.spoolVendor,
    this.reportStatus,
    this.reportError,
  });

  factory FilamentUsage.fromJson(Map<String, dynamic> json) {
    return FilamentUsage(
      id: _text(json['filamentId']) ?? 'Unknown',
      weight: _number(json['weight']),
      name: _text(json['filament_name']),
      type: _text(json['filament_type']),
      vendor: _text(json['filament_vendor']),
      spoolId: _text(json['spoolman_spool_id']),
      spoolName: _text(json['spoolman_spool_name']),
      spoolType: _text(json['spoolman_filament_type']),
      spoolVendor: _text(json['spoolman_vendor']),
      reportStatus: _text(json['report_status']),
      reportError: _text(json['error']),
    );
  }

  final String id;
  final double weight;
  final String? name;
  final String? type;
  final String? vendor;
  final String? spoolId;
  final String? spoolName;
  final String? spoolType;
  final String? spoolVendor;
  final String? reportStatus;
  final String? reportError;

  String get displayName => name ?? 'Filament $id';

  String? get details {
    final values = [vendor, type].whereType<String>().toSet().toList();
    return values.isEmpty ? null : values.join(' · ');
  }

  bool get isReported =>
      reportStatus == 'reported' || reportStatus == 'corrected';

  String get spoolLabel {
    if (spoolId == null) return 'Not reported to Spoolman';
    final name = spoolName == null ? '' : ' · $spoolName';
    return 'Spool #$spoolId$name';
  }

  String? get spoolDetails {
    final values = [spoolVendor, spoolType].whereType<String>().toSet().toList();
    return values.isEmpty ? null : values.join(' · ');
  }
}

class SavedTask {
  const SavedTask({
    required this.historyId,
    required this.modelName,
    required this.status,
    required this.totalWeight,
    required this.progress,
    required this.filaments,
    required this.usageIsEstimated,
    this.startTime,
    this.endTime,
    this.imageUrl,
    this.printerName,
    this.printerModel,
  });

  factory SavedTask.fromJson(Map<String, dynamic> json) {
    final reported = _mapList(json['reported_filament']);
    final theoretical = _mapList(json['teoric_filaments']);
    final usageIsEstimated = reported.isEmpty;
    final usage = usageIsEstimated ? theoretical : reported;

    return SavedTask(
      historyId: _text(json['history_id']) ?? '',
      modelName: _text(json['model_name']) ?? 'Unknown task',
      status: _text(json['status']) ?? 'Unknown',
      totalWeight: _number(json['total_weight']),
      progress: _number(json['percent_complete']).round().clamp(0, 100),
      startTime: parseTaskDate(json['start_time']),
      endTime: parseTaskDate(json['end_time']),
      imageUrl: _text(json['image_cover_url']),
      printerName: _text(json['printer_name']),
      printerModel: _text(json['printer_model']),
      filaments: usage.map(FilamentUsage.fromJson).toList(growable: false),
      usageIsEstimated: usageIsEstimated,
    );
  }

  final String modelName;
  final String historyId;
  final String status;
  final double totalWeight;
  final int progress;
  final DateTime? startTime;
  final DateTime? endTime;
  final String? imageUrl;
  final String? printerName;
  final String? printerModel;
  final List<FilamentUsage> filaments;
  final bool usageIsEstimated;

  DateTime? get sortTime => endTime ?? startTime;

  double get usedWeight => filaments.fold(0, (sum, item) => sum + item.weight);

  String get dateLabel {
    final date = startTime ?? endTime;
    if (date == null) return 'Date unavailable';
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    return '${date.day} ${months[date.month - 1]} ${date.year}';
  }

  String get timeLabel {
    if (startTime == null && endTime == null) return 'Time unavailable';
    if (startTime == null) return 'Finished ${_clock(endTime!)}';
    if (endTime == null) return 'Started ${_clock(startTime!)}';
    return '${_clock(startTime!)} – ${_clock(endTime!)}';
  }

  String? get durationLabel {
    if (startTime == null || endTime == null || endTime!.isBefore(startTime!)) {
      return null;
    }
    final duration = endTime!.difference(startTime!);
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    if (hours == 0) return '${minutes}m';
    return '${hours}h ${minutes}m';
  }

  String? get printerLabel {
    final values =
        [printerName, printerModel].whereType<String>().toSet().toList();
    return values.isEmpty ? null : values.join(' · ');
  }
}

List<SavedTask> savedTasksNewestFirst(List<Map<String, dynamic>> tasks) {
  final indexedTasks = tasks
      .asMap()
      .entries
      .map((entry) => (index: entry.key, task: SavedTask.fromJson(entry.value)))
      .toList();

  indexedTasks.sort((left, right) {
    final leftTime = left.task.sortTime;
    final rightTime = right.task.sortTime;
    if (leftTime == null && rightTime == null) {
      return right.index.compareTo(left.index);
    }
    if (leftTime == null) return 1;
    if (rightTime == null) return -1;
    final dateComparison = rightTime.compareTo(leftTime);
    return dateComparison != 0
        ? dateComparison
        : right.index.compareTo(left.index);
  });

  return indexedTasks.map((entry) => entry.task).toList(growable: false);
}

DateTime? parseTaskDate(dynamic value) {
  final text = _text(value);
  if (text == null) return null;

  final match = RegExp(
    r'^(\d{2}):(\d{2}):(\d{2})-(\d{2})-(\d{2})-(\d{4})$',
  ).firstMatch(text);
  if (match != null) {
    return DateTime(
      int.parse(match.group(6)!),
      int.parse(match.group(5)!),
      int.parse(match.group(4)!),
      int.parse(match.group(1)!),
      int.parse(match.group(2)!),
      int.parse(match.group(3)!),
    );
  }
  return DateTime.tryParse(text);
}

String formatGrams(double value) {
  final decimals = value >= 100
      ? 0
      : value >= 10
          ? 1
          : 2;
  return value
      .toStringAsFixed(decimals)
      .replaceFirst(RegExp(r'\.0+$'), '')
      .replaceFirst(RegExp(r'(\.\d*[1-9])0+$'), r'$1');
}

String _clock(DateTime value) {
  return '${value.hour.toString().padLeft(2, '0')}:'
      '${value.minute.toString().padLeft(2, '0')}';
}

String? _text(dynamic value) {
  if (value == null) return null;
  final text = value.toString().trim();
  return text.isEmpty ? null : text;
}

double _number(dynamic value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

List<Map<String, dynamic>> _mapList(dynamic value) {
  if (value is! List) return const [];
  return value
      .whereType<Map>()
      .map((item) => Map<String, dynamic>.from(item))
      .toList(growable: false);
}
