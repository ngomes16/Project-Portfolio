/**
 * File: src/components/budget/FlexBudgetCard.tsx
 * Purpose: Personal Flex Budget card with deposit/withdraw quick actions and transaction list.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';
import { Card } from '../Card';
import { Button } from '../Button';
import { useBudget } from '../../state/BudgetState';
import { formatCurrency } from '../../utils/format';

export function FlexBudgetCard() {
  const theme = useTheme();
  const { flexBudget, deposit, withdraw, transactions } = useBudget();

  return (
    <Card style={{ marginTop: 16 }}>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Personal Flex Budget</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>{formatCurrency(flexBudget)} available</Text>
      <View style={{ height: 8 }} />
      <View style={{ flexDirection: 'row', gap: 12 }}>
        <Button label="+ $50" onPress={() => deposit(50, 'Quick deposit')} style={{ flex: 1 }} />
        <Button label="- $20" onPress={() => withdraw(20, 'Quick withdraw')} style={{ flex: 1 }} />
      </View>
      <View style={{ height: 8 }} />
      <Text style={{ color: theme.colors.textSecondary, fontWeight: '600' }}>Recent</Text>
      {transactions.length === 0 ? (
        <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>No activity yet.</Text>
      ) : (
        transactions.slice(0, 4).map(t => (
          <View key={t.id} style={{ borderTopColor: theme.colors.border, borderTopWidth: 1, paddingTop: 8, marginTop: 8 }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{t.type === 'deposit' ? 'Deposit' : 'Withdraw'} • {formatCurrency(t.amount)}</Text>
            <Text style={{ color: theme.colors.textSecondary }}>{t.date.slice(0,10)}{t.note ? ` • ${t.note}` : ''}</Text>
          </View>
        ))
      )}
    </Card>
  );
}


