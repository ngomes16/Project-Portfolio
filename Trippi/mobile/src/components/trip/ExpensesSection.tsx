/**
 * File: src/components/trip/ExpensesSection.tsx
 * Purpose: Revamped expenses section with summary, list, and add expense entry point.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { Trip } from '../../data/sample';
import { useTheme } from '../../theme/ThemeProvider';
import { Card } from '../Card';
import { InlineButton } from '../InlineButton';

type Props = { trip: Trip; onAddExpense: () => void };

export function ExpensesSection({ trip, onAddExpense }: Props) {
  const theme = useTheme();
  const total = (trip.expenses || []).reduce((s, e) => s + e.amount, 0);
  const count = (trip.expenses || []).length;
  return (
    <Card style={{ marginTop: 16 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Expenses</Text>
        <InlineButton label="Add" iconName="add" variant="primary" onPress={onAddExpense} />
      </View>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>Total recorded: ${total.toFixed(2)} • {count} entries</Text>
      {count === 0 ? (
        <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>No expenses yet. Add from Itinerary or here.</Text>
      ) : (
        (trip.expenses || []).map(e => (
          <View key={e.id} style={{ borderTopWidth: 1, borderTopColor: theme.colors.border, paddingTop: 8, marginTop: 8 }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{e.label} • ${e.amount.toFixed(2)}</Text>
            <Text style={{ color: theme.colors.textSecondary }}>Paid by {trip.members.find(m => m.id === e.paidBy)?.name || e.paidBy} • Split with {(e.splitWith || []).map(id => trip.members.find(m => m.id === id)?.name || id).join(', ')}</Text>
          </View>
        ))
      )}
    </Card>
  );
}


