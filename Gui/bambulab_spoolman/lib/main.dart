import 'package:flutter/material.dart';
import 'package:bambulab_spoolman/data/filament_model.dart';
import 'package:bambulab_spoolman/data/web_socket_service.dart';
import 'package:bambulab_spoolman/view/filaments_map_view.dart';
import 'package:bambulab_spoolman/view/live_view.dart';
import 'package:bambulab_spoolman/view/settings_view.dart';
import 'package:bambulab_spoolman/view/tasks_view.dart';
import 'package:bambulab_spoolman/data/data_model.dart';
import 'package:provider/provider.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => DataModel()),
        ChangeNotifierProvider(
          create: (_) => FilamentMappingModel(
            webSocketService: WebSocketService(),
          ),
        ),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Bambu Lab · Spoolman',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color.fromARGB(255, 46, 162, 185),
          surface: const Color(0xFFF8FAFB),
        ),
        useMaterial3: true,
        cardTheme: const CardThemeData(
          elevation: 0,
          margin: EdgeInsets.zero,
          clipBehavior: Clip.antiAlias,
          color: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(18)),
            side: BorderSide(color: Color(0xFFE1E7EA)),
          ),
        ),
        inputDecorationTheme: const InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.all(Radius.circular(12)),
          ),
        ),
        navigationRailTheme: const NavigationRailThemeData(
          backgroundColor: Colors.white,
          indicatorShape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(12)),
          ),
        ),
      ),
      home: const MyHomePage(title: 'Bambu Lab · Spoolman'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});
  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int selectedIndex = 0;

  static const List<Widget> _pages = <Widget>[
    LiveView(),
    TasksView(),
    FilamentsMapView(),
    SettingsView(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.surface,
        surfaceTintColor: Colors.transparent,
        scrolledUnderElevation: 0,
        titleSpacing: 24,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.autorenew_rounded,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(width: 10),
            Text(
              widget.title,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ],
        ),
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth < 700) {
            return Column(
              children: [
                Expanded(child: _pages[selectedIndex]),
                NavigationBar(
                  selectedIndex: selectedIndex,
                  onDestinationSelected: _selectPage,
                  destinations: const [
                    NavigationDestination(
                      icon: Icon(Icons.monitor_heart_outlined),
                      selectedIcon: Icon(Icons.monitor_heart),
                      label: 'Live',
                    ),
                    NavigationDestination(
                      icon: Icon(Icons.history_outlined),
                      selectedIcon: Icon(Icons.history),
                      label: 'History',
                    ),
                    NavigationDestination(
                      icon: Icon(Icons.inventory_2_outlined),
                      selectedIcon: Icon(Icons.inventory_2),
                      label: 'Filaments',
                    ),
                    NavigationDestination(
                      icon: Icon(Icons.settings_outlined),
                      selectedIcon: Icon(Icons.settings),
                      label: 'Settings',
                    ),
                  ],
                ),
              ],
            );
          }
          return Row(
            children: [
              NavigationRail(
                selectedIndex: selectedIndex,
                onDestinationSelected: _selectPage,
                labelType: NavigationRailLabelType.all,
                groupAlignment: -0.85,
                minWidth: 88,
                destinations: const [
                  NavigationRailDestination(
                    icon: Icon(Icons.monitor_heart_outlined),
                    selectedIcon: Icon(Icons.monitor_heart),
                    label: Text('Live'),
                  ),
                  NavigationRailDestination(
                    icon: Icon(Icons.history_outlined),
                    selectedIcon: Icon(Icons.history),
                    label: Text('History'),
                  ),
                  NavigationRailDestination(
                    icon: Icon(Icons.inventory_2_outlined),
                    selectedIcon: Icon(Icons.inventory_2),
                    label: Text('Filaments'),
                  ),
                  NavigationRailDestination(
                    icon: Icon(Icons.settings_outlined),
                    selectedIcon: Icon(Icons.settings),
                    label: Text('Settings'),
                  ),
                ],
              ),
              const VerticalDivider(thickness: 1, width: 1),
              Expanded(child: _pages[selectedIndex]),
            ],
          );
        },
      ),
    );
  }

  void _selectPage(int index) {
    setState(() => selectedIndex = index);
  }
}
