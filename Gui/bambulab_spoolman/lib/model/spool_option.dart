class SpoolOption {
  const SpoolOption({
    required this.id,
    required this.name,
    required this.type,
    required this.vendor,
  });

  factory SpoolOption.fromJson(Map<String, dynamic> json) {
    return SpoolOption(
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

  String get label => '#$id · $name';
  String get details => [vendor, type].where((value) => value.isNotEmpty).join(' · ');
}
