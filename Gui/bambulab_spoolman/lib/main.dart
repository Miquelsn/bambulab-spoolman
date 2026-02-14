import 'package:bambulab_spoolman/view/settings_view.dart';
import 'package:flutter/material.dart';
import 'package:bambulab_spoolman/view/live_view.dart';
import 'package:bambulab_spoolman/view/tasks_view.dart';
import 'package:bambulab_spoolman/data/data_model.dart';
import 'package:bambulab_spoolman/view/filaments_map_view.dart';
import 'package:provider/provider.dart'; 
import 'package:bambulab_spoolman/data/filament_model.dart';
import 'package:bambulab_spoolman/data/web_socket_service.dart';

void main() {
  final webSocketService = WebSocketService();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(
            create: (_) => DataModel(webSocketService: webSocketService)),
        ChangeNotifierProvider(
            create: (_) => FilamentMappingModel(webSocketService: webSocketService)),
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
      title: 'Spoolman-Bambulab',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color.fromARGB(255, 46, 162, 185),
        ),
        useMaterial3: true,
      ),
      home: const MyHomePage(title: 'Bambulab Spoolman Integration'),
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

  static final List<Widget> _pages = <Widget>[
    LiveView(),
    FilamentsMapView(),
    TasksView(),
    SettingsView(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
      ),
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: selectedIndex,
            onDestinationSelected: (int index) {
              setState(() {
                selectedIndex = index;
              });
            },
            labelType: NavigationRailLabelType.all,
            destinations: const <NavigationRailDestination>[
              NavigationRailDestination(
                icon: Icon(Icons.home),
                selectedIcon: Icon(Icons.home_filled),
                label: Text('Live'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.change_circle),
                selectedIcon: Icon(Icons.change_circle),
                label: Text('Filaments Map'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.settings),
                selectedIcon: Icon(Icons.settings_applications),
                label: Text('Tasks'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.info),
                selectedIcon: Icon(Icons.info_outline),
                label: Text('Settings'),
              ),
            ],
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(
            child: _pages[selectedIndex],
          ),
        ],
      ),
    );
  }
}
