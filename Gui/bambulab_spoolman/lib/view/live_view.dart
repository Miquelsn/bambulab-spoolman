import 'package:bambulab_spoolman/data/data_model.dart';
import 'package:bambulab_spoolman/model/printer_status.dart';
import 'package:bambulab_spoolman/view/terminal_log_view.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class LiveView extends StatelessWidget {
  const LiveView({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<DataModel>(
      builder: (context, dataModel, child) {
        final theme = Theme.of(context);
        return ColoredBox(
          color: theme.colorScheme.surfaceContainerLowest,
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1080),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('Live status', style: theme.textTheme.headlineMedium),
                    const SizedBox(height: 6),
                    Text(
                      'Backend connectivity and recent service activity.',
                      style: theme.textTheme.bodyLarge?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 20),
                    Card(
                      child: ListTile(
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 10,
                        ),
                        leading: Icon(
                          dataModel.backendStatus
                              ? Icons.cloud_done_outlined
                              : Icons.cloud_off_outlined,
                          color: dataModel.backendStatus
                              ? theme.colorScheme.primary
                              : theme.colorScheme.error,
                        ),
                        title: Text(
                          dataModel.backendStatus
                              ? 'Backend online'
                              : 'Backend offline',
                        ),
                        subtitle: dataModel.connectionMessage == null
                            ? const Text('Live updates are connected.')
                            : Text(dataModel.connectionMessage!),
                        trailing: dataModel.backendStatus
                            ? null
                            : IconButton.filledTonal(
                                tooltip: 'Retry backend connection',
                                onPressed: dataModel.reconnect,
                                icon: const Icon(Icons.refresh),
                              ),
                      ),
                    ),
                    const SizedBox(height: 28),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            'Printers',
                            style: theme.textTheme.titleLarge,
                          ),
                        ),
                        Text(
                          '${dataModel.printers.where((printer) => printer.connected).length}'
                          ' of ${dataModel.printers.length} connected',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    _PrinterGrid(printers: dataModel.printers),
                    const SizedBox(height: 28),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            'Recent activity',
                            style: theme.textTheme.titleLarge,
                          ),
                        ),
                        IconButton(
                          tooltip: 'Refresh activity log',
                          onPressed: dataModel.backendStatus
                              ? dataModel.refreshLogs
                              : null,
                          icon: const Icon(Icons.refresh),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    const LogTerminalView(),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _PrinterGrid extends StatelessWidget {
  const _PrinterGrid({required this.printers});

  final List<PrinterStatus> printers;

  @override
  Widget build(BuildContext context) {
    if (printers.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Icon(
                Icons.print_disabled_outlined,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Text('No configured printers were reported.'),
              ),
            ],
          ),
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 760 ? 2 : 1;
        final width = (constraints.maxWidth - (columns - 1) * 12) / columns;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final printer in printers)
              SizedBox(width: width, child: _PrinterCard(printer: printer)),
          ],
        );
      },
    );
  }
}

class _PrinterCard extends StatelessWidget {
  const _PrinterCard({required this.printer});

  final PrinterStatus printer;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final active = printer.connected && printer.enabled;
    final color = active ? theme.colorScheme.primary : theme.colorScheme.outline;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(Icons.precision_manufacturing_outlined, color: color),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        printer.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        [printer.model, printer.displayState]
                            .whereType<String>()
                            .join(' · '),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (printer.isPrinting) ...[
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      printer.taskName ?? 'Current print',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text('${printer.progress}%'),
                ],
              ),
              const SizedBox(height: 8),
              LinearProgressIndicator(
                value: printer.progress / 100,
                borderRadius: BorderRadius.circular(99),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
