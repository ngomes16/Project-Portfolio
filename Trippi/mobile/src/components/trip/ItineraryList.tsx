/**
 * File: src/components/trip/ItineraryList.tsx
 * Purpose: Redesigned itinerary list with compact inline actions and improved layout.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { BudgetItem, Trip } from '../../data/sample';
import { useTheme } from '../../theme/ThemeProvider';
import { Card } from '../Card';
import { InlineButton } from '../InlineButton';
import { categoryColor } from '../../utils/budget';

type Props = {
  items: BudgetItem[];
  onEdit: (item: BudgetItem) => void;
  onAddExpense: (item: BudgetItem) => void;
  onAddNew: () => void;
};

export function ItineraryList({ items, onEdit, onAddExpense, onAddNew }: Props) {
  const theme = useTheme();
  const projected = items.reduce((s, i) => s + (i.total || 0), 0);
  return (
    <Card style={{ marginTop: 16 }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <View>
          <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Current Itinerary</Text>
          <Text style={{ color: theme.colors.textSecondary, marginTop: 2 }}>Projected {`$${projected.toLocaleString()}`}</Text>
        </View>
        <InlineButton label="Add Item" iconName="add" variant="primary" onPress={onAddNew} />
      </View>
      {items.map(item => (
        <View key={item.id} style={{ marginTop: 10, borderTopWidth: 1, borderTopColor: theme.colors.border, paddingTop: 10 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <View style={{ flex: 1, paddingRight: 12 }}>
              <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{item.label}</Text>
              <Text style={{ color: theme.colors.textSecondary }}>
                {item.category} • {item.startAt ? new Date(item.startAt).toLocaleString() : 'No time set'}
              </Text>
              <Text style={{ color: theme.colors.textSecondary }}>
                Budget ${item.total.toLocaleString()} {item.perPerson ? `• $${item.perPerson}/person` : ''}
              </Text>
              <View style={{ width: 60, height: 4, backgroundColor: categoryColor(item.category), borderRadius: 2, marginTop: 6 }} />
            </View>
            <View style={{ flexDirection: 'column' }}>
              <InlineButton label="Edit" iconName="create" onPress={() => onEdit(item)} style={{ marginBottom: 6 }} />
              <InlineButton label="Expense" iconName="cash" onPress={() => onAddExpense(item)} />
            </View>
          </View>
        </View>
      ))}
    </Card>
  );
}


