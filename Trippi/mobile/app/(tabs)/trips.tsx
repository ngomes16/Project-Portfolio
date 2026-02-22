/**
 * File: app/(tabs)/trips.tsx
 * Purpose: Trips tab with trip cards and a floating + button that opens the Create Trip flow.
 * Update: Wired FAB to navigate directly to /trips/create. Removed Budget tab references. Sorted by upcoming start date.
 */
import React from 'react';
import { View, Text, StyleSheet, FlatList, Pressable } from 'react-native';
import { Screen } from '../../src/components/Screen';
import { useTheme } from '../../src/theme/ThemeProvider';
import { useTrips } from '../../src/state/TripsStore';
import { Link, useRouter } from 'expo-router';
import { TripCard } from '../../src/components/TripCard';
import { FAB } from '../../src/components/FAB';

export default function TripsTab() {
  const router = useRouter();
  const theme = useTheme();
  const { trips } = useTrips();
  const sorted = React.useMemo(() => {
    const toMillis = (value: any): number => {
      if (!value) return Number.MAX_SAFE_INTEGER;
      if (typeof value === 'string') {
        const ts = Date.parse(value);
        return Number.isFinite(ts) ? ts : Number.MAX_SAFE_INTEGER;
      }
      if (typeof value === 'object' && typeof value.toDate === 'function') {
        try { return value.toDate().getTime(); } catch { return Number.MAX_SAFE_INTEGER; }
      }
      return Number.MAX_SAFE_INTEGER;
    };
    return [...trips].sort((a, b) => toMillis(a.startDate) - toMillis(b.startDate));
  }, [trips]);
  return (
    <Screen>
      <Text style={[styles.title, { color: theme.colors.textPrimary }]}>Trips</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>Your upcoming adventures</Text>
      <FlatList
        contentContainerStyle={{ paddingTop: 12, paddingBottom: 90 }}
        data={sorted}
        keyExtractor={(t) => t.id}
        renderItem={({ item }) => (
          <Link href={{ pathname: '/trip/[id]', params: { id: item.id } }} asChild>
            <Pressable>
              <TripCard
                name={item.name}
                destination={item.destination}
                dateRange={item.dateRange}
                memberNames={(item.members || []).map(m => m.name)}
              />
            </Pressable>
          </Link>
        )}
      />
      <FAB onPress={() => router.push('/trips/create')} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '700' },
});


