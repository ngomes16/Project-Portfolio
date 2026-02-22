/**
 * File: app/trip/[id].tsx
 * Purpose: Trip detail screen with tabs: Overview (rich details), Itinerary, Members, Expenses. Uses centralized TripsStore.
 * Update: Navigates to dedicated pages for adding/editing itinerary and adding expenses. Added Delete Trip action and
 *         Firestore-backed member search/add from the Members tab.
 */
import React from 'react';
import { View, Text, StyleSheet, Pressable, Alert } from 'react-native';
import { Screen } from '../../src/components/Screen';
import { useTheme } from '../../src/theme/ThemeProvider';
import { useTrips } from '../../src/state/TripsStore';
import { useLocalSearchParams } from 'expo-router';
import { Avatar } from '../../src/components/Avatar';
import { Card } from '../../src/components/Card';
import { Segmented } from '../../src/components/Segmented';
import { Button } from '../../src/components/Button';
import { TextField } from '../../src/components/TextField';
import { useTrips as useTripsStore } from '../../src/state/TripsStore';
import { searchUsersByUsernameOrEmail } from '../../src/services/firestore';
import { ItineraryTimeline } from '../../src/components/trip/ItineraryTimeline';
import { MemberRow } from '../../src/components/MemberRow';
import { Link, useRouter } from 'expo-router';
import { ExpenseForm } from '../../src/components/ExpenseForm';
import { TripOverviewCard } from '../../src/components/trip/TripOverviewCard';
import { TripSectionBar } from '../../src/components/trip/TripSectionBar';
import { ItineraryList } from '../../src/components/trip/ItineraryList';
// Removed modal-based member details/add in favor of pages and inline search.
import { SplitBalances } from '../../src/components/trip/SplitBalances';
import { ExpensesSection } from '../../src/components/trip/ExpensesSection';
import { SettleUpCard } from '../../src/components/trip/SettleUpCard';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '../../src/state/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { MiniCalendar } from '../../src/components/trip/MiniCalendar';

export default function TripDetail() {
  const theme = useTheme();
  const { id, tab: tabParam } = useLocalSearchParams<{ id: string; tab?: string }>();
  const router = useRouter();
  const { trips, selectTrip } = useTrips();
  const { user } = useAuth();
  const trip = trips.find(t => t.id === id);
  const insets = useSafeAreaInsets();
  React.useEffect(() => { if (trip) selectTrip(trip.id); }, [trip, selectTrip]);
  if (!trip) {
    return (
      <Screen>
        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
          <Pressable onPress={() => router.back()} hitSlop={12} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, marginRight: 12 })}>
            <Ionicons name="chevron-back" size={24} color={theme.colors.textPrimary} />
          </Pressable>
        </View>
        <Text style={{ color: theme.colors.textPrimary }}>Trip not found.</Text>
      </Screen>
    );
  }
  const total = trip.itinerary.reduce((s, i) => s + i.total, 0);

  const [tab, setTab] = React.useState<'Overview' | 'Itinerary' | 'Members' | 'Expenses'>(
    (tabParam === 'Itinerary' || tabParam === 'Members' || tabParam === 'Expenses') ? (tabParam as any) : 'Overview'
  );
  const { addMember: addTripMember, removeMember: removeTripMember, deleteTrip } = useTripsStore();
  const [showSearch, setShowSearch] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const [searching, setSearching] = React.useState(false);
  const [searchResults, setSearchResults] = React.useState<{ id: string; username: string; name: string; avatarColor: string }[]>([]);

  const [selectedDate, setSelectedDate] = React.useState<string | null>(null);

  return (
    <Screen scroll edges={["left","right","bottom"]} floatingBottom={<TripSectionBar value={tab} onChange={(v) => setTab(v)} />}>
      {tab !== 'Overview' && (
        <>
          {/* Add safe-area spacer for non-Overview tabs since Screen excludes top edge */}
          <View style={{ height: (insets.top || 0) + 8 }} />
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
            <Pressable onPress={() => router.back()} hitSlop={12} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, marginRight: 12 })}>
              <Ionicons name="chevron-back" size={24} color={theme.colors.textPrimary} />
            </Pressable>
          </View>
          <Text style={[styles.title, { color: theme.colors.textPrimary }]}>{trip.name}</Text>
          <Text style={{ color: theme.colors.textSecondary }}>{trip.destination} • {trip.dateRange}</Text>
          <View style={{ height: 12 }} />
        </>
      )}
      {/* Old top segmented control removed in favor of bottom TripSectionBar */}

      {tab === 'Overview' && (
        <TripOverviewCard trip={trip} />
      )}

      {tab === 'Itinerary' && (
        <>
          <MiniCalendar startDate={trip.startDate || '2025-09-01'} endDate={trip.endDate || '2025-09-30'} selectedDate={selectedDate} onChangeSelectedDate={setSelectedDate} />
          <Card style={{ marginTop: 12 }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Timeline</Text>
            <ItineraryTimeline items={trip.itinerary} filterDate={selectedDate} />
          </Card>
          <ItineraryList
            items={trip.itinerary}
            onAddNew={() => router.push({ pathname: '/trip/[id]/itinerary/new', params: { id: trip.id } })}
            onEdit={(item) => router.push({ pathname: '/trip/[id]/itinerary/[itemId]/edit', params: { id: trip.id, itemId: item.id } })}
            onAddExpense={(item) => router.push({ pathname: '/trip/[id]/itinerary/[itemId]/expense', params: { id: trip.id, itemId: item.id } })}
          />
        </>
      )}

      {tab === 'Members' && (
        <Card style={{ marginTop: 16 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Members</Text>
            <Button label={showSearch ? 'Done' : 'Add'} onPress={() => setShowSearch(s => !s)} style={{ width: 90 }} />
          </View>
          {/* Removed SettleUp on Members tab per redesign */}
          {showSearch && (
            <View style={{ marginTop: 10 }}>
              <TextField
                placeholder="search by username or email"
                value={search}
                onChangeText={async (v) => {
                  setSearch(v);
                  if (!v.trim()) { setSearchResults([]); return; }
                  try {
                    setSearching(true);
                    const results = await searchUsersByUsernameOrEmail(v.trim().toLowerCase());
                    const mapped = results.map(r => ({ id: r.id, username: (r as any).username, name: (r as any).displayName || (r as any).name || (r as any).email || 'User', avatarColor: ['#7C5CFF','#22C55E','#F59E0B','#0EA5E9'][Math.floor(Math.random()*4)] }));
                    setSearchResults(mapped);
                  } catch (e) {
                    setSearchResults([]);
                  } finally { setSearching(false); }
                }}
              />
              {searching ? <Text style={{ color: theme.colors.textSecondary }}>Searching…</Text> : null}
              {searchResults.map(u => (
                <View key={u.id} style={{ borderTopColor: theme.colors.border, borderTopWidth: 1, paddingTop: 8, marginTop: 8, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text style={{ color: theme.colors.textPrimary }}>{u.name} @{u.username}</Text>
                  <Button label="Add" onPress={() => {
                    if (!trip.members.some(m => m.id === u.id)) {
                      addTripMember(trip.id, { id: u.id, name: u.name, avatarColor: u.avatarColor });
                    }
                  }} style={{ width: 90 }} />
                </View>
              ))}
            </View>
          )}
          {trip.members.map(m => (
            <View key={m.id} style={{ flexDirection: 'row', alignItems: 'center' }}>
              <View style={{ flex: 1 }}>
                <MemberRow id={m.id} name={m.name} avatarColor={m.avatarColor} onView={(mid) => router.push({ pathname: '/trip/[id]/member/[memberId]', params: { id: trip.id, memberId: mid } })} />
              </View>
              <View style={{ marginLeft: 8 }}>
                <Button
                  label={m.id === '1' ? 'Owner' : 'Remove'}
                  variant={m.id === '1' ? 'secondary' : 'primary'}
                  onPress={() => { if (m.id !== '1') removeTripMember(trip.id, m.id); }}
                  style={{ width: 100 }}
                />
              </View>
            </View>
          ))}
        </Card>
      )}

      {tab === 'Expenses' && (
        <>
          <SettleUpCard trip={trip} userId={user?.uid || '1'} subtitle={'You Owe'} onSettleUp={() => {}} />
          <ExpensesSection trip={trip} onAddExpense={() => router.push({ pathname: '/trip/[id]/itinerary/[itemId]/expense', params: { id: trip.id, itemId: '' } })} />
          <SplitBalances trip={trip} />
          <Card style={{ marginTop: 16 }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Needs Your Input</Text>
            {trip.itinerary.filter(i => i.startAt && Date.parse(i.startAt) < Date.now() && !(trip.expenses || []).some(e => e.itemId === i.id)).map(i => (
              <View key={i.id} style={{ borderTopWidth: 1, borderTopColor: theme.colors.border, paddingTop: 8, marginTop: 8 }}>
                <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{i.label}</Text>
                <Text style={{ color: theme.colors.textSecondary }}>Event finished. Add actual expense?</Text>
                <Button label="Add Expense" onPress={() => router.push({ pathname: '/trip/[id]/itinerary/[itemId]/expense', params: { id: trip.id, itemId: i.id } })} style={{ marginTop: 8 }} />
              </View>
            ))}
          </Card>
        </>
      )}

      {/* Itinerary add/edit now uses dedicated pages; legacy modal removed */}

      {/* Expenses now navigates to dedicated page; legacy modal removed */}
      {/* Bottom in-screen section bar now passed via Screen.floatingBottom to anchor above safe-area */}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '700' },
});


