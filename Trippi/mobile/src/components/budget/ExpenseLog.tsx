/**
 * File: src/components/budget/ExpenseLog.tsx
 * Purpose: Chronological feed of budget-related actions (deposits, withdrawals, contributions, expenses)
 *          with simple filters and search.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';
import { Card } from '../Card';
import { TextField } from '../TextField';
import { useTrips } from '../../state/TripsStore';
import { useBudget } from '../../state/BudgetState';
import { Segmented } from '../Segmented';
import { formatCurrency } from '../../utils/format';

type Entry = { id: string; type: 'contribution' | 'expense' | 'flex'; label: string; amount: number; date: string; tripName?: string };

export function ExpenseLog() {
  const theme = useTheme();
  const { trips } = useTrips();
  const { transactions } = useBudget();

  const entries: Entry[] = [
    ...trips.flatMap(t => (t.contributions || []).map(c => ({ id: c.id, type: 'contribution' as const, label: c.label, amount: c.amount, date: c.date || '', tripName: t.name }))),
    ...trips.flatMap(t => (t.expenses || []).map(e => ({ id: e.id, type: 'expense' as const, label: e.label, amount: e.amount, date: e.createdAt, tripName: t.name }))),
    ...transactions.map(tx => ({ id: tx.id, type: 'flex' as const, label: tx.type === 'deposit' ? 'Flex deposit' : 'Flex withdraw', amount: tx.amount, date: tx.date })),
  ].sort((a, b) => (b.date || '').localeCompare(a.date || ''));

  const [query, setQuery] = React.useState('');
  const [filter, setFilter] = React.useState<'all' | 'contribution' | 'expense' | 'flex'>('all');

  const filtered = entries.filter(e => (filter === 'all' || e.type === filter) && (e.label.toLowerCase().includes(query.toLowerCase()) || (e.tripName || '').toLowerCase().includes(query.toLowerCase())));

  return (
    <Card style={{ marginTop: 16 }}>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Expense Log</Text>
      <View style={{ height: 8 }} />
      <Segmented options={[{ label: 'All', value: 'all' }, { label: 'Contrib', value: 'contribution' }, { label: 'Expenses', value: 'expense' }, { label: 'Flex', value: 'flex' }]} value={filter} onChange={(v) => setFilter(v as any)} />
      <View style={{ height: 8 }} />
      <TextField label="Search" placeholder="Search by label or trip" value={query} onChangeText={setQuery} />
      {filtered.length === 0 ? (
        <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>No entries.</Text>
      ) : (
        filtered.map(e => (
          <View key={`${e.type}-${e.id}`} style={{ borderTopColor: theme.colors.border, borderTopWidth: 1, paddingTop: 8, marginTop: 8 }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{e.label} • {formatCurrency(e.amount)}</Text>
            <Text style={{ color: theme.colors.textSecondary }}>{e.tripName || '—'} • {e.date.slice(0,10)}</Text>
          </View>
        ))
      )}
    </Card>
  );
}


