/// Stub implementation used on non-web platforms (e.g., VM unit tests).
/// Web builds use location_service_web.dart via the conditional export in
/// location_service.dart.

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
  Future<LocationResult> getCurrentLocation() async {
    return LocationResult.error(
      message: 'GPS not available in this environment',
    );
  }
}
