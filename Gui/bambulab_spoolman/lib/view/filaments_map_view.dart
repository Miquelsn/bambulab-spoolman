import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:bambulab_spoolman/data/filament_model.dart'; 

class FilamentsMapView extends StatefulWidget {
  const FilamentsMapView({super.key});

  @override
  State<FilamentsMapView> createState() => _FilamentsMapViewState();
}

class _FilamentsMapViewState extends State<FilamentsMapView> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fetchFilaments();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _fetchFilaments() {
    context.read<FilamentMappingModel>().requestFilaments();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Filament Mapper"),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: "Action Needed", icon: Icon(Icons.link_off)),
            Tab(text: "Mapped", icon: Icon(Icons.link)),
          ],
        ),
      ),
      body: Consumer<FilamentMappingModel>(
        builder: (context, model, child) {
          if (model.isLoading && model.bambuFilaments.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }

          // 1. Separate the data
          final unmappedBambu = model.bambuFilaments
              .where((b) => !model.mapping.containsKey(b.id))
              .toList();
          
          final mappedBambu = model.bambuFilaments
              .where((b) => model.mapping.containsKey(b.id))
              .toList();

          return TabBarView(
            controller: _tabController,
            children: [
              // Tab 1: Unmapped (To Do List)
              _buildFilamentList(context, model, unmappedBambu, isMapped: false),
              
              // Tab 2: Mapped (Review List)
              _buildFilamentList(context, model, mappedBambu, isMapped: true),
            ],
          );
        },
      ),
    );
  }

  Widget _buildFilamentList(
    BuildContext context, 
    FilamentMappingModel model, 
    List<BambuFilament> list, 
    {required bool isMapped}
  ) {
    if (list.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(isMapped ? Icons.inbox : Icons.check_circle_outline, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text(isMapped ? "No filaments mapped yet." : "All filaments are mapped!", 
              style: Theme.of(context).textTheme.titleMedium),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: list.length,
      itemBuilder: (context, index) {
        final bambu = list[index];
        final mappedSpoolId = model.mapping[bambu.id];
        
        // Find the mapped spool object if it exists
        SpoolmanFilament? mappedSpool;
        if (mappedSpoolId != null) {
          mappedSpool = model.spoolmanFilaments.firstWhere(
            (s) => s.id == mappedSpoolId, 
            orElse: () => SpoolmanFilament(id: '', name: 'Unknown', type: '', vendor: '')
          );
        }

        return Card(
          elevation: 2,
          margin: const EdgeInsets.only(bottom: 12),
          child: Padding(
            padding: const EdgeInsets.all(12.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Bambu Header
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.green.shade100,
                        borderRadius: BorderRadius.circular(4)
                      ),
                      child: const Text("Slicer", style: TextStyle(fontSize: 10, color: Colors.green)),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        bambu.name,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                    ),
                    Chip(label: Text(bambu.type, style: const TextStyle(fontSize: 12))),
                  ],
                ),
                Text("Vendor: ${bambu.vendor}", style: Theme.of(context).textTheme.bodySmall),
                
                const Divider(),

                // Action Area
                if (!isMapped) ...[
                   _buildUnmappedAction(context, model, bambu),
                ] else ...[
                   _buildMappedAction(context, model, bambu, mappedSpool!),
                ]
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildUnmappedAction(BuildContext context, FilamentMappingModel model, BambuFilament bambu) {
    // Check if we have suggested matches
    final suggestions = model.possibleMatches[bambu.id] ?? [];
    final hasSuggestions = suggestions.isNotEmpty;

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        if (hasSuggestions) 
          Row(
            children: [
              const Icon(Icons.lightbulb, color: Colors.amber, size: 18),
              const SizedBox(width: 4),
              Text("${suggestions.length} suggestions", style: const TextStyle(color: Colors.amber, fontWeight: FontWeight.bold)),
            ],
          )
        else
          const Text("Not mapped", style: TextStyle(color: Colors.grey, fontStyle: FontStyle.italic)),

        ElevatedButton.icon(
          icon: const Icon(Icons.link),
          label: const Text("Select Match"),
          onPressed: () => _showSelectionSheet(context, model, bambu),
          style: ElevatedButton.styleFrom(
            backgroundColor: Theme.of(context).colorScheme.primaryContainer,
            foregroundColor: Theme.of(context).colorScheme.onPrimaryContainer,
          ),
        )
      ],
    );
  }

  Widget _buildMappedAction(BuildContext context, FilamentMappingModel model, BambuFilament bambu, SpoolmanFilament spool) {
    return Row(
      children: [
        const Icon(Icons.inventory_2_outlined, size: 20, color: Colors.blueGrey),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(spool.name, style: const TextStyle(fontWeight: FontWeight.w600)),
              Text("${spool.vendor} • ${spool.type}", style: const TextStyle(fontSize: 12, color: Colors.grey)),
            ],
          ),
        ),
        IconButton(
          icon: const Icon(Icons.edit_outlined),
          onPressed: () => _showSelectionSheet(context, model, bambu),
          tooltip: "Change mapping",
        ),
        IconButton(
          icon: const Icon(Icons.link_off, color: Color.fromARGB(255, 252, 0, 0)),
          onPressed: () {
            // Ideally add an 'unmap' function to your model, 
            // or map it to null/empty if that's how your logic works
             model.unmapFilament(bambu.id); 
          },
          tooltip: "Unlink",
        ),
      ],
    );
  }

  // The Smart Selection Modal
  void _showSelectionSheet(BuildContext context, FilamentMappingModel model, BambuFilament bambu) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (ctx) => _FilamentSelectionSheet(
        model: model, 
        bambuTarget: bambu
      ),
    );
  }
}

class _FilamentSelectionSheet extends StatefulWidget {
  final FilamentMappingModel model;
  final BambuFilament bambuTarget;

  const _FilamentSelectionSheet({required this.model, required this.bambuTarget});

  @override
  State<_FilamentSelectionSheet> createState() => _FilamentSelectionSheetState();
}

class _FilamentSelectionSheetState extends State<_FilamentSelectionSheet> {
  String _searchQuery = "";

  @override
  Widget build(BuildContext context) {
    // 1. Get IDs of suggested matches
    final suggestedIds = widget.model.possibleMatches[widget.bambuTarget.id] ?? [];

    // 2. Separate Spoolman filaments into Suggested and Others
    // Also filter out filaments that are ALREADY used by other mappings (optional, based on your logic)
    final allSpools = widget.model.spoolmanFilaments;
    
    // Filter logic
    final filteredSpools = allSpools.where((spool) {
      final matchesSearch = spool.name.toLowerCase().contains(_searchQuery.toLowerCase()) || 
                            spool.vendor.toLowerCase().contains(_searchQuery.toLowerCase());
      return matchesSearch;
    }).toList();

    final suggestedSpools = filteredSpools.where((s) => suggestedIds.contains(s.id)).toList();
    final otherSpools = filteredSpools.where((s) => !suggestedIds.contains(s.id)).toList();

    return DraggableScrollableSheet(
      initialChildSize: 0.9,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      expand: false,
      builder: (_, scrollController) {
        return Column(
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Map: ${widget.bambuTarget.name}", style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  TextField(
                    decoration: InputDecoration(
                      hintText: "Search Spoolman...",
                      prefixIcon: const Icon(Icons.search),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      filled: true,
                    ),
                    onChanged: (val) => setState(() => _searchQuery = val),
                  ),
                ],
              ),
            ),
            
            // Lists
            Expanded(
              child: ListView(
                controller: scrollController,
                children: [
                  if (suggestedSpools.isNotEmpty) ...[
                    _buildSectionHeader("Suggested Matches", Icons.star, Colors.amber),
                    ...suggestedSpools.map((s) => _buildOptionTile(s, isSuggested: true)),
                    const Divider(),
                  ],
                  
                  _buildSectionHeader("All Inventory", Icons.list, Colors.blueGrey),
                  ...otherSpools.map((s) => _buildOptionTile(s, isSuggested: false)),
                  
                  if (otherSpools.isEmpty && suggestedSpools.isEmpty)
                     const Padding(
                       padding: EdgeInsets.all(20.0),
                       child: Text("No filaments found matching search."),
                     )
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildSectionHeader(String title, IconData icon, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Text(title, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildOptionTile(SpoolmanFilament spool, {required bool isSuggested}) {
    // Check if this spool is currently mapped to THIS specific Bambu filament
    final isCurrentSelection = widget.model.mapping[widget.bambuTarget.id] == spool.id;
    // Check if mapped to ANOTHER filament (warning)
    final isUsedElsewhere = !isCurrentSelection && widget.model.mapping.containsValue(spool.id);

    return ListTile(
      leading: CircleAvatar(
        backgroundColor: isSuggested ? Colors.amber.shade100 : Colors.grey.shade200,
        child: Text(spool.vendor.isNotEmpty ? spool.vendor[0].toUpperCase() : "?"),
      ),
      title: Text(spool.name),
      subtitle: Text("${spool.vendor} • ${spool.type}"),
      trailing: isUsedElsewhere 
        ? const Chip(label: Text("Used"), backgroundColor: Colors.blue, labelStyle: TextStyle(fontSize: 10, color: Colors.white))
        : (isCurrentSelection ? const Icon(Icons.check_circle, color: Colors.green) : null),
      onTap: () {
        widget.model.mapFilament(widget.bambuTarget.id, spool.id);
        Navigator.pop(context);
      },
    );
  }
}