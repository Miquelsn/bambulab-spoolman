import 'dart:async';

import 'package:bambulab_spoolman/data/data_model.dart';
import 'package:bambulab_spoolman/model/log_event.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class LogTerminalView extends StatefulWidget {
  const LogTerminalView({super.key});

  @override
  State<LogTerminalView> createState() => _LogTerminalViewState();
}

class _LogTerminalViewState extends State<LogTerminalView> {
  Timer? _logTimer;
  final _searchController = TextEditingController();
  String _filter = 'all';

  @override
  void initState() {
    super.initState();
    _logTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (mounted) context.read<DataModel>().refreshLogs();
    });
  }

  @override
  void dispose() {
    _logTimer?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DataModel>(
      builder: (context, dataModel, child) {
        final query = _searchController.text.trim().toLowerCase();
        final logs = dataModel.logs.reversed.where((event) {
          final matchesFilter = _filter == 'all' ||
              (_filter == 'problem' && event.isProblem) ||
              (_filter == 'info' && !event.isProblem);
          final matchesSearch = query.isEmpty ||
              event.message.toLowerCase().contains(query) ||
              event.subsystem.toLowerCase().contains(query) ||
              (event.printerId?.toLowerCase().contains(query) ?? false);
          return matchesFilter && matchesSearch;
        }).toList(growable: false);

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                for (final option in const [
                  ('all', 'All activity'),
                  ('problem', 'Needs attention'),
                  ('info', 'Information'),
                ])
                  ChoiceChip(
                    label: Text(option.$2),
                    selected: _filter == option.$1,
                    onSelected: (_) => setState(() => _filter = option.$1),
                  ),
                SizedBox(
                  width: 260,
                  child: TextField(
                    controller: _searchController,
                    onChanged: (_) => setState(() {}),
                    decoration: const InputDecoration(
                      isDense: true,
                      prefixIcon: Icon(Icons.search),
                      hintText: 'Search activity',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Semantics(
              label: 'Structured application activity, newest entries first',
              child: Container(
                height: 410,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                ),
                child: logs.isEmpty
                    ? const _EmptyActivity()
                    : ListView.separated(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        itemCount: logs.length,
                        separatorBuilder: (_, __) => const Divider(height: 1),
                        itemBuilder: (context, index) =>
                            _ActivityRow(event: logs[index]),
                      ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _ActivityRow extends StatelessWidget {
  const _ActivityRow({required this.event});

  final LogEvent event;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isError = event.level == 'error';
    final isWarning = event.level == 'warning';
    final color = isError
        ? theme.colorScheme.error
        : isWarning
            ? Colors.orange.shade800
            : theme.colorScheme.primary;
    final icon = isError
        ? Icons.error_outline
        : isWarning
            ? Icons.warning_amber_rounded
            : Icons.check_circle_outline;
    final contextParts = [
      event.subsystem,
      if (event.printerId != null) 'Printer ${event.printerId}',
      if (event.taskId != null) 'Task ${event.taskId}',
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, size: 20, color: color),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(event.message, style: theme.textTheme.bodyMedium),
                const SizedBox(height: 4),
                Text(
                  contextParts.join(' · '),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            event.timeLabel,
            style: theme.textTheme.labelMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyActivity extends StatelessWidget {
  const _EmptyActivity();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.inbox_outlined,
            size: 40,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 10),
          Text('No matching activity', style: theme.textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            'New service events will appear here.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}
