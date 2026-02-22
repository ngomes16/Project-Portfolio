/**
 * File: app/trips.tsx
 * Purpose: Trips screen with search, filters, and rich trip list items; create flow navigates to wizard.
 */
import React from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';
import { useTheme } from '../src/theme/ThemeProvider';
import { Card } from '../src/components/Card';
import { Button } from '../src/components/Button';
import { useTrips } from '../src/state/TripsStore';
import { Link } from 'expo-router';
import { Screen } from '../src/components/Screen';
import { useRouter } from 'expo-router';
import { TextField } from '../src/components/TextField';
import { TripListItem } from '../src/components/TripListItem';
import { useUIState } from '../src/state/UIState';

export default function TripsScreen() {
  const theme = useTheme();
  const { trips } = useTrips();
  const router = useRouter();
  const { tripsTab, setTripsTabQuery, setTripsTabScroll } = useUIState();
  const listRef = React.useRef<any>(null);
  const [query, setQuery] = React.useState(tripsTab.query);
  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return trips;
    return trips.filter(t => t.name.toLowerCase().includes(q) || t.destination.toLowerCase().includes(q));
  }, [trips, query]);
  return (
    <Screen>
      <FlatList
        ref={listRef}
        contentContainerStyle={{ paddingBottom: 48 }}
        data={filtered}
        keyExtractor={(t) => t.id}
        onScroll={(e) => setTripsTabScroll(e.nativeEvent.contentOffset.y || 0)}
        onLayout={() => {
          requestAnimationFrame(() => {
            listRef.current?.scrollToOffset?.({ offset: tripsTab.scrollOffset, animated: false });
          });
        }}
        ListHeaderComponent={
          <View style={{ marginBottom: 12 }}>
            <Text style={[styles.title, { color: theme.colors.textPrimary }]}>Your Trips</Text>
            <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>
              Manage upcoming adventures and shared budgets.
            </Text>
            <View style={{ height: theme.spacing(2) }} />
            <TextField label="Search" placeholder="Search by name or destination" value={query} onChangeText={(t) => { setQuery(t); setTripsTabQuery(t); }} />
            <View style={{ height: theme.spacing(1) }} />
            <Button label="Create Trip" onPress={() => router.push('/trips/create')} />
          </View>
        }
        renderItem={({ item }) => (
          <TripListItem
            name={item.name}
            destination={item.destination}
            dateRange={item.dateRange}
            members={item.members.length}
            onOpen={() => router.push({ pathname: '/trip/[id]', params: { id: item.id } })}
          />
        )}
      />

    </Screen>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  title: { fontSize: 22, fontWeight: '700' },
  tripTitle: { fontSize: 16, fontWeight: '600', marginBottom: 2 },
});


