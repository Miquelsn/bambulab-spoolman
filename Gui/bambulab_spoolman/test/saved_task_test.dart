import 'package:bambulab_spoolman/model/saved_task.dart';
import 'package:bambulab_spoolman/data/web_socket_service.dart';
import 'package:bambulab_spoolman/view/tasks_view.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('builds the local backend WebSocket URL', () {
    expect(getBackendWebSocketUrl(), 'ws://localhost:12346/');
  });

  test('sorts saved tasks from newest to oldest', () {
    final tasks = savedTasksNewestFirst([
      {
        'model_name': 'Old',
        'end_time': '10:00:00-01-06-2025',
      },
      {
        'model_name': 'New',
        'end_time': '10:00:00-02-06-2025',
      },
    ]);

    expect(tasks.map((task) => task.modelName), ['New', 'Old']);
  });

  test('formats task date, time, and duration', () {
    final task = SavedTask.fromJson({
      'model_name': 'Benchy',
      'start_time': '18:40:35-19-05-2025',
      'end_time': '22:22:27-19-05-2025',
    });

    expect(task.dateLabel, '19 May 2025');
    expect(task.timeLabel, '18:40 – 22:22');
    expect(task.durationLabel, '3h 41m');
  });

  test('prefers recorded material and includes display metadata', () {
    final task = SavedTask.fromJson({
      'reported_filament': [
        {
          'filamentId': 'GFA00',
          'weight': 8.25,
          'filament_name': 'Matte Black',
          'filament_type': 'PLA',
          'filament_vendor': 'Bambu Lab',
        }
      ],
      'teoric_filaments': [
        {'filamentId': 'GFA00', 'weight': 10}
      ],
    });

    expect(task.usageIsEstimated, isFalse);
    expect(task.usedWeight, 8.25);
    expect(task.filaments.single.displayName, 'Matte Black');
    expect(task.filaments.single.details, 'Bambu Lab · PLA');
  });

  testWidgets('task card fits a narrow screen', (tester) async {
    await tester.binding.setSurfaceSize(const Size(430, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final task = SavedTask.fromJson({
      'model_name': 'Two-colour calibration model',
      'status': 'Complete',
      'total_weight': 56.18,
      'percent_complete': 99,
      'start_time': '18:40:35-19-05-2025',
      'end_time': '22:22:27-19-05-2025',
      'reported_filament': [
        {
          'filamentId': 'GFA00',
          'weight': 50,
          'filament_name': 'Matte Black',
          'filament_type': 'PLA',
          'filament_vendor': 'Bambu Lab',
        },
        {
          'filamentId': 'GFS00',
          'weight': 6.18,
          'filament_name': 'Support material',
          'filament_type': 'PLA Support',
          'filament_vendor': 'Bambu Lab',
        },
      ],
    });

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: SavedTaskCard(
              task: task,
              canEdit: false,
              isUpdating: (_) => false,
              onChangeSpool: (_) {},
            ),
          ),
        ),
      ),
    );

    expect(find.text('Two-colour calibration model'), findsOneWidget);
    expect(find.text('Material used'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
