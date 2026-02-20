import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:bambulab_spoolman/data/data_model.dart';

class SettingsView extends StatefulWidget {
  const SettingsView({super.key});

  @override
  State<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends State<SettingsView> {
  final _formKey = GlobalKey<FormState>();

  late TextEditingController printerIpController;
  late TextEditingController spoolmanIpController;
  late TextEditingController spoolmanPortController;

  late TextEditingController emailController;
  late TextEditingController passwordController;

  @override
  void initState() {
    super.initState();
    final model = context.read<DataModel>();

    model.sendWebSocketMessage("get_local_settings");

    printerIpController = TextEditingController(text: model.printerIp);
    spoolmanIpController = TextEditingController(text: model.spoolmanIp);
    spoolmanPortController =
        TextEditingController(text: model.spoolmanPort.toString());

    model.sendWebSocketMessage("get_bambucloud_settings");
    emailController = TextEditingController(text: model.email);
    passwordController = TextEditingController(text: model.password);
  }

  @override
  void dispose() {
    printerIpController.dispose();
    spoolmanIpController.dispose();
    spoolmanPortController.dispose();
    emailController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  void _undoChanges() {
    final model = context.read<DataModel>();

    printerIpController.text = model.printerIp;
    spoolmanIpController.text = model.spoolmanIp;
    spoolmanPortController.text = model.spoolmanPort.toString();
  }

  void _saveLocalChanges() {
    if (_formKey.currentState!.validate()) {
      final model = context.read<DataModel>();

      model.updateLocalSettings(
        newPrinterIp: printerIpController.text.trim(),
        newSpoolmanIp: spoolmanIpController.text.trim(),
        newSpoolmanPort: int.parse(spoolmanPortController.text.trim()),
      );

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Settings saved")),
      );
    }
  }

  void _saveBambuCredentials() {
    if (emailController.text.isEmpty || passwordController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Email and password required")),
      );
      return;
    }

    final model = context.read<DataModel>();

    model.updateBambuCredentials(
      newEmail: emailController.text.trim(),
      newPassword: passwordController.text.trim(),
    );
  }

  void _showTfaDialog(BuildContext context, DataModel model) {
    final codeController = TextEditingController();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => AlertDialog(
        title: const Text("Two-Factor Authentication"),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text("Enter the 6-digit code from your authenticator app."),
            const SizedBox(height: 12),
            TextField(
              controller: codeController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: "Authenticator Code",
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Cancel"),
          ),
          ElevatedButton(
            onPressed: () {
              final code = codeController.text.trim();
              if (code.isNotEmpty) {
                Navigator.pop(context);
                model.sendTfaCode(code);
              }
            },
            child: const Text("Verify"),
          ),
        ],
      ),
    );
  }

  void _showVerificationDialog(BuildContext context, DataModel model) {
    final codeController = TextEditingController();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => AlertDialog(
        title: const Text("Email Verification Required"),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text("Enter the verification code sent to your email."),
            const SizedBox(height: 12),
            TextField(
              controller: codeController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: "Verification Code",
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Cancel"),
          ),
          ElevatedButton(
            onPressed: () {
              final code = codeController.text.trim();
              if (code.isNotEmpty) {
                Navigator.pop(context);
                model.sendVerificationCode(code);
              }
            },
            child: const Text("Verify"),
          ),
        ],
      ),
    );
  }

  void _showLoginResultDialog(BuildContext context, DataModel model) {
    String title = "Login Status";
    String message = "";

    switch (model.bambuLoginStatus) {
      case "success":
        title = "Login Successful";
        message = "Connected to BambuCloud successfully.";
        break;

      case "bad_credentials":
        title = "Login Failed";
        message = "Incorrect email or password.";
        break;

      case "network_error":
        title = "Connection Error";
        message = "Cannot reach BambuCloud. Check your internet connection.";
        break;

      case "needs_verification_code":
        _showVerificationDialog(context, model);
        return;

      case "needs_tfa":
        _showTfaDialog(context, model);
        return;

      default:
        message = "Unknown error occurred.";
    }

    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("OK"),
          )
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DataModel>(
      builder: (context, model, child) {
        // 🔄 Sync controllers with backend values AFTER they arrive
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (printerIpController.text != model.printerIp) {
            printerIpController.text = model.printerIp;
          }
          if (spoolmanIpController.text != model.spoolmanIp) {
            spoolmanIpController.text = model.spoolmanIp;
          }
          if (spoolmanPortController.text != model.spoolmanPort.toString()) {
            spoolmanPortController.text = model.spoolmanPort.toString();
          }
          if (emailController.text != model.email) {
            emailController.text = model.email;
          }
          if (passwordController.text != model.password) {
            passwordController.text = model.password;
          }

          if (model.bambuLoginStatus.isNotEmpty) {
            _showLoginResultDialog(context, model);
            model.bambuLoginStatus = ""; // reset so it doesn't repeat
          }
        });

        return Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Center(
                child: Text("Settings",
                    style:
                        TextStyle(fontSize: 32, fontWeight: FontWeight.bold)),
              ),
              const Divider(height: 32),

              const Center(
                child: Text("Local settings",
                    style:
                        TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
              ),
              const SizedBox(height: 16),

              /// Printer IP
              TextFormField(
                controller: printerIpController,
                decoration: const InputDecoration(
                  labelText: 'BambuLab Printer IP',
                  border: OutlineInputBorder(),
                ),
                validator: (value) =>
                    value == null || value.isEmpty ? "Enter printer IP" : null,
              ),
              const SizedBox(height: 16),

              /// Spoolman IP
              TextFormField(
                controller: spoolmanIpController,
                decoration: const InputDecoration(
                  labelText: 'Spoolman IP',
                  border: OutlineInputBorder(),
                ),
                validator: (value) =>
                    value == null || value.isEmpty ? "Enter Spoolman IP" : null,
              ),
              const SizedBox(height: 16),

              /// Spoolman Port
              TextFormField(
                controller: spoolmanPortController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Spoolman Port (Default 7912)',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) return "Enter port";
                  final port = int.tryParse(value);
                  if (port == null || port <= 0 || port > 65535) {
                    return "Invalid port";
                  }
                  return null;
                },
              ),

              const SizedBox(height: 32),

              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  OutlinedButton.icon(
                    onPressed: _undoChanges,
                    icon: const Icon(Icons.undo),
                    label: const Text("Undo"),
                  ),
                  ElevatedButton.icon(
                    onPressed: _saveLocalChanges,
                    icon: const Icon(Icons.save),
                    label: const Text("Save"),
                  ),
                ],
              ),
              const Divider(height: 32),

              const Center(
                child: Text("BambuCloud settings",
                    style:
                        TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
              ),
              const SizedBox(height: 16),

              /// Email
              TextFormField(
                controller: emailController,
                decoration: const InputDecoration(
                  labelText: 'BambuCloud Email',
                  border: OutlineInputBorder(),
                ),
              ),

              const SizedBox(height: 16),

              /// Password
              TextFormField(
                controller: passwordController,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'BambuCloud Password',
                  border: OutlineInputBorder(),
                ),
              ),

              const SizedBox(height: 16),

              ElevatedButton.icon(
                onPressed: model.isLoggingIn ? null : _saveBambuCredentials,
                icon: model.isLoggingIn
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.login),
                label: Text(model.isLoggingIn
                    ? "Logging in..."
                    : "Login to BambuCloud"),
              ),
              const SizedBox(height: 12),
            ],
          ),
        );
      },
    );
  }
}
