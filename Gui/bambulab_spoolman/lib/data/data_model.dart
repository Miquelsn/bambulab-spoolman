import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../model/log_event.dart';
import '../model/printer_configuration.dart';
import '../model/printer_status.dart';
import '../model/spool_option.dart';
import 'web_socket_service.dart';

class DataModel extends ChangeNotifier {
  DataModel() {
    _webSocketService = WebSocketService(
      onConnectedCallback: _onWebSocketConnected,
      onDisconnectedCallback: _handleDisconnection,
    );
    _messageSubscription = _webSocketService.messageStream.listen(
      _processReceivedMessage,
      onError: _handleDisconnection,
    );
  }

  late final WebSocketService _webSocketService;
  StreamSubscription<String>? _messageSubscription;
  Timer? _reconnectTimer;
  Timer? _taskTimeout;
  bool _disposed = false;

  bool backendStatus = false;
  String lastMessage = '';
  String? connectionMessage = 'Connecting to the backend…';
  String? tasksError;
  List<LogEvent> logs = [];
  List<Map<String, dynamic>> tasks = [];
  List<SpoolOption> spools = [];
  List<PrinterStatus> printers = [];
  final Set<String> updatingFilaments = {};
  String? taskMutationMessage;
  bool taskMutationFailed = false;
  bool tasksLoaded = false;

  bool settingsLoaded = false;
  bool authBusy = false;
  bool printerDiscoveryBusy = false;
  bool printerUpdateBusy = false;
  bool spoolmanBusy = false;
  bool cloudAuthenticated = false;
  String cloudEmail = '';
  String cloudAuthStatus = '';
  String spoolmanHost = '';
  String spoolmanPort = '7912';
  String? settingsMessage;
  bool settingsMessageFailed = false;
  List<PrinterConfiguration> printerConfigurations = [];

  bool sendWebSocketMessage(String message) {
    return _webSocketService.sendMessage(message);
  }

  bool _sendAction(String action, [Map<String, dynamic>? fields]) {
    return sendWebSocketMessage(json.encode({'action': action, ...?fields}));
  }

  void refreshTasks() {
    _taskTimeout?.cancel();
    if (!backendStatus) {
      tasksLoaded = true;
      tasksError =
          'The backend is offline. Reconnect to refresh print history.';
      _notify();
      return;
    }

    tasksLoaded = false;
    tasksError = null;
    _notify();
    _sendAction('get_tasks');
    _taskTimeout = Timer(const Duration(seconds: 10), () {
      if (!tasksLoaded) {
        tasksLoaded = true;
        tasksError = 'Print history did not respond. Try refreshing again.';
        _notify();
      }
    });
  }

  void refreshLogs() {
    if (!backendStatus) return;
    _sendAction('get_logs');
    _sendAction('get_printers');
  }

  void refreshSpools() {
    if (backendStatus) _sendAction('get_spools');
  }

  void loadSettings() {
    if (backendStatus) _sendAction('get_settings');
  }

  bool loginToBambu({required String email, required String password}) {
    if (!backendStatus || authBusy) return false;
    authBusy = true;
    cloudAuthStatus = '';
    settingsMessage = null;
    _notify();
    final sent =
        _sendAction('bambu_login', {'email': email, 'password': password});
    if (!sent) {
      authBusy = false;
      settingsMessage = 'The backend disconnected before login started.';
      settingsMessageFailed = true;
      _notify();
    }
    return sent;
  }

  bool submitBambuVerification({required String email, required String code}) {
    if (!backendStatus || authBusy) return false;
    authBusy = true;
    settingsMessage = null;
    _notify();
    final sent = _sendAction('bambu_verify', {'email': email, 'code': code});
    if (!sent) {
      authBusy = false;
      settingsMessage = 'The backend disconnected before verification started.';
      settingsMessageFailed = true;
      _notify();
    }
    return sent;
  }

  bool discoverPrinters() {
    if (!backendStatus || printerDiscoveryBusy) return false;
    printerDiscoveryBusy = true;
    settingsMessage = 'Searching the local network for Bambu printers…';
    settingsMessageFailed = false;
    _notify();
    final sent = _sendAction('discover_printers');
    if (!sent) {
      printerDiscoveryBusy = false;
      settingsMessage = 'The backend disconnected before discovery started.';
      settingsMessageFailed = true;
      _notify();
    }
    return sent;
  }

  bool updatePrinter({
    required String deviceId,
    required String ip,
    required String accessCode,
    required bool enabled,
  }) {
    if (!backendStatus || printerUpdateBusy) return false;
    printerUpdateBusy = true;
    settingsMessage = null;
    _notify();
    final sent = _sendAction('update_printer', {
      'device_id': deviceId,
      'ip': ip,
      'access_code': accessCode,
      'enabled': enabled,
    });
    if (!sent) {
      printerUpdateBusy = false;
      settingsMessage = 'The backend disconnected before saving the printer.';
      settingsMessageFailed = true;
      _notify();
    }
    return sent;
  }

  bool updateSpoolman({required String host, required String port}) {
    if (!backendStatus || spoolmanBusy) return false;
    spoolmanBusy = true;
    settingsMessage = null;
    _notify();
    final sent = _sendAction('update_spoolman', {'host': host, 'port': port});
    if (!sent) {
      spoolmanBusy = false;
      settingsMessage = 'The backend disconnected before saving Spoolman.';
      settingsMessageFailed = true;
      _notify();
    }
    return sent;
  }

  void clearSettingsMessage() {
    settingsMessage = null;
    _notify();
  }

  bool updateTaskFilament({
    required String historyId,
    required int filamentIndex,
    required String spoolId,
  }) {
    if (!backendStatus || historyId.isEmpty) return false;
    final key = '$historyId:$filamentIndex';
    updatingFilaments.add(key);
    taskMutationMessage = null;
    taskMutationFailed = false;
    _notify();
    final sent = _sendAction('update_task_filament', {
      'history_id': historyId,
      'filament_index': filamentIndex,
      'spool_id': spoolId,
    });
    if (!sent) {
      updatingFilaments.remove(key);
      taskMutationMessage =
          'The backend disconnected before saving the change.';
      taskMutationFailed = true;
      _notify();
    }
    return sent;
  }

  bool isUpdatingFilament(String historyId, int index) {
    return updatingFilaments.contains('$historyId:$index');
  }

  void clearTaskMutationMessage() {
    taskMutationMessage = null;
    _notify();
  }

  Future<void> reconnect() async {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    connectionMessage = 'Connecting to the backend…';
    _notify();
    await _webSocketService.reconnect();
  }

  void _processReceivedMessage(String message) {
    lastMessage = message;
    try {
      final decoded = json.decode(message);
      if (decoded is! Map<String, dynamic>) return;

      final type = decoded['type'];
      final payload = decoded['payload'];
      if (type == 'logs' && payload is List) {
        logs = payload
            .whereType<Map>()
            .map((item) => LogEvent.fromJson(Map<String, dynamic>.from(item)))
            .toList(growable: false);
      } else if (type == 'tasks' && payload is List) {
        _taskTimeout?.cancel();
        tasks = payload
            .whereType<Map>()
            .map((task) => Map<String, dynamic>.from(task))
            .toList(growable: false);
        tasksLoaded = true;
        tasksError = null;
      } else if (type == 'spools' && payload is List) {
        spools = payload
            .whereType<Map>()
            .map(
                (item) => SpoolOption.fromJson(Map<String, dynamic>.from(item)))
            .where((spool) => spool.id.isNotEmpty)
            .toList(growable: false);
      } else if (type == 'printers' && payload is List) {
        printers = payload
            .whereType<Map>()
            .map((item) =>
                PrinterStatus.fromJson(Map<String, dynamic>.from(item)))
            .toList(growable: false);
      } else if (type == 'settings' && payload is Map) {
        final settings = Map<String, dynamic>.from(payload);
        final cloud = settings['cloud'];
        final spoolman = settings['spoolman'];
        final configuredPrinters = settings['printers'];
        if (cloud is Map) {
          cloudEmail = cloud['email']?.toString() ?? '';
          cloudAuthenticated = cloud['authenticated'] == true;
        }
        if (spoolman is Map) {
          spoolmanHost = spoolman['host']?.toString() ?? '';
          spoolmanPort = spoolman['port']?.toString() ?? '7912';
        }
        if (configuredPrinters is List) {
          printerConfigurations = configuredPrinters
              .whereType<Map>()
              .map((item) => PrinterConfiguration.fromJson(
                    Map<String, dynamic>.from(item),
                  ))
              .where((printer) => printer.id.isNotEmpty)
              .toList(growable: false);
        }
        settingsLoaded = true;
      } else if (type == 'auth_result' && payload is Map) {
        authBusy = false;
        cloudAuthStatus = payload['status']?.toString() ?? 'error';
        settingsMessage = payload['message']?.toString() ?? 'Login failed.';
        settingsMessageFailed = cloudAuthStatus != 'success' &&
            cloudAuthStatus != 'needs_verification_code';
        if (cloudAuthStatus == 'success') cloudAuthenticated = true;
      } else if (type == 'printer_discovery_result' && payload is Map) {
        printerDiscoveryBusy = false;
        settingsMessage = payload['message']?.toString();
        settingsMessageFailed = payload['status'] != 'success';
      } else if (type == 'printer_update_result' && payload is Map) {
        printerUpdateBusy = false;
        settingsMessage = payload['message']?.toString();
        settingsMessageFailed = payload['status'] != 'success';
      } else if (type == 'spoolman_update_result' && payload is Map) {
        spoolmanBusy = false;
        settingsMessage = payload['message']?.toString();
        settingsMessageFailed = payload['status'] != 'success';
      } else if (type == 'task_updated' && payload is Map) {
        final historyId = payload['history_id']?.toString();
        if (historyId != null) {
          updatingFilaments.removeWhere((key) => key.startsWith('$historyId:'));
        }
        taskMutationMessage = 'Spoolman usage and task history were updated.';
        taskMutationFailed = false;
        refreshTasks();
        refreshLogs();
      } else if (type == 'mutation_error' && payload is Map) {
        final historyId = payload['history_id']?.toString() ?? '';
        final index = payload['filament_index'];
        updatingFilaments.remove('$historyId:$index');
        taskMutationMessage =
            payload['message']?.toString() ?? 'The task could not be updated.';
        taskMutationFailed = true;
      }
    } on FormatException {
      connectionMessage = 'The backend returned an unreadable response.';
    }
    _notify();
  }

  void _handleDisconnection([Object? error]) {
    backendStatus = false;
    connectionMessage = 'Backend offline. Retrying automatically…';
    tasksLoaded = true;
    updatingFilaments.clear();
    authBusy = false;
    printerDiscoveryBusy = false;
    printerUpdateBusy = false;
    spoolmanBusy = false;
    tasksError = tasks.isEmpty
        ? 'Print history is unavailable while the backend is offline.'
        : 'Backend offline. Showing the last loaded print history.';
    _notify();
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_disposed || _reconnectTimer != null) return;
    _reconnectTimer = Timer(const Duration(seconds: 3), () async {
      _reconnectTimer = null;
      final connected = await _webSocketService.reconnect();
      if (!connected) _scheduleReconnect();
    });
  }

  void _onWebSocketConnected() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    backendStatus = true;
    connectionMessage = null;
    refreshTasks();
    refreshLogs();
    refreshSpools();
    loadSettings();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _taskTimeout?.cancel();
    _reconnectTimer?.cancel();
    unawaited(_messageSubscription?.cancel());
    unawaited(_webSocketService.closeConnection());
    super.dispose();
  }
}
