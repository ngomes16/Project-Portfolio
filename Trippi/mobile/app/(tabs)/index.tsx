/**
 * File: app/(tabs)/index.tsx
 * Purpose: Redesigned Home screen inspired by the provided reference. Presents:
 *   - Upcoming Trips horizontal list with per-trip circular progress
 *   - Savings Progress (total saved vs goal) ring chart
 *   - Prioritized Savings card for the soonest trip
 *   - Budget Summary (remaining)
 * All data is derived from `TripsStore` and Firestore where configured.
 */
import React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, Image } from 'react-native';
import { Screen } from '../../src/components/Screen';
import { useTheme } from '../../src/theme/ThemeProvider';
import { useTrips } from '../../src/state/TripsStore';
import { PieChartWithOverlay } from '../../src/components/PieChartWithOverlay';
import { Link } from 'expo-router';
// TripCard not used in the redesigned Home
import CircularProgress from '../../src/components/CircularProgress';
import { Card } from '../../src/components/Card';
import { formatCurrency } from '../../src/utils/format';
import { getDestinationImage } from '../../src/utils/images';
import TopRightBlur from '../../src/components/TopRightBlur';

export default function HomeTab() {
  const theme = useTheme();
  const { trips } = useTrips();
  const userName = 'Traveler';
  const perTrip = trips.map((t, i) => ({ id: t.id, name: t.name, saved: (t.contributions || []).reduce((s, c) => s + c.amount, 0), goal: t.goalBudget || 0, color: ['#7C5CFF','#22C55E','#F59E0B','#0EA5E9'][i % 4] }));
  const totalSaved = perTrip.reduce((s, t) => s + t.saved, 0);
  const totalGoal = perTrip.reduce((s, t) => s + t.goal, 0);
  const [tileWidth, setTileWidth] = React.useState<number>(0);

  const sortedTrips = React.useMemo(() => ([...trips].sort((a, b) => {
    const aTs = a.startDate ? Date.parse(a.startDate) : Number.MAX_SAFE_INTEGER;
    const bTs = b.startDate ? Date.parse(b.startDate) : Number.MAX_SAFE_INTEGER;
    return aTs - bTs;
  })), [trips]);

  // Compute prioritized trip (soonest with a goal)
  const prioritized = sortedTrips.find(t => (t.goalBudget ?? (t.itinerary || []).reduce((s, i) => s + (i.total || 0), 0)) > 0);
  const prioritizedSaved = prioritized ? (prioritized.contributions || []).reduce((s, c) => s + c.amount, 0) : 0;
  const prioritizedGoal = prioritized ? ((prioritized.goalBudget ?? (prioritized.itinerary || []).reduce((s, i) => s + (i.total || 0), 0)) || 0) : 0;
  const prioritizedPct = prioritizedGoal > 0 ? Math.min(1, prioritizedSaved / prioritizedGoal) : 0;

  return (
    <Screen scroll>
      {/* Decorative gradient anchored to the true top-right corner */}
      <TopRightBlur />
      {/* Brand/title aligned to top-left with proper safe-area insets */}
      <Text style={[styles.brand, { color: theme.colors.textPrimary }]}>Trippi</Text>

      {/* Upcoming Trips tiles */}
      <Text style={[styles.sectionTitle, { color: theme.colors.textPrimary, marginTop: 4 }]}>Upcoming Trips</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ marginHorizontal: -16 }}
        contentContainerStyle={{ paddingHorizontal: 16, paddingVertical: 12 }}
        snapToAlignment="start"
        decelerationRate="fast"
        snapToInterval={232}
      >
        {sortedTrips.map((t, idx) => {
            const plannedTotal = (t.itinerary || []).reduce((s, i) => s + (i.total || 0), 0);
            const goal = (t.goalBudget ?? plannedTotal) || 0;
            const saved = (t.contributions || []).reduce((s, c) => s + c.amount, 0);
            const pct = goal > 0 ? Math.min(1, saved / goal) : 0;
            return (
              <Link key={t.id} href={{ pathname: '/trip/[id]', params: { id: t.id } }} asChild>
                <Pressable style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}>
                  <Card style={{ width: 220, marginRight: 12, padding: 0, overflow: 'hidden' }}>
                    <Image source={{ uri: getDestinationImage(t.destination) }} style={{ height: 112, width: '100%' }} resizeMode="cover" />
                    <View style={{ padding: 12 }}>
                      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>{t.name}</Text>
                      <Text style={{ color: theme.colors.textSecondary, marginTop: 4, fontSize: 12 }}>{t.dateRange}</Text>
                      <View style={{ height: 8 }} />
                      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <CircularProgress progress={pct} />
                        <View style={{ width: 8 }} />
                        <Text style={{ color: theme.colors.textSecondary, fontSize: 12 }}>{Math.round(pct * 100)}%</Text>
                      </View>
                    </View>
                  </Card>
                </Pressable>
              </Link>
            );
          })}
      </ScrollView>

      {/* Savings Progress */}
      <Text style={[styles.sectionTitle, { color: theme.colors.textPrimary, marginTop: 8 }]}>Savings Progress</Text>
      <Card onLayout={(e) => setTileWidth(e.nativeEvent.layout.width)} style={{ alignItems: 'center' }}>
        <Text style={{ color: theme.colors.textSecondary }}>Total Saved</Text>
        <Text style={{ color: theme.colors.textPrimary, fontWeight: '800', fontSize: 20, marginTop: 2 }}>{formatCurrency(totalSaved)} of {formatCurrency(totalGoal)}</Text>
        <View style={{ height: 8 }} />
        <PieChartWithOverlay size={160} thickness={22} frameWidth={tileWidth} data={perTrip} />
      </Card>

      {/* Prioritized Savings */}
      <Text style={[styles.sectionTitle, { color: theme.colors.textPrimary, marginTop: 16 }]}>Prioritized Savings</Text>
      {prioritized ? (
        <Card style={{ flexDirection: 'row', alignItems: 'center' }}>
          <Image source={{ uri: getDestinationImage(prioritized.destination) }} style={{ width: 110, height: 80, borderRadius: 12 }} resizeMode="cover" />
          <View style={{ marginLeft: 12, flex: 1 }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>{prioritized.name}</Text>
            <Text style={{ color: theme.colors.textSecondary, fontSize: 12 }}>{prioritized.dateRange}</Text>
            <View style={{ height: 8 }} />
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <View style={{ flex: 1, height: 8, backgroundColor: theme.colors.border, borderRadius: 8, overflow: 'hidden' }}>
                <View style={{ width: `${Math.round(prioritizedPct * 100)}%`, height: '100%', backgroundColor: theme.colors.primary }} />
              </View>
              <Text style={{ color: theme.colors.textSecondary, marginLeft: 8 }}>{Math.round(prioritizedPct * 100)}%</Text>
            </View>
          </View>
        </Card>
      ) : (
        <Card><Text style={{ color: theme.colors.textSecondary }}>No goals yet. Create a trip goal to track savings.</Text></Card>
      )}

      {/* Budget Summary */}
      <Text style={[styles.sectionTitle, { color: theme.colors.textPrimary, marginTop: 16 }]}>Budget Summary</Text>
      <Card style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{ color: theme.colors.textSecondary }}>Remaining</Text>
        <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>{formatCurrency(Math.max(0, totalGoal - totalSaved))}</Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  brand: { fontSize: 28, fontWeight: '800' },
  sectionTitle: { fontSize: 16, fontWeight: '700' },
});



