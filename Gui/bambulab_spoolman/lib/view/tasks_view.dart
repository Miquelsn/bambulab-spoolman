import 'package:bambulab_spoolman/data/data_model.dart';
import 'package:bambulab_spoolman/model/saved_task.dart';
import 'package:bambulab_spoolman/model/spool_option.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class TasksView extends StatefulWidget {
  const TasksView({super.key});

  @override
  State<TasksView> createState() => _TasksViewState();
}

class _TasksViewState extends State<TasksView> {
  @override
  void initState() {
    super.initState();
    Provider.of<DataModel>(context, listen: false).refreshTasks();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DataModel>(
      builder: (context, dataModel, child) {
        final tasks = savedTasksNewestFirst(dataModel.tasks);
        final mutationMessage = dataModel.taskMutationMessage;
        if (mutationMessage != null) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!mounted) return;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(mutationMessage),
                backgroundColor: dataModel.taskMutationFailed
                    ? Theme.of(context).colorScheme.error
                    : null,
              ),
            );
            dataModel.clearTaskMutationMessage();
          });
        }
        return ColoredBox(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _HistoryHeader(
                taskCount: tasks.length,
                isLoading: !dataModel.tasksLoaded,
                onRefresh: dataModel.refreshTasks,
              ),
              if (dataModel.tasksError != null)
                _HistoryNotice(
                  message: dataModel.tasksError!,
                  onRetry: dataModel.refreshTasks,
                ),
              Expanded(
                child: !dataModel.tasksLoaded
                    ? const Center(
                        child: CircularProgressIndicator(
                          semanticsLabel: 'Loading print history',
                        ),
                      )
                    : tasks.isEmpty
                        ? _EmptyHistory(hasError: dataModel.tasksError != null)
                        : ListView.separated(
                            padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
                            itemCount: tasks.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 16),
                            itemBuilder: (context, index) => Center(
                              child: ConstrainedBox(
                                constraints:
                                    const BoxConstraints(maxWidth: 1080),
                                child: SavedTaskCard(
                                  task: tasks[index],
                                  canEdit: dataModel.backendStatus &&
                                      dataModel.spools.isNotEmpty,
                                  isUpdating: (filamentIndex) =>
                                      dataModel.isUpdatingFilament(
                                    tasks[index].historyId,
                                    filamentIndex,
                                  ),
                                  onChangeSpool: (filamentIndex) =>
                                      _changeSpool(
                                    context,
                                    dataModel,
                                    tasks[index],
                                    filamentIndex,
                                  ),
                                ),
                              ),
                            ),
                          ),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _changeSpool(
    BuildContext context,
    DataModel dataModel,
    SavedTask task,
    int filamentIndex,
  ) async {
    if (dataModel.spools.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No Spoolman spools are available.')),
      );
      return;
    }
    final filament = task.filaments[filamentIndex];
    final spoolId = await showDialog<String>(
      context: context,
      builder: (context) => _SpoolPickerDialog(
        filament: filament,
        spools: dataModel.spools,
      ),
    );
    if (spoolId == null || !mounted) return;
    dataModel.updateTaskFilament(
      historyId: task.historyId,
      filamentIndex: filamentIndex,
      spoolId: spoolId,
    );
  }
}

class _HistoryNotice extends StatelessWidget {
  const _HistoryNotice({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1080),
        child: Container(
          margin: const EdgeInsets.fromLTRB(24, 0, 24, 16),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: colors.errorContainer,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Icon(Icons.cloud_off_outlined, color: colors.onErrorContainer),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  message,
                  style: TextStyle(color: colors.onErrorContainer),
                ),
              ),
              TextButton(
                style: TextButton.styleFrom(
                  foregroundColor: colors.onErrorContainer,
                ),
                onPressed: onRetry,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HistoryHeader extends StatelessWidget {
  const _HistoryHeader({
    required this.taskCount,
    required this.isLoading,
    required this.onRefresh,
  });

  final int taskCount;
  final bool isLoading;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1128),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 28, 24, 20),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Print history',
                        style: theme.textTheme.headlineMedium),
                    const SizedBox(height: 4),
                    Text(
                      taskCount == 1
                          ? '1 saved task'
                          : '$taskCount saved tasks',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              IconButton.filledTonal(
                tooltip: 'Refresh print history',
                onPressed: isLoading ? null : onRefresh,
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class SavedTaskCard extends StatelessWidget {
  const SavedTaskCard({
    super.key,
    required this.task,
    required this.canEdit,
    required this.isUpdating,
    required this.onChangeSpool,
  });

  final SavedTask task;
  final bool canEdit;
  final bool Function(int index) isUpdating;
  final ValueChanged<int> onChangeSpool;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      clipBehavior: Clip.antiAlias,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final details = _TaskDetails(
            task: task,
            canEdit: canEdit,
            isUpdating: isUpdating,
            onChangeSpool: onChangeSpool,
          );
          if (constraints.maxWidth < 720) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SizedBox(height: 190, child: _TaskCover(task: task)),
                details,
              ],
            );
          }
          return IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SizedBox(width: 240, child: _TaskCover(task: task)),
                Expanded(child: details),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _TaskCover extends StatelessWidget {
  const _TaskCover({required this.task});

  final SavedTask task;

  @override
  Widget build(BuildContext context) {
    final imageUrl = task.imageUrl;
    if (imageUrl == null) return const _ImageFallback();
    return Image.network(
      imageUrl,
      fit: BoxFit.cover,
      semanticLabel: 'Preview of ${task.modelName}',
      errorBuilder: (_, __, ___) => const _ImageFallback(),
      loadingBuilder: (context, child, progress) {
        if (progress == null) return child;
        return const _ImageFallback(showProgress: true);
      },
    );
  }
}

class _ImageFallback extends StatelessWidget {
  const _ImageFallback({this.showProgress = false});

  final bool showProgress;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return ColoredBox(
      color: colors.surfaceContainerHigh,
      child: Center(
        child: showProgress
            ? const SizedBox.square(
                dimension: 28,
                child: CircularProgressIndicator(strokeWidth: 2.5),
              )
            : Icon(
                Icons.view_in_ar_outlined,
                size: 52,
                color: colors.onSurfaceVariant,
              ),
      ),
    );
  }
}

class _TaskDetails extends StatelessWidget {
  const _TaskDetails({
    required this.task,
    required this.canEdit,
    required this.isUpdating,
    required this.onChangeSpool,
  });

  final SavedTask task;
  final bool canEdit;
  final bool Function(int index) isUpdating;
  final ValueChanged<int> onChangeSpool;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final duration = task.durationLabel;
    final printer = task.printerLabel;
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  task.modelName,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              _StatusBadge(status: task.status, progress: task.progress),
            ],
          ),
          if (printer != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(
                  Icons.precision_manufacturing_outlined,
                  size: 17,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Printed on $printer',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 16),
          Wrap(
            spacing: 20,
            runSpacing: 10,
            children: [
              _Metadata(
                  icon: Icons.calendar_today_outlined, text: task.dateLabel),
              _Metadata(icon: Icons.schedule, text: task.timeLabel),
              if (duration != null)
                _Metadata(icon: Icons.timelapse, text: duration),
              _Metadata(
                icon: Icons.scale_outlined,
                text: '${formatGrams(task.totalWeight)} g total',
              ),
            ],
          ),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 18),
            child: Divider(height: 1),
          ),
          _MaterialUsage(
            task: task,
            canEdit: canEdit,
            isUpdating: isUpdating,
            onChangeSpool: onChangeSpool,
          ),
        ],
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status, required this.progress});

  final String status;
  final int progress;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final failed = status.toLowerCase() == 'failed';
    final foreground =
        failed ? theme.colorScheme.error : theme.colorScheme.primary;
    final background = failed
        ? theme.colorScheme.errorContainer
        : theme.colorScheme.primaryContainer;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        '$status · $progress%',
        style: theme.textTheme.labelMedium?.copyWith(
          color: foreground,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _Metadata extends StatelessWidget {
  const _Metadata({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 17, color: theme.colorScheme.onSurfaceVariant),
        const SizedBox(width: 6),
        Text(
          text,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}

class _MaterialUsage extends StatelessWidget {
  const _MaterialUsage({
    required this.task,
    required this.canEdit,
    required this.isUpdating,
    required this.onChangeSpool,
  });

  final SavedTask task;
  final bool canEdit;
  final bool Function(int index) isUpdating;
  final ValueChanged<int> onChangeSpool;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (task.filaments.isEmpty) {
      return Row(
        children: [
          Icon(
            Icons.inventory_2_outlined,
            size: 20,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 8),
          Text(
            'No material breakdown recorded',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      );
    }

    final total = task.usedWeight;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                task.usageIsEstimated ? 'Estimated material' : 'Material used',
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            Text(
              '${formatGrams(total)} g',
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        for (var index = 0; index < task.filaments.length; index++) ...[
          _FilamentRow(
            filament: task.filaments[index],
            totalWeight: total,
            canEdit: canEdit && task.historyId.isNotEmpty,
            isUpdating: isUpdating(index),
            onChangeSpool: () => onChangeSpool(index),
          ),
          if (index < task.filaments.length - 1) const SizedBox(height: 12),
        ],
      ],
    );
  }
}

class _FilamentRow extends StatelessWidget {
  const _FilamentRow({
    required this.filament,
    required this.totalWeight,
    required this.canEdit,
    required this.isUpdating,
    required this.onChangeSpool,
  });

  final FilamentUsage filament;
  final double totalWeight;
  final bool canEdit;
  final bool isUpdating;
  final VoidCallback onChangeSpool;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final proportion = totalWeight <= 0
        ? 0.0
        : (filament.weight / totalWeight).clamp(0.0, 1.0);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Icon(
            Icons.fiber_manual_record,
            size: 16,
            color: theme.colorScheme.primary,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      filament.displayName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    '${formatGrams(filament.weight)} g',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              if (filament.details != null) ...[
                const SizedBox(height: 2),
                Text(
                  filament.details!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
              const SizedBox(height: 6),
              LinearProgressIndicator(
                value: proportion,
                minHeight: 5,
                semanticsLabel: '${filament.displayName} proportion',
                semanticsValue: (proportion * 100).round().toString(),
                borderRadius: BorderRadius.circular(999),
                backgroundColor: theme.colorScheme.surfaceContainerHighest,
              ),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
                decoration: BoxDecoration(
                  color: filament.isReported
                      ? theme.colorScheme.primaryContainer.withValues(alpha: 0.45)
                      : theme.colorScheme.surfaceContainer,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    Icon(
                      filament.isReported
                          ? Icons.inventory_2_outlined
                          : Icons.report_problem_outlined,
                      size: 20,
                      color: filament.isReported
                          ? theme.colorScheme.primary
                          : theme.colorScheme.error,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            filament.spoolLabel,
                            style: theme.textTheme.bodyMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          if (filament.reportError != null)
                            Text(
                              filament.reportError!,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.error,
                              ),
                            )
                          else if (filament.spoolDetails != null)
                            Text(
                              filament.spoolDetails!,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (isUpdating)
                      const Padding(
                        padding: EdgeInsets.all(10),
                        child: SizedBox.square(
                          dimension: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      )
                    else
                      TextButton.icon(
                        onPressed: canEdit ? onChangeSpool : null,
                        icon: const Icon(Icons.swap_horiz, size: 19),
                        label: Text(
                          filament.spoolId == null ? 'Report' : 'Change',
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SpoolPickerDialog extends StatefulWidget {
  const _SpoolPickerDialog({
    required this.filament,
    required this.spools,
  });

  final FilamentUsage filament;
  final List<SpoolOption> spools;

  @override
  State<_SpoolPickerDialog> createState() => _SpoolPickerDialogState();
}

class _SpoolPickerDialogState extends State<_SpoolPickerDialog> {
  String? selectedId;

  @override
  void initState() {
    super.initState();
    selectedId = widget.spools.any(
      (spool) => spool.id == widget.filament.spoolId,
    )
        ? widget.filament.spoolId
        : null;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return AlertDialog(
      icon: const Icon(Icons.swap_horiz),
      title: Text(
        widget.filament.spoolId == null
            ? 'Report filament usage'
            : 'Change reported spool',
      ),
      content: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '${formatGrams(widget.filament.weight)} g of '
              '${widget.filament.displayName}',
              style: theme.textTheme.titleSmall,
            ),
            const SizedBox(height: 6),
            Text(
              widget.filament.spoolId == null
                  ? 'This will register the usage on the selected Spoolman spool.'
                  : 'This will refund the current spool and apply the same usage '
                      'to the selected spool.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 20),
            LayoutBuilder(
              builder: (context, constraints) => DropdownMenu<String>(
                width: constraints.maxWidth,
                initialSelection: selectedId,
                requestFocusOnTap: true,
                enableFilter: true,
                label: const Text('Spoolman spool'),
                hintText: 'Search by spool, material, or vendor',
                onSelected: (value) => setState(() => selectedId = value),
                dropdownMenuEntries: [
                  for (final spool in widget.spools)
                    DropdownMenuEntry(
                      value: spool.id,
                      label: '${spool.label} · ${spool.details}',
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: selectedId == null ||
                  selectedId == widget.filament.spoolId
              ? null
              : () => Navigator.pop(context, selectedId),
          child: Text(
            widget.filament.spoolId == null ? 'Report usage' : 'Move usage',
          ),
        ),
      ],
    );
  }
}

class _EmptyHistory extends StatelessWidget {
  const _EmptyHistory({required this.hasError});

  final bool hasError;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              hasError ? Icons.cloud_off_outlined : Icons.history_toggle_off,
              size: 56,
              color: theme.colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              hasError ? 'Print history unavailable' : 'No saved tasks yet',
              style: theme.textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(
              hasError
                  ? 'Reconnect to the backend and try again.'
                  : 'Completed and failed prints will appear here.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
