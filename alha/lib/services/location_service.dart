// Platform-conditional export:
//   web  → location_service_web.dart (dart:html geolocation)
//   other → location_service_stub.dart (no-op, for VM unit tests)
export 'location_service_stub.dart'
    if (dart.library.html) 'location_service_web.dart';
