import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/di/service_locator.dart';
import '../../../core/models/resource_center_model.dart';
import '../../../core/network/api_client.dart';

class ResourceCentersScreen extends StatefulWidget {
  const ResourceCentersScreen({super.key});

  @override
  State<ResourceCentersScreen> createState() => _ResourceCentersScreenState();
}

class _ResourceCentersScreenState extends State<ResourceCentersScreen> {
  final ApiClient _apiClient = sl<ApiClient>();

  List<ResourceCenterModel> _centers = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadCenters();
  }

  Future<void> _loadCenters() async {
    setState(() => _isLoading = true);
    try {
      final centers = await _apiClient.getResourceCenters();
      setState(() {
        _centers = centers;
        _isLoading = false;
      });
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: const Text(
          'Relief Centers & Helplines',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: AppColors.primaryLight),
            onPressed: _loadCenters,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primaryLight))
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Emergency Helplines Header Card
                _buildEmergencyHelplinesCard(),
                const SizedBox(height: 20),

                const Text(
                  'Active Emergency Depots & Inventory',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 12),

                ..._centers.map((center) => _buildCenterCard(center)),
              ],
            ),
    );
  }

  Widget _buildEmergencyHelplinesCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.surface,
            AppColors.surfaceLight.withValues(alpha: 0.3),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.primaryLight.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.phone_in_talk, color: AppColors.primaryLight, size: 22),
              SizedBox(width: 10),
              Text(
                'Swat Emergency Helplines',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          _buildHelplineRow('Rescue 1122 (Swat)', '1122', AppColors.riskDanger),
          const Divider(color: AppColors.border, height: 16),
          _buildHelplineRow('Swat Flood Control Room (DC)', '0946-9240400', AppColors.primaryLight),
          const Divider(color: AppColors.border, height: 16),
          _buildHelplineRow('PDMA KP Emergency Call Center', '1700', AppColors.accent),
          const Divider(color: AppColors.border, height: 16),
          _buildHelplineRow('Edhi Ambulance Service', '115', AppColors.riskMedium),
        ],
      ),
    );
  }

  Widget _buildHelplineRow(String service, String number, Color tagColor) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              service,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              number,
              style: TextStyle(
                color: tagColor,
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
          ],
        ),
        IconButton(
          icon: const Icon(Icons.call, color: AppColors.primaryLight),
          onPressed: () {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Dialing $service ($number)...'),
                backgroundColor: AppColors.surface,
              ),
            );
          },
        ),
      ],
    );
  }

  Widget _buildCenterCard(ResourceCenterModel center) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.accent.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.warehouse_rounded, color: AppColors.accent, size: 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  center.name,
                  style: const TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'Stock Availability:',
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: center.inventory.map((item) {
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.surfaceLight,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      item.itemName,
                      style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withValues(alpha: 0.3),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        '${item.quantity}',
                        style: const TextStyle(
                          color: AppColors.primaryLight,
                          fontWeight: FontWeight.bold,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
