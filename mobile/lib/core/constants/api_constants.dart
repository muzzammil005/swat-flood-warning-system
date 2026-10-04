class ApiConstants {
  // Default connection URLs
  // For physical Android devices connected via USB, run:
  //   adb reverse tcp:8000 tcp:8000
  // and use defaultAdbReverseUrl (http://127.0.0.1:8000/api).
  static const String defaultAdbReverseUrl = "http://127.0.0.1:8000/api";
  static const String defaultLocalhostUrl = "http://localhost:8000/api";
  static const String defaultEmulatorUrl = "http://10.0.2.2:8000/api";
  static const String defaultDesktopUrl = "http://localhost:8000/api";
  static const String defaultPhoneLanUrl = "http://192.168.1.100:8000/api";
  
  // Default URL used when no custom URL has been saved
  static const String defaultBaseUrl = defaultAdbReverseUrl;

  // Storage key for custom base URL
  static const String baseUrlKey = "custom_base_url";

  // Endpoints
  static const String health = "/health";
  static const String zones = "/zones";
  static const String zonesSummary = "/zones/summary";
  static const String zonesNearest = "/zones/nearest";
  static const String alerts = "/alerts";
  static const String alertsBroadcast = "/alerts/broadcast";
  static const String reports = "/reports";
  static const String resourceCenters = "/resource-centers";
  static const String login = "/auth/login";
  static const String modelMetrics = "/model/metrics";
  static const String modelFeatureImportance = "/model/feature-importance";

  /// Normalizes user-input URL to ensure proper protocol (http://) and /api path.
  static String normalizeBaseUrl(String rawUrl) {
    var url = rawUrl.trim();
    if (url.isEmpty) return defaultBaseUrl;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'http://$url';
    }
    while (url.endsWith('/')) {
      url = url.substring(0, url.length - 1);
    }
    if (!url.endsWith('/api')) {
      url = '$url/api';
    }
    return url;
  }
}

