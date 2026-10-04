import 'dart:math' as math;
import '../models/zone_model.dart';

/// Production DSA implementation:
/// Spatial Index for O(N) / Geospatial Nearest-Neighbor queries
/// using the Haversine Great-Circle distance formula.
class SpatialIndex {
  static const double earthRadiusKm = 6371.0;

  /// Calculate distance in meters between two coordinates using Haversine formula
  static double haversineDistanceMeters(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    final dLat = _degToRad(lat2 - lat1);
    final dLon = _degToRad(lon2 - lon1);

    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(_degToRad(lat1)) *
            math.cos(_degToRad(lat2)) *
            math.sin(dLon / 2) *
            math.sin(dLon / 2);

    final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
    return earthRadiusKm * c * 1000.0;
  }

  static double _degToRad(double deg) => deg * (math.pi / 180.0);

  /// Find the nearest zone to given GPS coordinates
  static ({ZoneModel zone, double distanceMeters})? findNearestZone(
    double userLat,
    double userLon,
    List<ZoneModel> zones,
  ) {
    if (zones.isEmpty) return null;

    ZoneModel? closestZone;
    double minDistance = double.infinity;

    for (final zone in zones) {
      final dist = haversineDistanceMeters(
        userLat,
        userLon,
        zone.coordinates.latitude,
        zone.coordinates.longitude,
      );

      if (dist < minDistance) {
        minDistance = dist;
        closestZone = zone;
      }
    }

    if (closestZone == null) return null;
    return (zone: closestZone, distanceMeters: minDistance);
  }

  /// Sort zones by distance to user
  static List<ZoneModel> sortZonesByProximity(
    double userLat,
    double userLon,
    List<ZoneModel> zones,
  ) {
    final list = List<ZoneModel>.from(zones);
    list.sort((a, b) {
      final distA = haversineDistanceMeters(
        userLat,
        userLon,
        a.coordinates.latitude,
        a.coordinates.longitude,
      );
      final distB = haversineDistanceMeters(
        userLat,
        userLon,
        b.coordinates.latitude,
        b.coordinates.longitude,
      );
      return distA.compareTo(distB);
    });
    return list;
  }
}
