import 'package:shared_preferences/shared_preferences.dart';
import '../constants/api_constants.dart';

class StorageService {
  final SharedPreferences? _prefs;
  final Map<String, dynamic> _inMemory = {};

  StorageService([this._prefs]);

  static Future<StorageService> init() async {
    final prefs = await SharedPreferences.getInstance();
    return StorageService(prefs);
  }

  String getBaseUrl() {
    final raw = _prefs?.getString(ApiConstants.baseUrlKey) ??
        _inMemory[ApiConstants.baseUrlKey] as String?;
    if (raw != null && raw.trim().isNotEmpty) {
      return ApiConstants.normalizeBaseUrl(raw);
    }
    return ApiConstants.defaultBaseUrl;
  }

  Future<bool> setBaseUrl(String url) async {
    final normalized = ApiConstants.normalizeBaseUrl(url);
    _inMemory[ApiConstants.baseUrlKey] = normalized;
    if (_prefs != null) {
      return _prefs.setString(ApiConstants.baseUrlKey, normalized);
    }
    return true;
  }

  bool getSoundEnabled() {
    return _prefs?.getBool('sound_enabled') ??
        _inMemory['sound_enabled'] as bool? ??
        true;
  }

  Future<bool> setSoundEnabled(bool enabled) async {
    _inMemory['sound_enabled'] = enabled;
    if (_prefs != null) {
      return _prefs.setBool('sound_enabled', enabled);
    }
    return true;
  }

  bool getVibrationEnabled() {
    return _prefs?.getBool('vibration_enabled') ??
        _inMemory['vibration_enabled'] as bool? ??
        true;
  }

  Future<bool> setVibrationEnabled(bool enabled) async {
    _inMemory['vibration_enabled'] = enabled;
    if (_prefs != null) {
      return _prefs.setBool('vibration_enabled', enabled);
    }
    return true;
  }

  String? getCachedZones() {
    return _prefs?.getString('cached_zones_json') ??
        _inMemory['cached_zones_json'] as String?;
  }

  Future<bool> setCachedZones(String jsonStr) async {
    _inMemory['cached_zones_json'] = jsonStr;
    if (_prefs != null) {
      return _prefs.setString('cached_zones_json', jsonStr);
    }
    return true;
  }
}
