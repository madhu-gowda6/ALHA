import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

enum WsConnectionState { disconnected, connecting, connected, reconnecting }

class WebSocketService {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  StreamController<Map<String, dynamic>>? _messageController;
  final _stateController = StreamController<WsConnectionState>.broadcast();

  String? _url;
  String? _token;
  WsConnectionState _state = WsConnectionState.disconnected;
  bool _shouldReconnect = false;
  int _reconnectDelay = 1;

  WsConnectionState get connectionState => _state;
  Stream<WsConnectionState> get connectionStateStream => _stateController.stream;

  Stream<Map<String, dynamic>> get messages {
    _messageController ??= StreamController<Map<String, dynamic>>.broadcast();
    return _messageController!.stream;
  }

  void connect(String url, String token) {
    _url = url;
    _token = token;
    _shouldReconnect = true;
    _messageController ??= StreamController<Map<String, dynamic>>.broadcast();
    _doConnect();
  }

  void _doConnect() {
    _setState(WsConnectionState.connecting);
    try {
      _channel = WebSocketChannel.connect(Uri.parse('$_url?token=$_token'));
      _subscription = _channel!.stream.listen(
        _onData,
        onError: _onError,
        onDone: _onDone,
      );
      // Wait for actual WebSocket handshake before marking connected
      _channel!.ready.then((_) {
        _setState(WsConnectionState.connected);
        _reconnectDelay = 1;
      }).catchError((e) {
        debugPrint('WebSocket ready error: $e');
        if (_shouldReconnect) _scheduleReconnect();
      });
    } catch (e) {
      debugPrint('WebSocket connect error: $e');
      _scheduleReconnect();
    }
  }

  void _onData(dynamic data) {
    try {
      final json = jsonDecode(data as String) as Map<String, dynamic>;
      _messageController?.add(json);
    } catch (e) {
      debugPrint('WebSocket parse error: $e');
    }
  }

  void _onError(dynamic error) {
    debugPrint('WebSocket error: $error');
    if (_shouldReconnect) _scheduleReconnect();
  }

  void _onDone() {
    if (_shouldReconnect) {
      _scheduleReconnect();
    } else {
      _setState(WsConnectionState.disconnected);
    }
  }

  void _scheduleReconnect() {
    if (!_shouldReconnect) return;
    _setState(WsConnectionState.reconnecting);
    Future.delayed(Duration(seconds: _reconnectDelay), () {
      if (_shouldReconnect) {
        _reconnectDelay = (_reconnectDelay * 2).clamp(1, 30);
        _doConnect();
      }
    });
  }

  void send(Map<String, dynamic> message) {
    if (_state == WsConnectionState.connected && _channel != null) {
      _channel!.sink.add(jsonEncode(message));
    }
  }

  void disconnect() {
    _shouldReconnect = false;
    _subscription?.cancel();
    _channel?.sink.close();
    _channel = null;
    _setState(WsConnectionState.disconnected);
  }

  void _setState(WsConnectionState state) {
    _state = state;
    if (!_stateController.isClosed) _stateController.add(state);
  }

  void dispose() {
    disconnect();
    _stateController.close();
    _messageController?.close();
  }
}
