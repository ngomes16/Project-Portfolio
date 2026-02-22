/**
 * File: src/components/budget/ContributionHistory.tsx
 * Purpose: Shows a list of contributions across trips for transparency and history.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';
import { useTrips } from '../../state/TripsStore';
import { Card } from '../Card';
import { formatCurrency } from '../../utils/format';

export function ContributionHistory() {
  const theme = useTheme();
  const { trips } = useTrips();
  const rows = trips.flatMap(t => (t.contributions || []).map(c => ({ ...c, tripId: t.id, tripName: t.name })));
  const sorted = rows.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  return (
    <Card style={{ marginTop: 16 }}>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Contribution History</Text>
      {sorted.length === 0 ? (
        <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>No contributions yet.</Text>
      ) : (
        sorted.map(c => (
          <View key={c.id} style={{ borderTopColor: theme.colors.border, borderTopWidth: 1, paddingTop: 8, marginTop: 8 }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{c.label} • {formatCurrency(c.amount)}</Text>
            <Text style={{ color: theme.colors.textSecondary }}>{c.tripName} • {c.date || '—'}</Text>
          </View>
        ))
      )}
    </Card>
  );
}


