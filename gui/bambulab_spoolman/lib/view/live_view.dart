import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:bambulab_spoolman/data/data_model.dart';
import 'package:bambulab_spoolman/view/terminal_log_view.dart';

class LiveView extends StatefulWidget {
  const LiveView({super.key});

  @override
  State<LiveView> createState() => _LiveViewState();
}

class _LiveViewState extends State<LiveView> {
  @override
  Widget build(BuildContext context) {
    return Consumer<DataModel>(
      builder: (context, dataModel, child) {
        return Column(
          mainAxisAlignment: MainAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              spacing: 10,
              children: [
                Padding(
                  padding: const EdgeInsets.all(30.0),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 10,
                        backgroundColor:
                            dataModel.backendStatus ? Colors.green : Colors.red,
                      ),
                      Text(
                        dataModel.backendStatus
                            ? "Backend Online"
                            : "Backend Offline",
                        style: TextStyle(
                            fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
              ],
            ),
            Padding(
              padding: const EdgeInsets.all(20.0),
              child: LogTerminalView(),
            ),
            ElevatedButton(
              onPressed: () {
                dataModel.sendWebSocketMessage("Aqui");
              },
              child: Text("Yo"),
            )
          ],
        );
      },
    );
  }
}
