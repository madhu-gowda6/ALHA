/// Web implementation of LocationService.
///
/// Uses package:web + dart:js_interop with .toJS callback conversion.
/// This is the ONLY approach that reliably triggers the browser permission
/// dialog in Flutter Web with dart2js in release/minify mode.
///
/// dart:html / dart:js_util.allowInterop callbacks are tree-shaken by dart2js
/// in release builds (--minify), causing silent failures with no dialog.
import 'dart:async';
import 'dart:js_interop';

import 'package:web/web.dart' as web;

class LocationResult {
  final double? lat;
  final double? lon;
  final bool success;
  final String? errorMessage;

  const LocationResult._({
    this.lat,
    this.lon,
    required this.success,
    this.errorMessage,
  });

  factory LocationResult.success({required double lat, required double lon}) =>
      LocationResult._(lat: lat, lon: lon, success: true);

  factory LocationResult.error({required String message}) =>
      LocationResult._(success: false, errorMessage: message);
}

class LocationService {
  Future<LocationResult> getCurrentLocation() {
    // Verify secure context — geolocation silently fails (no dialog) on HTTP.
    if (!web.window.isSecureContext) {
      return Future.value(LocationResult.error(
        message: 'GPS requires HTTPS. Please access the app over a secure '
            'connection. / GPS के लिए HTTPS आवश्यक है।',
      ));
    }

    final completer = Completer<LocationResult>();

    // .toJS converts the Dart closure to a JS function that dart2js will NOT
    // tree-shake — this is the critical difference from allowInterop.
    web.window.navigator.geolocation.getCurrentPosition(
      (web.GeolocationPosition pos) {
        if (completer.isCompleted) return;
        final lat = pos.coords.latitude.toDouble();
        final lon = pos.coords.longitude.toDouble();
        completer.complete(LocationResult.success(lat: lat, lon: lon));
      }.toJS,
      (web.GeolocationPositionError err) {
        if (completer.isCompleted) return;
        // code 1 = PERMISSION_DENIED, 2 = POSITION_UNAVAILABLE, 3 = TIMEOUT
        final msg = err.code == 1
            ? 'GPS access denied. Please enter your location manually / '
                'GPS की अनुमति नहीं मिली। कृपया अपना स्थान दर्ज करें।'
            : 'Location unavailable / स्थान उपलब्ध नहीं है';
        completer.complete(LocationResult.error(message: msg));
      }.toJS,
      web.PositionOptions(
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0,
      ),
    );

    return completer.future;
  }
}
