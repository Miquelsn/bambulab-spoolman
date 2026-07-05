import 'package:bambulab_spoolman/data/filament_model.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class FilamentsMapView extends StatefulWidget {
  const FilamentsMapView({super.key});

  @override
  State<FilamentsMapView> createState() => _FilamentsMapViewState();
}

class _FilamentsMapViewState extends State<FilamentsMapView>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) context.read<FilamentMappingModel>().requestFilaments();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<FilamentMappingModel>(
      builder: (context, model, child) {
        final unmapped = model.bambuFilaments
            .where((filament) => !model.mapping.containsKey(filament.id))
            .toList(growable: false);
        final mapped = model.bambuFilaments
            .where((filament) => model.mapping.containsKey(filament.id))
            .toList(growable: false);

        return Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1100),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _Header(
                    refreshing: model.isLoading,
                    onRefresh: model.refreshFilaments,
                  ),
                  if (model.message != null) ...[
                    const SizedBox(height: 12),
                    _Notice(
                      message: model.message!,
                      isError: model.messageIsError,
                      onDismiss: model.clearMessage,
                    ),
                  ],
                  const SizedBox(height: 18),
                  Card(
                    child: TabBar(
                      controller: _tabController,
                      tabs: [
                        Tab(
                          icon: const Icon(Icons.link_off_outlined),
                          text: 'Action needed (${unmapped.length})',
                        ),
                        Tab(
                          icon: const Icon(Icons.link),
                          text: 'Mapped (${mapped.length})',
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  Expanded(
                    child: model.isLoading && model.bambuFilaments.isEmpty
                        ? const Center(child: CircularProgressIndicator())
                        : model.bambuFilaments.isEmpty
                            ? const _EmptyCatalog()
                            : TabBarView(
                                controller: _tabController,
                                children: [
                                  _FilamentList(
                                    filaments: unmapped,
                                    model: model,
                                    mapped: false,
                                  ),
                                  _FilamentList(
                                    filaments: mapped,
                                    model: model,
                                    mapped: true,
                                  ),
                                ],
                              ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.refreshing, required this.onRefresh});

  final bool refreshing;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final title = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Filament mapping',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 6),
            Text(
              'Link each slicer filament profile to the physical Spoolman spool that should record usage.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ],
        );
        final refresh = OutlinedButton.icon(
          onPressed: refreshing ? null : onRefresh,
          icon: refreshing
              ? const SizedBox.square(
                  dimension: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.refresh),
          label: Text(refreshing ? 'Refreshing…' : 'Refresh'),
        );
        if (constraints.maxWidth < 650) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [title, const SizedBox(height: 12), refresh],
          );
        }
        return Row(
          children: [
            Expanded(child: title),
            const SizedBox(width: 20),
            refresh,
          ],
        );
      },
    );
  }
}

class _FilamentList extends StatelessWidget {
  const _FilamentList({
    required this.filaments,
    required this.model,
    required this.mapped,
  });

  final List<BambuFilament> filaments;
  final FilamentMappingModel model;
  final bool mapped;

  @override
  Widget build(BuildContext context) {
    if (filaments.isEmpty) {
      return _EmptyTab(mapped: mapped);
    }
    return ListView.separated(
      padding: const EdgeInsets.only(bottom: 32),
      itemCount: filaments.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, index) => _FilamentCard(
        filament: filaments[index],
        model: model,
        mapped: mapped,
      ),
    );
  }
}

class _FilamentCard extends StatelessWidget {
  const _FilamentCard({
    required this.filament,
    required this.model,
    required this.mapped,
  });

  final BambuFilament filament;
  final FilamentMappingModel model;
  final bool mapped;

  @override
  Widget build(BuildContext context) {
    final mappedId = model.mapping[filament.id];
    SpoolmanFilament? mappedSpool;
    for (final spool in model.spoolmanFilaments) {
      if (spool.id == mappedId) mappedSpool = spool;
    }
    final suggestions = model.possibleMatches[filament.id] ?? const [];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Wrap(
              spacing: 10,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                const Chip(
                  avatar: Icon(Icons.tune, size: 16),
                  label: Text('Slicer profile'),
                  visualDensity: VisualDensity.compact,
                ),
                Text(
                  filament.name,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                if (filament.type.isNotEmpty)
                  Chip(
                    label: Text(filament.type),
                    visualDensity: VisualDensity.compact,
                  ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              [filament.vendor, filament.id]
                  .where((value) => value.isNotEmpty)
                  .join(' · '),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            const Divider(height: 28),
            if (mapped)
              _MappedAction(
                filament: filament,
                spool: mappedSpool,
                mappedId: mappedId,
                model: model,
              )
            else
              _UnmappedAction(
                filament: filament,
                suggestionCount: suggestions.length,
                model: model,
              ),
          ],
        ),
      ),
    );
  }
}

class _UnmappedAction extends StatelessWidget {
  const _UnmappedAction({
    required this.filament,
    required this.suggestionCount,
    required this.model,
  });

  final BambuFilament filament;
  final int suggestionCount;
  final FilamentMappingModel model;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 16,
      runSpacing: 12,
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Text(
          suggestionCount > 0
              ? '$suggestionCount suggested match${suggestionCount == 1 ? '' : 'es'}'
              : 'No automatic suggestion',
          style: TextStyle(
            color: suggestionCount > 0
                ? Theme.of(context).colorScheme.primary
                : Theme.of(context).colorScheme.onSurfaceVariant,
            fontWeight: FontWeight.w600,
          ),
        ),
        FilledButton.icon(
          onPressed: model.isSaving
              ? null
              : () => _showSelectionSheet(context, model, filament),
          icon: const Icon(Icons.link),
          label: const Text('Select spool'),
        ),
      ],
    );
  }
}

class _MappedAction extends StatelessWidget {
  const _MappedAction({
    required this.filament,
    required this.spool,
    required this.mappedId,
    required this.model,
  });

  final BambuFilament filament;
  final SpoolmanFilament? spool;
  final String? mappedId;
  final FilamentMappingModel model;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 16,
      runSpacing: 12,
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              spool == null ? Icons.warning_amber : Icons.inventory_2_outlined,
              color: spool == null
                  ? Theme.of(context).colorScheme.error
                  : Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  spool?.name ?? 'Missing Spoolman spool #$mappedId',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                if (spool != null)
                  Text(
                    [spool!.vendor, spool!.type]
                        .where((value) => value.isNotEmpty)
                        .join(' · '),
                  ),
              ],
            ),
          ],
        ),
        Wrap(
          spacing: 8,
          children: [
            OutlinedButton.icon(
              onPressed: model.isSaving
                  ? null
                  : () => _showSelectionSheet(context, model, filament),
              icon: const Icon(Icons.edit_outlined),
              label: const Text('Change'),
            ),
            TextButton.icon(
              onPressed: model.isSaving
                  ? null
                  : () => model.unmapFilament(filament.id),
              icon: const Icon(Icons.link_off),
              label: const Text('Unlink'),
            ),
          ],
        ),
      ],
    );
  }
}

void _showSelectionSheet(
  BuildContext context,
  FilamentMappingModel model,
  BambuFilament filament,
) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => _FilamentSelectionSheet(
      model: model,
      filament: filament,
    ),
  );
}

class _FilamentSelectionSheet extends StatefulWidget {
  const _FilamentSelectionSheet({required this.model, required this.filament});

  final FilamentMappingModel model;
  final BambuFilament filament;

  @override
  State<_FilamentSelectionSheet> createState() =>
      _FilamentSelectionSheetState();
}

class _FilamentSelectionSheetState extends State<_FilamentSelectionSheet> {
  String query = '';

  @override
  Widget build(BuildContext context) {
    final queryText = query.trim().toLowerCase();
    final suggestedIds =
        widget.model.possibleMatches[widget.filament.id] ?? const [];
    final filtered = widget.model.spoolmanFilaments.where((spool) {
      if (queryText.isEmpty) return true;
      return spool.name.toLowerCase().contains(queryText) ||
          spool.vendor.toLowerCase().contains(queryText) ||
          spool.type.toLowerCase().contains(queryText) ||
          spool.id.toLowerCase().contains(queryText);
    }).toList(growable: false);
    filtered.sort((a, b) {
      final aSuggested = suggestedIds.contains(a.id);
      final bSuggested = suggestedIds.contains(b.id);
      if (aSuggested != bSuggested) return aSuggested ? -1 : 1;
      return a.name.toLowerCase().compareTo(b.name.toLowerCase());
    });

    return FractionallySizedBox(
      heightFactor: 0.9,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Map ${widget.filament.name}',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close),
                  tooltip: 'Close',
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              autofocus: true,
              decoration: const InputDecoration(
                labelText: 'Search Spoolman spools',
                prefixIcon: Icon(Icons.search),
              ),
              onChanged: (value) => setState(() => query = value),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: filtered.isEmpty
                  ? const Center(child: Text('No matching Spoolman spools.'))
                  : ListView.separated(
                      itemCount: filtered.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final spool = filtered[index];
                        final current =
                            widget.model.mapping[widget.filament.id] ==
                                spool.id;
                        final usedElsewhere = !current &&
                            widget.model.mapping.entries.any(
                              (entry) =>
                                  entry.key != widget.filament.id &&
                                  entry.value == spool.id,
                            );
                        final suggested = suggestedIds.contains(spool.id);
                        return ListTile(
                          enabled: !usedElsewhere,
                          leading: CircleAvatar(
                            child: Text(
                              spool.vendor.isEmpty
                                  ? '?'
                                  : spool.vendor[0].toUpperCase(),
                            ),
                          ),
                          title: Text(spool.name),
                          subtitle: Text(
                            [spool.vendor, spool.type, '#${spool.id}']
                                .where((value) => value.isNotEmpty)
                                .join(' · '),
                          ),
                          trailing: usedElsewhere
                              ? const Chip(label: Text('Already used'))
                              : current
                                  ? const Icon(Icons.check_circle)
                                  : suggested
                                      ? const Chip(label: Text('Suggested'))
                                      : null,
                          onTap: usedElsewhere
                              ? null
                              : () {
                                  widget.model.mapFilament(
                                    widget.filament.id,
                                    spool.id,
                                  );
                                  Navigator.pop(context);
                                },
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({
    required this.message,
    required this.isError,
    required this.onDismiss,
  });

  final String message;
  final bool isError;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final color = isError ? colors.error : colors.primary;
    return Material(
      color: color.withValues(alpha: 0.09),
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        child: Row(
          children: [
            Icon(isError ? Icons.error_outline : Icons.check_circle_outline,
                color: color),
            const SizedBox(width: 10),
            Expanded(child: Text(message)),
            IconButton(
              onPressed: onDismiss,
              icon: const Icon(Icons.close),
              tooltip: 'Dismiss',
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyCatalog extends StatelessWidget {
  const _EmptyCatalog();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.inventory_2_outlined, size: 48),
            SizedBox(height: 14),
            Text(
              'No slicer filaments are available yet.',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 8),
            Text(
              'Check Bambu Cloud and Spoolman in Settings, then use Refresh to load both catalogs.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyTab extends StatelessWidget {
  const _EmptyTab({required this.mapped});

  final bool mapped;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(mapped ? Icons.inbox_outlined : Icons.check_circle_outline,
              size: 48),
          const SizedBox(height: 12),
          Text(
            mapped
                ? 'No filaments are mapped yet.'
                : 'All filaments are mapped.',
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ],
      ),
    );
  }
}
