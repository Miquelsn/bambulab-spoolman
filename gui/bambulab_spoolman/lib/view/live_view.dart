import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:bambulab_spoolman/data/data_model.dart';

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
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircleAvatar(
                    radius: 10,
                    backgroundColor: dataModel.backendStatus ? Colors.green : Colors.red,
                  ),
                  const SizedBox(height: 10),
                  Text(
                    dataModel.backendStatus ? "Backend Online" : "Backend Offline",
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              ElevatedButton(onPressed: (){dataModel.sendWebSocketMessage("Aqui"); print("AQA");},child: Text("Yo"),)
            ],
          ),
        );
      },
    );
  }
}
