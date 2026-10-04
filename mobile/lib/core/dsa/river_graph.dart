import '../models/zone_model.dart';

/// Production DSA implementation:
/// Directed Acyclic Graph (DAG) modeling the Swat River Basin.
/// Flow direction: Kalam (Headwater) -> Bahrain -> Madyan -> Mingora
class RiverGraph {
  final Map<String, ZoneModel> _zonesById = {};
  final Map<String, List<String>> _downstreamAdj = {};
  final Map<String, String?> _upstreamParent = {};

  void buildFromZones(List<ZoneModel> zones) {
    _zonesById.clear();
    _downstreamAdj.clear();
    _upstreamParent.clear();

    for (final zone in zones) {
      _zonesById[zone.id] = zone;
      _downstreamAdj[zone.id] = [];
      _upstreamParent[zone.id] = zone.upstreamZoneId;
    }

    // Populate downstream adjacency
    for (final zone in zones) {
      if (zone.upstreamZoneId != null &&
          _downstreamAdj.containsKey(zone.upstreamZoneId)) {
        _downstreamAdj[zone.upstreamZoneId]!.add(zone.id);
      }
    }
  }

  /// Get list of all upstream ancestors from this zone to the headwaters
  List<String> getUpstreamChain(String zoneId) {
    final chain = <String>[];
    String? current = _upstreamParent[zoneId];
    while (current != null && _zonesById.containsKey(current)) {
      chain.add(current);
      current = _upstreamParent[current];
    }
    return chain;
  }

  /// Get all downstream successors impacted if this zone surges
  List<String> getDownstreamSuccessors(String zoneId) {
    final result = <String>[];
    final queue = <String>[zoneId];
    final visited = <String>{zoneId};

    while (queue.isNotEmpty) {
      final curr = queue.removeAt(0);
      final neighbors = _downstreamAdj[curr] ?? [];
      for (final next in neighbors) {
        if (!visited.contains(next)) {
          visited.add(next);
          result.add(next);
          queue.add(next);
        }
      }
    }
    return result;
  }

  /// Detects if an upstream flood wave is cascading downstream
  /// Returns a summary message for any downstream risk
  String? checkCascadingSurge(String zoneId) {
    final upstreamIds = getUpstreamChain(zoneId);
    for (final upId in upstreamIds) {
      final upZone = _zonesById[upId];
      if (upZone != null) {
        final tier = upZone.riskTier.toUpperCase();
        if (tier == 'DANGER' || tier == 'HIGH') {
          return 'Surge Alert: Upstream ${upZone.name} is in $tier state. Water is advancing downstream towards ${_zonesById[zoneId]?.name ?? zoneId}.';
        }
      }
    }
    return null;
  }
}
