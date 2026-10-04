import 'package:dio/dio.dart';
import 'package:get_it/get_it.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../dsa/river_graph.dart';
import '../network/api_client.dart';
import '../services/location_service.dart';
import '../services/notification_service.dart';
import '../services/storage_service.dart';

final sl = GetIt.instance;

void configureDependencies({SharedPreferences? mockPrefs}) {
  if (sl.isRegistered<RiverGraph>()) {
    // Already configured
    return;
  }

  // Core DSA
  sl.registerLazySingleton<RiverGraph>(() => RiverGraph());

  // Services
  if (!sl.isRegistered<StorageService>()) {
    sl.registerLazySingleton<StorageService>(() => StorageService(mockPrefs));
  }

  if (!sl.isRegistered<Dio>()) {
    sl.registerLazySingleton<Dio>(() => Dio());
  }

  if (!sl.isRegistered<LocationService>()) {
    sl.registerLazySingleton<LocationService>(() => LocationService());
  }

  if (!sl.isRegistered<NotificationService>()) {
    sl.registerLazySingleton<NotificationService>(
        () => NotificationService(sl<StorageService>()));
  }

  // Network client
  if (!sl.isRegistered<ApiClient>()) {
    sl.registerLazySingleton<ApiClient>(
        () => ApiClient(sl<Dio>(), sl<StorageService>()));
  }
}

Future<void> initDependencies() async {
  final prefs = await SharedPreferences.getInstance();
  configureDependencies(mockPrefs: prefs);
}
