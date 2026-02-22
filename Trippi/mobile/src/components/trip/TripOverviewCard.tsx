/**
 * File: src/components/trip/TripOverviewCard.tsx
 * Purpose: Modern, engaging Overview for a trip. Renders a lightened, full-bleed hero
 *          image with readable overlaid title + dates, top-aligned controls (Back, Edit)
 *          that respect the safe area, and a metrics card showing Budget, Savings,
 *          and circular progress. Also displays a Notes card.
 * Update: Ensures hero extends to the very top of the screen by offsetting container
 *         margins and relying on Screen edges control. Keeps controls at the true top.
 */
import React from 'react';
import { View, Text, ImageBackground, Pressable, Dimensions, Modal, Alert } from 'react-native';
import Svg, { Defs, LinearGradient, Stop, Rect } from 'react-native-svg';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Trip } from '../../data/sample';
import { useTheme } from '../../theme/ThemeProvider';
import { Card } from '../Card';
import { CircularProgress } from '../CircularProgress';
import { PieChart } from '../PieChart';
import { formatCurrency } from '../../utils/format';
import { getDestinationImage } from '../../utils/images';
import { useTrips } from '../../state/TripsStore';

type Props = { trip: Trip };

export function TripOverviewCard({ trip }: Props) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { deleteTrip } = useTrips();
  const [menuVisible, setMenuVisible] = React.useState(false);

  const plannedTotal = trip.itinerary.reduce((sum, item) => sum + (item.total || 0), 0);
  const budget = trip.goalBudget ?? plannedTotal;
  const savings = (trip.contributions || []).reduce((sum, c) => sum + c.amount, 0);
  const progress = budget > 0 ? Math.max(0, Math.min(1, savings / budget)) : 0;
  const byCategory = React.useMemo(() => {
    const map: Record<string, number> = {};
    for (const it of trip.itinerary) map[it.category] = (map[it.category] || 0) + (it.total || 0);
    const colors: Record<string, string> = {
      Lodging: '#7C5CFF', Flights: '#5CB6FF', Transport: '#22C55E', Activities: '#F59E0B', Food: '#EF4444', Other: '#0EA5E9'
    };
    return Object.keys(map).map(k => ({ name: k, value: map[k], color: colors[k] || '#A78BFA' }));
  }, [trip.itinerary]);

  const win = Dimensions.get('window');
  const heroHeight = Math.max(240, Math.min(360, Math.round(win.height * 0.35)));

  return (
    <>
      {/* Full-bleed hero (~35% screen height) with top-aligned controls and title */}
      <View style={{ marginHorizontal: -16, marginTop: -16 }}>
        <ImageBackground source={{ uri: getDestinationImage(trip.destination) }} style={{ height: heroHeight, paddingTop: insets.top + 6, paddingHorizontal: 16 }}>
          <View pointerEvents="none" style={{ position: 'absolute', left: 0, right: 0, top: 0, bottom: 0 }}>
            <Svg width="100%" height="100%">
              <Defs>
                <LinearGradient id="lighten" x1="0%" y1="0%" x2="0%" y2="100%">
                  <Stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.28" />
                  <Stop offset="60%" stopColor="#FFFFFF" stopOpacity="0.58" />
                  <Stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.9" />
                </LinearGradient>
              </Defs>
              <Rect x="0" y="0" width="100%" height="100%" fill="url(#lighten)" />
            </Svg>
          </View>
          {/* Top controls absolutely positioned to remain at the very top */}
          <View style={{ position: 'absolute', left: 16, right: 16, top: insets.top + 6, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <Pressable onPress={() => router.back()} hitSlop={12} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}>
              <Ionicons name="chevron-back" size={26} color={theme.colors.textPrimary} />
            </Pressable>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '800', fontSize: 20 }}>Trippi</Text>
            <Pressable onPress={() => setMenuVisible(true)} hitSlop={12} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}>
              <Ionicons name="ellipsis-horizontal" size={22} color={theme.colors.textPrimary} />
            </Pressable>
          </View>
          <View style={{ flex: 1 }} />
          <View style={{ paddingBottom: 16 }}>
            <Text style={{ color: theme.colors.textPrimary, fontSize: 32, fontWeight: '800' }}>{trip.name}</Text>
            <Text style={{ color: theme.colors.textSecondary, fontSize: 15, marginTop: 4 }}>{trip.dateRange}</Text>
          </View>
        </ImageBackground>
      </View>

      {/* Options Menu */}
      <Modal transparent animationType="fade" visible={menuVisible} onRequestClose={() => setMenuVisible(false)}>
        <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.25)' }} onPress={() => setMenuVisible(false)}>
          <View style={{ position: 'absolute', top: insets.top + 52, right: 18, backgroundColor: theme.colors.surface, borderRadius: 12, borderWidth: 1, borderColor: theme.colors.border, minWidth: 180, paddingVertical: 6, shadowColor: '#000', shadowOpacity: 0.15, shadowRadius: 12, shadowOffset: { width: 0, height: 6 } }}>
            <Pressable
              onPress={() => { setMenuVisible(false); router.push({ pathname: '/trip/[id]/itinerary/new', params: { id: trip.id } }); }}
              style={({ pressed }) => ({ paddingHorizontal: 12, paddingVertical: 10, opacity: pressed ? 0.7 : 1 })}
            >
              <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>Edit Itinerary</Text>
            </Pressable>
            <View style={{ height: 1, backgroundColor: theme.colors.border }} />
            <Pressable
              onPress={() => {
                setMenuVisible(false);
                Alert.alert('Delete Trip', 'Are you sure you want to delete this trip? This cannot be undone.', [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Delete', style: 'destructive', onPress: () => { deleteTrip(trip.id); router.back(); } },
                ]);
              }}
              style={({ pressed }) => ({ paddingHorizontal: 12, paddingVertical: 10, opacity: pressed ? 0.7 : 1 })}
            >
              <Text style={{ color: '#EF4444', fontWeight: '700' }}>Delete Trip</Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>

      {/* Metrics Card */}
      <Card style={{ marginTop: 14 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <View style={{ flex: 1 }}>
            <Text style={{ color: theme.colors.textSecondary }}>Budget</Text>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '800', fontSize: 20 }}>{formatCurrency(budget || 0)}</Text>
            <View style={{ height: 10 }} />
            <View style={{ height: 1, backgroundColor: theme.colors.border, marginRight: 16 }} />
            <View style={{ height: 10 }} />
            <Text style={{ color: theme.colors.textSecondary }}>Savings</Text>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '800', fontSize: 20 }}>{formatCurrency(savings)}</Text>
          </View>
          <View style={{ width: 110, alignItems: 'center', justifyContent: 'center' }}>
            <CircularProgress size={90} strokeWidth={8} progress={progress} />
          </View>
        </View>
      </Card>

      {/* Notes Card */}
      <Card style={{ marginTop: 14 }}>
        <Text style={{ color: theme.colors.textPrimary, fontWeight: '700', marginBottom: 6 }}>Notes</Text>
        <Text style={{ color: theme.colors.textSecondary }}>
          {(trip as any).notes || 'Add notes to keep everyone aligned for this trip.'}
        </Text>
      </Card>

      {/* Budget by category */}
      {byCategory.length > 0 && (
        <Card style={{ marginTop: 14 }}>
          <Text style={{ color: theme.colors.textPrimary, fontWeight: '700', marginBottom: 10 }}>Budget Breakdown</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <PieChart size={120} thickness={18} segments={byCategory.map(s => ({ value: s.value, color: s.color }))} />
            <View style={{ marginLeft: 12, flex: 1 }}>
              {byCategory.map(s => (
                <View key={s.name} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
                  <View style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: s.color, marginRight: 8 }} />
                  <Text style={{ color: theme.colors.textSecondary, flex: 1 }}>{s.name}</Text>
                  <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{formatCurrency(s.value)}</Text>
                </View>
              ))}
            </View>
          </View>
        </Card>
      )}
    </>
  );
}


