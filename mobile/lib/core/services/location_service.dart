import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:geolocator/geolocator.dart';
import '../models/zone_model.dart';

class LocationService {
  // Default coordinates fallback (Center of Swat Valley - Mingora)
  static const CoordinatesModel defaultSwatCenter = CoordinatesModel(
    latitude: 34.774,
    longitude: 72.361,
  );

  Future<CoordinatesModel> getCurrentLocation() async {
    try {
      if (!kIsWeb && Platform.environment.containsKey('FLUTTER_TEST')) {
        return defaultSwatCenter;
      }
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        return defaultSwatCenter;
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          return defaultSwatCenter;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        return defaultSwatCenter;
      }

      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 5),
        ),
      );

      return CoordinatesModel(
        latitude: position.latitude,
        longitude: position.longitude,
      );
    } catch (_) {
      return defaultSwatCenter;
    }
  }
}
