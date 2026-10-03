import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/main.dart';
import 'package:mobile/core/di/service_locator.dart';

void main() {
  testWidgets('App pumps without error', (WidgetTester tester) async {
    configureDependencies();
    await tester.pumpWidget(const FloodWatchApp());
    expect(find.text('Flood Watch'), findsOneWidget);
  });
}
