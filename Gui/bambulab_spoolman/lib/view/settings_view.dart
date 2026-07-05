import 'package:bambulab_spoolman/data/data_model.dart';
import 'package:bambulab_spoolman/model/printer_configuration.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class SettingsView extends StatefulWidget {
  const SettingsView({super.key});

  @override
  State<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends State<SettingsView> {
  final emailController = TextEditingController();
  final passwordController = TextEditingController();
  final verificationController = TextEditingController();
  final spoolmanHostController = TextEditingController();
  final spoolmanPortController = TextEditingController(text: '7912');
  String _settingsFingerprint = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) context.read<DataModel>().loadSettings();
    });
  }

  @override
  void dispose() {
    emailController.dispose();
    passwordController.dispose();
    verificationController.dispose();
    spoolmanHostController.dispose();
    spoolmanPortController.dispose();
    super.dispose();
  }

  void _syncSettings(DataModel model) {
    if (!model.settingsLoaded) return;
    final fingerprint =
        '${model.cloudEmail}|${model.spoolmanHost}|${model.spoolmanPort}';
    if (fingerprint == _settingsFingerprint) return;
    _settingsFingerprint = fingerprint;
    emailController.text = model.cloudEmail;
    spoolmanHostController.text = model.spoolmanHost;
    spoolmanPortController.text = model.spoolmanPort;
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<DataModel>(
      builder: (context, model, child) {
        _syncSettings(model);
        return ListView(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 48),
          children: [
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 960),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Settings',
                      style:
                          Theme.of(context).textTheme.headlineMedium?.copyWith(
                                fontWeight: FontWeight.w800,
                              ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Connect services and choose which printers this dashboard monitors.',
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                            color:
                                Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                    if (!model.backendStatus) ...[
                      const SizedBox(height: 16),
                      const _Notice(
                        icon: Icons.cloud_off_outlined,
                        message:
                            'The backend is offline. Settings will become available when it reconnects.',
                        isError: true,
                      ),
                    ],
                    if (model.settingsMessage != null) ...[
                      const SizedBox(height: 16),
                      _Notice(
                        icon: model.settingsMessageFailed
                            ? Icons.error_outline
                            : Icons.info_outline,
                        message: model.settingsMessage!,
                        isError: model.settingsMessageFailed,
                        onDismiss: model.clearSettingsMessage,
                      ),
                    ],
                    const SizedBox(height: 20),
                    _cloudCard(context, model),
                    const SizedBox(height: 16),
                    _printersCard(context, model),
                    const SizedBox(height: 16),
                    _spoolmanCard(context, model),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _cloudCard(BuildContext context, DataModel model) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SectionHeader(
              icon: Icons.cloud_outlined,
              title: 'Bambu Cloud',
              subtitle: 'Used to load your bound printers and print metadata.',
              trailing: _StatusChip(
                label:
                    model.cloudAuthenticated ? 'Connected' : 'Sign in required',
                positive: model.cloudAuthenticated,
              ),
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: [
                SizedBox(
                  width: 360,
                  child: TextField(
                    controller: emailController,
                    enabled: !model.authBusy,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.email],
                    decoration: const InputDecoration(
                      labelText: 'Email',
                      prefixIcon: Icon(Icons.email_outlined),
                    ),
                  ),
                ),
                SizedBox(
                  width: 360,
                  child: TextField(
                    controller: passwordController,
                    enabled: !model.authBusy,
                    obscureText: true,
                    autofillHints: const [AutofillHints.password],
                    onSubmitted: (_) => _login(model),
                    decoration: const InputDecoration(
                      labelText: 'Password',
                      prefixIcon: Icon(Icons.lock_outline),
                      helperText: 'Used for this login only; never saved.',
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton.icon(
                onPressed: model.authBusy || !model.backendStatus
                    ? null
                    : () => _login(model),
                icon: model.authBusy
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.login),
                label: Text(model.authBusy ? 'Connecting…' : 'Connect account'),
              ),
            ),
            if (model.cloudAuthStatus == 'needs_verification_code') ...[
              const Divider(height: 36),
              Text(
                'Email verification',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 6),
              const Text('Enter the code Bambu Lab sent to your email.'),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: verificationController,
                      enabled: !model.authBusy,
                      keyboardType: TextInputType.number,
                      onSubmitted: (_) => _verify(model),
                      decoration: const InputDecoration(
                        labelText: 'Verification code',
                        prefixIcon: Icon(Icons.verified_user_outlined),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  FilledButton(
                    onPressed: model.authBusy ? null : () => _verify(model),
                    child: const Text('Verify'),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _login(DataModel model) {
    final email = emailController.text.trim();
    final password = passwordController.text;
    if (email.isEmpty || password.isEmpty) {
      _showError('Enter both your email and password.');
      return;
    }
    model.loginToBambu(email: email, password: password);
  }

  void _verify(DataModel model) {
    final code = verificationController.text.trim();
    if (code.isEmpty) {
      _showError('Enter the verification code from your email.');
      return;
    }
    model.submitBambuVerification(
      email: emailController.text.trim(),
      code: code,
    );
  }

  Widget _printersCard(BuildContext context, DataModel model) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SectionHeader(
              icon: Icons.print_outlined,
              title: 'Printers',
              subtitle:
                  'Addresses are discovered automatically from Bambu LAN announcements.',
              trailing: OutlinedButton.icon(
                onPressed: model.printerDiscoveryBusy || !model.backendStatus
                    ? null
                    : model.discoverPrinters,
                icon: model.printerDiscoveryBusy
                    ? const SizedBox.square(
                        dimension: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.radar),
                label: Text(
                  model.printerDiscoveryBusy ? 'Searching…' : 'Discover',
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Turn off monitoring for a printer that is inactive or unavailable. It will be omitted without blocking the service.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            const SizedBox(height: 16),
            if (!model.settingsLoaded)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (model.printerConfigurations.isEmpty)
              const _EmptyState(
                icon: Icons.print_disabled_outlined,
                message:
                    'No printers are loaded yet. Connect your Bambu Cloud account first.',
              )
            else
              ...model.printerConfigurations.map(
                (printer) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _PrinterCard(
                    key: ValueKey(printer.id),
                    printer: printer,
                    busy: model.printerUpdateBusy,
                    onSave: model.updatePrinter,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _spoolmanCard(BuildContext context, DataModel model) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const _SectionHeader(
              icon: Icons.inventory_2_outlined,
              title: 'Spoolman',
              subtitle:
                  'Connect the local Spoolman API used for filament usage.',
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                SizedBox(
                  width: 360,
                  child: TextField(
                    controller: spoolmanHostController,
                    enabled: !model.spoolmanBusy,
                    decoration: const InputDecoration(
                      labelText: 'Spoolman host or IP',
                      prefixIcon: Icon(Icons.dns_outlined),
                    ),
                  ),
                ),
                SizedBox(
                  width: 180,
                  child: TextField(
                    controller: spoolmanPortController,
                    enabled: !model.spoolmanBusy,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Port',
                      prefixIcon: Icon(Icons.numbers),
                    ),
                  ),
                ),
                FilledButton.icon(
                  onPressed: model.spoolmanBusy || !model.backendStatus
                      ? null
                      : () => model.updateSpoolman(
                            host: spoolmanHostController.text.trim(),
                            port: spoolmanPortController.text.trim(),
                          ),
                  icon: model.spoolmanBusy
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.link),
                  label:
                      Text(model.spoolmanBusy ? 'Testing…' : 'Test and save'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}

class _PrinterCard extends StatefulWidget {
  const _PrinterCard({
    super.key,
    required this.printer,
    required this.busy,
    required this.onSave,
  });

  final PrinterConfiguration printer;
  final bool busy;
  final bool Function({
    required String deviceId,
    required String ip,
    required String accessCode,
    required bool enabled,
  }) onSave;

  @override
  State<_PrinterCard> createState() => _PrinterCardState();
}

class _PrinterCardState extends State<_PrinterCard> {
  late final TextEditingController ipController;
  late final TextEditingController accessCodeController;
  late bool enabled;

  @override
  void initState() {
    super.initState();
    ipController = TextEditingController(text: widget.printer.ip);
    accessCodeController = TextEditingController();
    enabled = widget.printer.enabled;
  }

  @override
  void didUpdateWidget(covariant _PrinterCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.printer.ip != widget.printer.ip &&
        ipController.text == oldWidget.printer.ip) {
      ipController.text = widget.printer.ip;
    }
    if (oldWidget.printer.enabled != widget.printer.enabled) {
      enabled = widget.printer.enabled;
    }
    if (!oldWidget.printer.hasAccessCode && widget.printer.hasAccessCode) {
      accessCodeController.clear();
    }
  }

  @override
  void dispose() {
    ipController.dispose();
    accessCodeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final printer = widget.printer;
    final colorScheme = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerLowest,
        border: Border.all(color: colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                final details = Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      printer.name,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    Text(
                      [printer.model, printer.id]
                          .whereType<String>()
                          .where((value) => value.isNotEmpty)
                          .join(' · '),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                    ),
                  ],
                );
                final status = _StatusChip(
                  label: !enabled
                      ? 'Omitted'
                      : printer.connected
                          ? 'Connected'
                          : 'Offline',
                  positive: enabled && printer.connected,
                );
                if (constraints.maxWidth < 420) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      details,
                      const SizedBox(height: 8),
                      status,
                    ],
                  );
                }
                return Row(
                  children: [
                    Expanded(child: details),
                    const SizedBox(width: 12),
                    status,
                  ],
                );
              },
            ),
            const SizedBox(height: 12),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Monitor this printer'),
              subtitle: const Text(
                'Turn this off to omit an inactive printer from connections and print tracking.',
              ),
              value: enabled,
              onChanged: widget.busy
                  ? null
                  : (value) => setState(() => enabled = value),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                SizedBox(
                  width: 260,
                  child: TextField(
                    controller: ipController,
                    enabled: !widget.busy && enabled,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Local IP address',
                      prefixIcon: Icon(Icons.lan_outlined),
                      helperText: 'Usually filled by Discover.',
                    ),
                  ),
                ),
                SizedBox(
                  width: 300,
                  child: TextField(
                    controller: accessCodeController,
                    enabled: !widget.busy && enabled,
                    obscureText: true,
                    decoration: InputDecoration(
                      labelText: printer.hasAccessCode
                          ? 'New LAN access code'
                          : 'LAN access code',
                      prefixIcon: const Icon(Icons.key_outlined),
                      helperText: printer.hasAccessCode
                          ? 'Leave blank to keep the saved code.'
                          : 'Shown in the printer network settings.',
                    ),
                  ),
                ),
                FilledButton.icon(
                  onPressed: widget.busy
                      ? null
                      : () => widget.onSave(
                            deviceId: printer.id,
                            ip: ipController.text.trim(),
                            accessCode: accessCodeController.text.trim(),
                            enabled: enabled,
                          ),
                  icon: widget.busy
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save_outlined),
                  label: const Text('Save'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.trailing,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final titleText = Text(
      title,
      style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.w700,
          ),
    );
    final subtitleText = Text(
      subtitle,
      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 560) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, color: Theme.of(context).colorScheme.primary),
                  const SizedBox(width: 12),
                  Expanded(child: titleText),
                ],
              ),
              const SizedBox(height: 6),
              subtitleText,
              if (trailing != null) ...[
                const SizedBox(height: 10),
                Align(alignment: Alignment.centerRight, child: trailing!),
              ],
            ],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: Theme.of(context).colorScheme.primary),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [titleText, const SizedBox(height: 2), subtitleText],
              ),
            ),
            if (trailing != null) ...[
              const SizedBox(width: 12),
              trailing!,
            ],
          ],
        );
      },
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.positive});

  final String label;
  final bool positive;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Chip(
      avatar: Icon(
        positive ? Icons.check_circle_outline : Icons.info_outline,
        size: 17,
        color: positive ? colors.primary : colors.onSurfaceVariant,
      ),
      label: Text(label),
      visualDensity: VisualDensity.compact,
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({
    required this.icon,
    required this.message,
    required this.isError,
    this.onDismiss,
  });

  final IconData icon;
  final String message;
  final bool isError;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final color = isError ? colors.error : colors.primary;
    return Material(
      color: color.withValues(alpha: 0.09),
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            Icon(icon, color: color),
            const SizedBox(width: 10),
            Expanded(child: Text(message)),
            if (onDismiss != null)
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

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 24),
      child: Column(
        children: [
          Icon(
            icon,
            size: 38,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 10),
          Text(message, textAlign: TextAlign.center),
        ],
      ),
    );
  }
}
