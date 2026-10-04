import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_ringtone_player/flutter_ringtone_player.dart';
import 'package:vibration/vibration.dart';
import 'storage_service.dart';

class NotificationService {
  final StorageService _storageService;

  NotificationService(this._storageService);

  Future<void> triggerEmergencySiren() async {
    try {
      if (!kIsWeb && Platform.environment.containsKey('FLUTTER_TEST')) {
        return;
      }
    } catch (_) {}
    try {
      if (_storageService.getSoundEnabled()) {
        FlutterRingtonePlayer().playAlarm(
          looping: false,
          asAlarm: true,
          volume: 1.0,
        );
      }
    } catch (_) {
      // Graceful fallback on desktop/web/simulators
    }

    try {
      if (_storageService.getVibrationEnabled()) {
        final hasVibe = await Vibration.hasVibrator();
        if (hasVibe) {
          Vibration.vibrate(pattern: [500, 1000, 500, 1000]);
        }
      }
    } catch (_) {
      // Graceful fallback
    }
  }

  void stopEmergencySiren() {
    try {
      FlutterRingtonePlayer().stop();
    } catch (_) {}
  }
}
