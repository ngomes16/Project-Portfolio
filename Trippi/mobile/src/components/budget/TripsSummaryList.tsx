/**
 * File: src/components/budget/TripsSummaryList.tsx
 * Purpose: Shows a list of active trips with quick stats (goal vs. saved) and progress bars.
 */
import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';
import { useTrips } from '../../state/TripsStore';
import { Card } from '../Card';
import { ProgressBar } from '../ProgressBar';
import { formatCurrency } from '../../utils/format';
import { useRouter } from 'expo-router';

export function TripsSummaryList() {
  const theme = useTheme();
  const { trips } = useTrips();
  const router = useRouter();
  return (
    <Card style={{ marginTop: 16 }}>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Active Trip Goals Summary</Text>
      {trips.map(t => {
        const goal = t.goalBudget || 0;
        const saved = (t.contributions || []).reduce((s, c) => s + c.amount, 0);
        const progress = goal > 0 ? Math.min(1, saved / goal) : 0;
        return (
          <Pressable key={t.id} onPress={() => router.push(`/trip/${t.id}`)} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}>
            <View style={{ borderTopColor: theme.colors.border, borderTopWidth: 1, paddingTop: 8, marginTop: 8 }}>
              <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{t.name}</Text>
              <Text style={{ color: theme.colors.textSecondary }}>{formatCurrency(saved)} saved • Goal {formatCurrency(goal)}</Text>
              <View style={{ height: 8 }} />
              <ProgressBar progress={progress} />
            </View>
          </Pressable>
        );
      })}
    </Card>
  );
}


