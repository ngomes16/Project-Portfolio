/**
 * File: src/components/budget/OverviewSummary.tsx
 * Purpose: Top dashboard section showing total savings across all trips and overall progress.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';
import { useTrips } from '../../state/TripsStore';
import { Card } from '../Card';
import { ProgressBar } from '../ProgressBar';
import { formatCurrency } from '../../utils/format';

export function OverviewSummary() {
  const theme = useTheme();
  const { trips } = useTrips();

  const totalGoal = trips.reduce((s, t) => s + (t.goalBudget || 0), 0);
  const totalSaved = trips.reduce((s, t) => s + (t.contributions || []).reduce((ss, c) => ss + c.amount, 0), 0);
  const progress = totalGoal > 0 ? Math.min(1, totalSaved / totalGoal) : 0;

  return (
    <Card style={{ marginTop: 16 }}>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Total Savings Across All Trips</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>{formatCurrency(totalSaved)} saved • Goal {formatCurrency(totalGoal)}</Text>
      <View style={{ height: 8 }} />
      <ProgressBar progress={progress} />
    </Card>
  );
}


