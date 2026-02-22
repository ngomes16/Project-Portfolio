/**
 * File: src/components/trip/MiniCalendar.tsx
 * Purpose: Compact, modern month calendar used on the Itinerary tab. Shows the
 *          month grid with chevron navigation, highlights the trip date range,
 *          and allows selecting a single day to filter the timeline. Passing a
 *          `null` selectedDate represents "All dates" in the trip.
 */
import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../theme/ThemeProvider';
import { Card } from '../Card';

type Props = {
  startDate?: string;
  endDate?: string;
  selectedDate: string | null;
  onChangeSelectedDate: (isoDate: string | null) => void;
};

function startOfDay(date: Date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function inRange(d: Date, start?: Date, end?: Date) {
  if (!start || !end) return true;
  const t = startOfDay(d).getTime();
  return t >= startOfDay(start).getTime() && t <= startOfDay(end).getTime();
}

function toJSDate(input?: string | Date | any): Date | undefined {
  if (!input) return undefined;
  if (input instanceof Date) return input;
  if (typeof input === 'string' || typeof input === 'number') {
    const d = new Date(input);
    return isNaN(d.getTime()) ? undefined : d;
  }
  if (typeof input === 'object' && typeof input.toDate === 'function') {
    const d = input.toDate();
    return d instanceof Date && !isNaN(d.getTime()) ? d : undefined;
  }
  return undefined;
}

export function MiniCalendar({ startDate, endDate, selectedDate, onChangeSelectedDate }: Props) {
  const theme = useTheme();
  const tripStart = toJSDate(startDate);
  const tripEnd = toJSDate(endDate);
  const initialMonthBase = selectedDate ? new Date(selectedDate) : (tripStart || tripEnd || new Date());
  const initialMonth = isNaN(initialMonthBase.getTime()) ? new Date() : initialMonthBase;
  const [visibleMonth, setVisibleMonth] = React.useState<Date>(new Date(initialMonth.getFullYear(), initialMonth.getMonth(), 1));

  React.useEffect(() => {
    if (selectedDate) {
      const d = new Date(selectedDate);
      setVisibleMonth(new Date(d.getFullYear(), d.getMonth(), 1));
    }
  }, [selectedDate]);

  const monthStart = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1);
  const monthEnd = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() + 1, 0);
  const startWeekday = monthStart.getDay(); // 0..6 Sun..Sat
  const daysInMonth = monthEnd.getDate();

  const days: Array<Date | null> = [];
  for (let i = 0; i < startWeekday; i++) days.push(null);
  for (let d = 1; d <= daysInMonth; d++) days.push(new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), d));
  // Pad trailing placeholders so the last row always has 7 columns for alignment
  const endWeekday = monthEnd.getDay();
  const trailing = 6 - endWeekday;
  for (let i = 0; i < trailing; i++) days.push(null);
  const rows: (Array<Date | null>)[] = [];
  for (let i = 0; i < days.length; i += 7) rows.push(days.slice(i, i + 7));

  const title = monthStart.toLocaleString(undefined, { month: 'long', year: 'numeric' });

  const handlePrev = () => setVisibleMonth(new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() - 1, 1));
  const handleNext = () => setVisibleMonth(new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() + 1, 1));

  const selected = selectedDate ? new Date(selectedDate) : null;

  return (
    <Card style={{ marginTop: 8 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Pressable onPress={handlePrev} hitSlop={10} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}>
          <Ionicons name="chevron-back" size={20} color={theme.colors.textPrimary} />
        </Pressable>
        <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>{title}</Text>
        <Pressable onPress={handleNext} hitSlop={10} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}>
          <Ionicons name="chevron-forward" size={20} color={theme.colors.textPrimary} />
        </Pressable>
      </View>

      {/* Weekday headers */}
      <View style={{ flexDirection: 'row', marginTop: 8 }}>
        {['S','M','T','W','T','F','S'].map((d, idx) => (
          <View key={`dow-${idx}`} style={{ flex: 1, alignItems: 'center' }}>
            <Text style={{ color: theme.colors.textSecondary, fontSize: 12 }}>{d}</Text>
          </View>
        ))}
      </View>

      {/* Grid */}
      <View style={{ marginTop: 4 }}>
        {rows.map((row, idx) => (
          <View key={`row-${idx}`} style={{ flexDirection: 'row', marginTop: idx === 0 ? 0 : 6 }}>
            {row.map((d, i) => {
              if (!d) return <View key={`empty-${idx}-${i}`} style={{ flex: 1 }} />;
              const inTrip = inRange(d, tripStart, tripEnd);
              const isSelected = selected ? isSameDay(d, selected) : false;
              const isToday = isSameDay(d, new Date());
              const baseColor = inTrip ? theme.colors.textPrimary : theme.colors.textSecondary;
              const bgColor = isSelected ? theme.colors.primary : (inTrip ? '#EEEAFD' : 'transparent');
              const textColor = isSelected ? '#FFFFFF' : baseColor;
              return (
                <Pressable
                  key={`cell-${idx}-${i}-${d.getDate()}`}
                  onPress={() => inTrip ? onChangeSelectedDate(d.toISOString()) : undefined}
                  style={({ pressed }) => ({ flex: 1, alignItems: 'center', opacity: pressed ? 0.75 : 1 })}
                  hitSlop={6}
                >
                  <View style={{ width: 32, height: 32, borderRadius: 8, alignItems: 'center', justifyContent: 'center', backgroundColor: bgColor }}>
                    <Text style={{ color: textColor, fontWeight: isToday ? '800' : '600', fontSize: 13 }}>{d.getDate()}</Text>
                  </View>
                </Pressable>
              );
            })}
          </View>
        ))}
      </View>

      {/* All dates toggle */}
      {(tripStart || tripEnd) && (
        <View style={{ marginTop: 10, alignItems: 'center' }}>
          <Pressable
            onPress={() => onChangeSelectedDate(null)}
            style={({ pressed }) => ({ paddingHorizontal: 10, height: 28, borderRadius: 8, borderWidth: 1, borderColor: theme.colors.border, alignItems: 'center', justifyContent: 'center', opacity: pressed ? 0.8 : 1 })}
          >
            <Text style={{ color: theme.colors.textSecondary, fontWeight: '600', fontSize: 12 }}>Show Entire Trip</Text>
          </Pressable>
        </View>
      )}
    </Card>
  );
}


