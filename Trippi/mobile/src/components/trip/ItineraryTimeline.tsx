/**
 * File: src/components/trip/ItineraryTimeline.tsx
 * Purpose: Timeline of itinerary items grouped by day with times for quick scanning.
 * Update: Accepts optional `filterDate` to show only one day's items when a date
 *         is selected from the mini calendar. Adds a more modern row style.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { BudgetItem } from '../../data/sample';
import { useTheme } from '../../theme/ThemeProvider';

type Props = { items: BudgetItem[]; filterDate?: string | null };

function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

export function ItineraryTimeline({ items, filterDate }: Props) {
  const theme = useTheme();
  const withDates = items.filter(i => i.startAt);
  const sorted = [...withDates].sort((a, b) => Date.parse(a.startAt!) - Date.parse(b.startAt!));
  const groups: Record<string, BudgetItem[]> = {};
  for (const it of sorted) {
    const d = new Date(it.startAt as string);
    if (filterDate) {
      const f = new Date(filterDate);
      if (!isSameDay(d, f)) continue;
    }
    const dateKey = d.toDateString();
    groups[dateKey] = groups[dateKey] || [];
    groups[dateKey].push(it);
  }

  const dayKeys = Object.keys(groups);
  if (dayKeys.length === 0) {
    return <Text style={{ color: theme.colors.textSecondary }}>No dated items yet.</Text>;
  }

  return (
    <View>
      {dayKeys.map(day => (
        <View key={day} style={{ marginTop: 12 }}>
          <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>{day}</Text>
          {groups[day].map(item => {
            const time = new Date(item.startAt as string).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            return (
              <View key={item.id} style={{ flexDirection: 'row', alignItems: 'flex-start', marginTop: 10 }}>
                <View style={{ width: 56, alignItems: 'flex-start' }}>
                  <Text style={{ color: theme.colors.textSecondary }}>{time}</Text>
                </View>
                <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: theme.colors.primary, marginRight: 10, marginTop: 8 }} />
                <View style={{ flex: 1, backgroundColor: theme.colors.surface, borderWidth: 1, borderColor: theme.colors.border, borderRadius: 12, padding: 10, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, shadowOffset: { width: 0, height: 3 }, elevation: 2 }}>
                  <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>{item.label}</Text>
                  <Text style={{ color: theme.colors.textSecondary, marginTop: 2 }}>{item.category} • ${item.total.toLocaleString()}</Text>
                </View>
              </View>
            );
          })}
        </View>
      ))}
    </View>
  );
}


