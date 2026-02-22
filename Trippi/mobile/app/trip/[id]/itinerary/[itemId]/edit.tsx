/**
 * File: app/trip/[id]/itinerary/[itemId]/edit.tsx
 * Purpose: Edit page for an itinerary item. Pre-fills existing values and confirms updates.
 * Update: Persists to Firestore events subcollection when Firestore is configured.
 */
import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Screen } from '../../../../../src/components/Screen';
import { useTheme } from '../../../../../src/theme/ThemeProvider';
import { useTrips } from '../../../../../src/state/TripsStore';
import { ItineraryForm } from '../../../../../src/components/trip/ItineraryForm';
import { isDemoMode } from '../../../../../src/firebase';
import { updateEvent } from '../../../../../src/services/firestore';

export default function EditItineraryItemPage() {
  const theme = useTheme();
  const router = useRouter();
  const { id, itemId } = useLocalSearchParams<{ id: string; itemId: string }>();
  const { trips, editItineraryItem } = useTrips();
  const trip = trips.find(t => t.id === id) || trips[0];
  const item = (trip?.itinerary || []).find(i => i.id === itemId);

  return (
    <Screen scroll>
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
        <Pressable onPress={() => router.back()} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, marginRight: 12 })}>
          <Text style={{ color: theme.colors.primary }}>{'< Back'}</Text>
        </Pressable>
      </View>
      <Text style={{ color: theme.colors.textPrimary, fontSize: 22, fontWeight: '700' }}>Edit Itinerary Item</Text>
      <View style={{ height: 12 }} />
      <ItineraryForm
        mode="edit"
        initial={{ label: item?.label, total: String(item?.total ?? ''), category: item?.category as any, startAt: item?.startAt }}
        onSubmit={(values) => {
          if (!item) return;
          editItineraryItem(String(id), { id: item.id, label: values.label, total: values.total, category: values.category, startAt: values.startAt } as any);
          if (!isDemoMode) {
            updateEvent(String(id), String(itemId), {
              title: values.label,
              start: values.startAt ? new Date(values.startAt) as any : undefined,
              category: values.category,
              budgetTotal: values.total,
            }).catch(() => {});
          }
          router.back();
        }}
        onCancel={() => router.back()}
      />
    </Screen>
  );
}


