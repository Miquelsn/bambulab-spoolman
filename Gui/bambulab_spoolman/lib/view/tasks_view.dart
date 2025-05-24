import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../data/data_model.dart';

class TasksView extends StatefulWidget {
  const TasksView({super.key});

  @override
  State<TasksView> createState() => _TasksViewState();
}

class _TasksViewState extends State<TasksView> {
  @override
  void initState() {
    super.initState();
    final dataModel = Provider.of<DataModel>(context, listen: false);
    dataModel.sendWebSocketMessage("get_tasks");
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DataModel>(
      builder: (context, dataModel, child) {
        final tasks = dataModel.tasks;

        if (tasks.isEmpty) {
          return const Center(child: CircularProgressIndicator());
        }

        return ListView.builder(
          itemCount: tasks.length,
          itemBuilder: (context, index) {
            final task = tasks[index];
            return Card(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: ListTile(
                leading: Text(task["model_name"] ?? "—"),
                title: Text(task["model_name"] ?? "Unknown"),
                subtitle: Text("Weight: ${task["total_weight"]}g\nStatus: ${task["status"]}"),
              ),
            );
          },
        );
      },
    );
  }
}
