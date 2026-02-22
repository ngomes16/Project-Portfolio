/**
 * File: src/components/trip/SplitBalances.tsx
 * Purpose: Shows per-member balances from shared expenses and contributions within a trip.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { Trip } from '../../data/sample';
import { useTheme } from '../../theme/ThemeProvider';
import { Card } from '../Card';
import { computeBalances } from '../../utils/balances';

type Props = { trip: Trip };

export function SplitBalances({ trip }: Props) {
  const theme = useTheme();
  const balances = computeBalances(trip);
  return (
    <Card style={{ marginTop: 16 }}>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Split Balances</Text>
      {balances.length === 0 ? (
        <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>No balances yet. Add expenses to compute splits.</Text>
      ) : (
        balances.map(b => (
          <View key={b.memberId} style={{ borderTopWidth: 1, borderTopColor: theme.colors.border, paddingTop: 8, marginTop: 8 }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{b.name}</Text>
            <Text style={{ color: b.balance >= 0 ? '#22C55E' : '#EF4444' }}>
              {b.balance >= 0 ? `Should receive $${b.balance.toFixed(2)}` : `Owes $${Math.abs(b.balance).toFixed(2)}`}
            </Text>
          </View>
        ))
      )}
    </Card>
  );
}


