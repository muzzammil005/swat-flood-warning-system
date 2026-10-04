class InventoryItemModel {
  final String id;
  final String itemName;
  final int quantity;

  const InventoryItemModel({
    required this.id,
    required this.itemName,
    required this.quantity,
  });

  factory InventoryItemModel.fromJson(Map<String, dynamic> json) {
    return InventoryItemModel(
      id: json['id'] as String? ?? '',
      itemName: json['item_name'] as String? ?? 'Item',
      quantity: (json['quantity'] as num?)?.toInt() ?? 0,
    );
  }
}

class ResourceCenterModel {
  final String id;
  final String name;
  final String locationZone;
  final List<InventoryItemModel> inventory;

  const ResourceCenterModel({
    required this.id,
    required this.name,
    required this.locationZone,
    required this.inventory,
  });

  factory ResourceCenterModel.fromJson(Map<String, dynamic> json) {
    return ResourceCenterModel(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? 'Emergency Depot',
      locationZone: json['location_zone'] as String? ?? '',
      inventory: (json['inventory'] as List?)
              ?.map((item) =>
                  InventoryItemModel.fromJson(item as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}
