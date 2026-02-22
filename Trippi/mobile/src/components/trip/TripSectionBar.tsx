/**
 * File: src/components/trip/TripSectionBar.tsx
 * Purpose: In-screen bottom tab bar for Trip Detail that replaces the old
 *          top segmented control. Provides quick navigation between Overview,
 *          Itinerary, Members, and Expenses. Positioned above the app's main
 *          bottom tabs and respects safe areas.
 * Update: Label for the first tab renamed from "Trips" to "Overview".
 */
import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../theme/ThemeProvider';

export type TripSection = 'Overview' | 'Itinerary' | 'Members' | 'Expenses';

type Props = {
  value: TripSection;
  onChange: (value: TripSection) => void;
};

export function TripSectionBar({ value, onChange }: Props) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const Item = ({ icon, label, tab }: { icon: any; label: string; tab: TripSection }) => (
    <Pressable onPress={() => onChange(tab)} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, alignItems: 'center', flex: 1 })}>
      <Ionicons name={icon as any} size={22} color={value === tab ? theme.colors.primary : theme.colors.textSecondary} />
      <Text style={{ marginTop: 4, color: value === tab ? theme.colors.primary : theme.colors.textSecondary, fontSize: 12 }}>{label}</Text>
    </Pressable>
  );
  return (
    <View style={{ position: 'absolute', left: 12, right: 12, bottom: (insets.bottom || 0) + 2, backgroundColor: theme.colors.surface, borderRadius: 16, borderWidth: 1, borderColor: theme.colors.border, height: 56, paddingHorizontal: 12, flexDirection: 'row', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 3 }}>
      <Item icon="image-outline" label="Overview" tab="Overview" />
      <Item icon="calendar-outline" label="Itinerary" tab="Itinerary" />
      <Item icon="people-outline" label="Members" tab="Members" />
      <Item icon="receipt-outline" label="Expenses" tab="Expenses" />
    </View>
  );
}


