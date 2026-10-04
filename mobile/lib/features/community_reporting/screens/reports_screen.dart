import 'package:flutter/material.dart';
import 'package:timeago/timeago.dart' as timeago;
import '../../../core/constants/app_colors.dart';
import '../../../core/di/service_locator.dart';
import '../../../core/models/report_model.dart';
import '../../../core/models/zone_model.dart';
import '../../../core/network/api_client.dart';
import '../../../core/services/location_service.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen>
    with SingleTickerProviderStateMixin {
  final ApiClient _apiClient = sl<ApiClient>();
  final LocationService _locationService = sl<LocationService>();

  late TabController _tabController;
  List<CommunityReportModel> _reports = [];
  bool _isLoading = true;

  // Form state
  final _formKey = GlobalKey<FormState>();
  final _descController = TextEditingController();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  String _selectedType = 'Flash Flood';
  String _selectedZone = 'zone-mingora';
  CoordinatesModel? _detectedLocation;
  bool _isSubmitting = false;

  final List<String> _reportTypes = [
    'Flash Flood',
    'River Overflow',
    'Landslide',
    'Road Blocked',
    'Bridge Damage',
    'Drainage Clogged',
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadReports();
    _autoDetectGps();
  }

  Future<void> _loadReports() async {
    setState(() => _isLoading = true);
    try {
      final reports = await _apiClient.getCommunityReports();
      setState(() {
        _reports = reports;
        _isLoading = false;
      });
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  void _autoDetectGps() async {
    final coords = await _locationService.getCurrentLocation();
    if (mounted) {
      setState(() => _detectedLocation = coords);
    }
  }

  Future<void> _submitReport() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);

    final payload = {
      'report_type': _selectedType,
      'description': _descController.text.trim(),
      'reporter_name': _nameController.text.trim().isEmpty
          ? 'Anonymous Citizen'
          : _nameController.text.trim(),
      'reporter_phone': _phoneController.text.trim(),
      'zone_id': _selectedZone,
      'latitude': _detectedLocation?.latitude ?? 34.774,
      'longitude': _detectedLocation?.longitude ?? 72.361,
    };

    final ok = await _apiClient.submitCommunityReport(payload);

    setState(() => _isSubmitting = false);

    if (mounted) {
      if (ok) {
        _descController.clear();
        _nameController.clear();
        _phoneController.clear();

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
                'Report submitted successfully. Local authorities notified.'),
            backgroundColor: Colors.green,
          ),
        );

        _loadReports();
        _tabController.animateTo(1); // Switch to community feed
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to submit report. Please check server.'),
            backgroundColor: AppColors.riskDanger,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: const Text(
          'Community Flood Reports',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: AppColors.textPrimary,
          ),
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppColors.primaryLight,
          labelColor: AppColors.primaryLight,
          unselectedLabelColor: AppColors.textSecondary,
          tabs: const [
            Tab(icon: Icon(Icons.add_location_alt_outlined), text: 'Submit Report'),
            Tab(icon: Icon(Icons.feed_outlined), text: 'Community Feed'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildSubmitFormTab(),
          _buildCommunityFeedTab(),
        ],
      ),
    );
  }

  Widget _buildSubmitFormTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.border),
          ),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Report Flood Incident',
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Your eyewitness field report helps Rescue 1122 and early-warning teams verify flood inundation.',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 16),

                // Report Type Dropdown
                DropdownButtonFormField<String>(
                  initialValue: _selectedType,
                  dropdownColor: AppColors.surface,
                  style: const TextStyle(color: AppColors.textPrimary),
                  decoration: InputDecoration(
                    labelText: 'Incident Type',
                    labelStyle: const TextStyle(color: AppColors.textSecondary),
                    filled: true,
                    fillColor: AppColors.surfaceLight,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide.none,
                    ),
                  ),
                  items: _reportTypes
                      .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                      .toList(),
                  onChanged: (v) => setState(() => _selectedType = v!),
                ),
                const SizedBox(height: 14),

                // Zone Selector
                DropdownButtonFormField<String>(
                  initialValue: _selectedZone,
                  dropdownColor: AppColors.surface,
                  style: const TextStyle(color: AppColors.textPrimary),
                  decoration: InputDecoration(
                    labelText: 'River Basin Zone',
                    labelStyle: const TextStyle(color: AppColors.textSecondary),
                    filled: true,
                    fillColor: AppColors.surfaceLight,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide.none,
                    ),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'zone-kalam', child: Text('Kalam Bazaar (Upper Catchment)')),
                    DropdownMenuItem(value: 'zone-bahrain', child: Text('Bahrain (Mid Basin)')),
                    DropdownMenuItem(value: 'zone-madyan', child: Text('Madyan (Tributary Confluence)')),
                    DropdownMenuItem(value: 'zone-mingora', child: Text('Mingora City (Urban Plain)')),
                  ],
                  onChanged: (v) => setState(() => _selectedZone = v!),
                ),
                const SizedBox(height: 14),

                // Description
                TextFormField(
                  controller: _descController,
                  maxLines: 3,
                  style: const TextStyle(color: AppColors.textPrimary),
                  decoration: InputDecoration(
                    labelText: 'Incident Description',
                    hintText: 'Describe water height, road blockage, or overflow...',
                    hintStyle: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                    labelStyle: const TextStyle(color: AppColors.textSecondary),
                    filled: true,
                    fillColor: AppColors.surfaceLight,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide.none,
                    ),
                  ),
                  validator: (v) =>
                      v == null || v.trim().isEmpty ? 'Please enter a description' : null,
                ),
                const SizedBox(height: 14),

                // Reporter Name & Phone
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _nameController,
                        style: const TextStyle(color: AppColors.textPrimary),
                        decoration: InputDecoration(
                          labelText: 'Your Name (Optional)',
                          labelStyle: const TextStyle(color: AppColors.textSecondary),
                          filled: true,
                          fillColor: AppColors.surfaceLight,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: BorderSide.none,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextFormField(
                        controller: _phoneController,
                        keyboardType: TextInputType.phone,
                        style: const TextStyle(color: AppColors.textPrimary),
                        decoration: InputDecoration(
                          labelText: 'Phone (Optional)',
                          labelStyle: const TextStyle(color: AppColors.textSecondary),
                          filled: true,
                          fillColor: AppColors.surfaceLight,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: BorderSide.none,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // GPS Location auto-detect pill
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceLight.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.my_location, color: AppColors.primaryLight, size: 16),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _detectedLocation != null
                              ? 'GPS Tagged: ${_detectedLocation!.latitude.toStringAsFixed(4)}, ${_detectedLocation!.longitude.toStringAsFixed(4)}'
                              : 'Acquiring GPS location...',
                          style: const TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 11,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Submit Button
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    onPressed: _isSubmitting ? null : _submitReport,
                    child: _isSubmitting
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Text(
                            'Submit Emergency Report',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCommunityFeedTab() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppColors.primaryLight));
    }

    if (_reports.isEmpty) {
      return const Center(
        child: Text(
          'No verified community reports yet.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadReports,
      color: AppColors.primaryLight,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _reports.length,
        itemBuilder: (context, index) {
          final rep = _reports[index];
          final isApproved = rep.status.toLowerCase() == 'approved';

          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: isApproved
                    ? AppColors.riskLow.withValues(alpha: 0.5)
                    : AppColors.border,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        rep.reportType,
                        style: const TextStyle(
                          color: AppColors.primaryLight,
                          fontWeight: FontWeight.bold,
                          fontSize: 11,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: isApproved
                            ? AppColors.riskLow.withValues(alpha: 0.2)
                            : AppColors.riskMedium.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        rep.status,
                        style: TextStyle(
                          color: isApproved
                              ? AppColors.riskLow
                              : AppColors.riskMedium,
                          fontWeight: FontWeight.bold,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  rep.description,
                  style: const TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 14,
                    height: 1.3,
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Reported by: ${rep.reporterName ?? 'Citizen'}',
                      style: const TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 11,
                      ),
                    ),
                    Text(
                      timeago.format(rep.submittedAt),
                      style: const TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
