/**
 * File: src/components/budget/GroupExpensesSummary.tsx
 * Purpose: Summaries for group/shared expenses: outstanding balances, covered contributions,
 *          gift history placeholders, and notifications needing confirmation.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';
import { useTrips } from '../../state/TripsStore';
import { Card } from '../Card';
import { computeBalances } from '../../utils/balances';

export function GroupExpensesSummary() {
  const theme = useTheme();
  const { trips } = useTrips();

  const outstanding = trips.flatMap(t => {
    const balances = computeBalances(t);
    return balances
      .filter(b => b.balance < 0)
      .map(b => ({ tripName: t.name, member: b.name, amount: Math.abs(b.balance) }));
  });

  return (
    <Card style={{ marginTop: 16 }}>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Group / Shared Expenses</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>Outstanding Balances</Text>
      {outstanding.length === 0 ? (
        <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>No outstanding balances.</Text>
      ) : (
        outstanding.slice(0, 5).map((o, idx) => (
          <View key={idx} style={{ borderTopColor: theme.colors.border, borderTopWidth: 1, paddingTop: 8, marginTop: 8 }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{o.member} owes {o.amount.toFixed(2)}</Text>
            <Text style={{ color: theme.colors.textSecondary }}>{o.tripName}</Text>
          </View>
        ))
      )}
      <View style={{ height: 8 }} />
      <Text style={{ color: theme.colors.textSecondary, fontWeight: '600' }}>Covered Contributions</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>Coming soon</Text>
      <View style={{ height: 8 }} />
      <Text style={{ color: theme.colors.textSecondary, fontWeight: '600' }}>Gift History</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>Coming soon</Text>
      <View style={{ height: 8 }} />
      <Text style={{ color: theme.colors.textSecondary, fontWeight: '600' }}>Expense Notifications</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>Coming soon</Text>
    </Card>
  );
}


