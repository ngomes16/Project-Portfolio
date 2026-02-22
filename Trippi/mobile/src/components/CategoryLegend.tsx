/**
 * File: src/components/CategoryLegend.tsx
 * Purpose: Legend list for budget categories with color chips and amounts.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { categoryColor } from '../utils/budget';
import { useTheme } from '../theme/ThemeProvider';

type Item = { category: string; total: number };
type Props = { items: Item[] };

export function CategoryLegend({ items }: Props) {
  const theme = useTheme();
  return (
    <View>
      {items.map((ct) => (
        <View key={ct.category} style={{ flexDirection: 'row', alignItems: 'center', marginTop: 6 }}>
          <View style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: categoryColor(ct.category as any), marginRight: 8 }} />
          <Text style={{ color: theme.colors.textSecondary, flex: 1 }}>{ct.category}</Text>
          <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>${ct.total.toLocaleString()}</Text>
        </View>
      ))}
    </View>
  );
}


