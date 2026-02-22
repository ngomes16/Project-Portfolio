/**
 * File: src/components/trip/TripProgressRow.tsx
 * Purpose: Per-trip goal progress row with totals and a progress bar.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { Trip } from '../../data/sample';
import { useTheme } from '../../theme/ThemeProvider';
import { ProgressBar } from '../ProgressBar';
import { formatCurrency } from '../../utils/format';

type Props = { trip: Trip };

export function TripProgressRow({ trip }: Props) {
  const theme = useTheme();
  const total = trip.itinerary.reduce((s, i) => s + i.total, 0);
  const goal = (trip.goalBudget ?? total) || 1;
  const pct = Math.min(1, total / goal);
  return (
    <View style={{ borderTopColor: theme.colors.border, borderTopWidth: 1, paddingTop: 8, marginTop: 8 }}>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{trip.name}</Text>
      <Text style={{ color: theme.colors.textSecondary }}>{formatCurrency(total)} of {formatCurrency(goal)} planned</Text>
      <View style={{ height: 8 }} />
      <ProgressBar progress={pct} />
    </View>
  );
}


