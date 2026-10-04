import 'package:flutter/material.dart';

class AppColors {
  // Theme foundation
  static const Color background = Color(0xFF0F172A); // Slate 900
  static const Color surface = Color(0xFF1E293B);    // Slate 800
  static const Color surfaceLight = Color(0xFF334155); // Slate 700
  static const Color card = Color(0xFF1E293B);
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);
  static const Color border = Color(0xFF334155);
  
  // Brand & River Accents
  static const Color primary = Color(0xFF0284C7);     // Sky 600
  static const Color primaryLight = Color(0xFF38BDF8); // Sky 400
  static const Color accent = Color(0xFF06B6D4);      // Cyan 500
  
  // River risk tiers (Synchronized with Backend & Web Portal)
  static const Color riskSafe = Color(0xFF3B82F6);    // Blue 500
  static const Color riskLow = Color(0xFF10B981);     // Emerald 500
  static const Color riskMedium = Color(0xFFF59E0B);  // Amber 500
  static const Color riskHigh = Color(0xFFF97316);    // Orange 500
  static const Color riskDanger = Color(0xFFEF4444);  // Red 500
  
  static Color getRiskColor(String tier) {
    switch (tier.toUpperCase()) {
      case 'DANGER':
        return riskDanger;
      case 'HIGH':
        return riskHigh;
      case 'MEDIUM':
        return riskMedium;
      case 'LOW':
        return riskLow;
      case 'SAFE':
      default:
        return riskSafe;
    }
  }

  static Color getRiskColorWithAlpha(String tier, double opacity) {
    return getRiskColor(tier).withValues(alpha: opacity);
  }
}
