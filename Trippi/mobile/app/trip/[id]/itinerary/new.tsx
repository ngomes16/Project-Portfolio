/**
 * File: app/trip/[id]/itinerary/new.tsx
 * Purpose: New page to add an itinerary item. Uses ItineraryForm and redirects back
 *          to the trip detail with the Itinerary tab active after submit/cancel.
 * Update: Persists to Firestore events subcollection when Firestore is configured.
 */
import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Screen } from '../../../../src/components/Screen';
import { useTheme } from '../../../../src/theme/ThemeProvider';
import { useTrips } from '../../../../src/state/TripsStore';
import { isDemoMode } from '../../../../src/firebase';
import { addEvent } from '../../../../src/services/firestore';
import { ItineraryForm } from '../../../../src/components/trip/ItineraryForm';

export default function NewItineraryItemPage() {
  const theme = useTheme();
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { addItineraryItem } = useTrips();

  return (
    <Screen scroll>
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
        <Pressable onPress={() => router.back()} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, marginRight: 12 })}>
          <Text style={{ color: theme.colors.primary }}>{'< Back'}</Text>
        </Pressable>
      </View>
      <Text style={{ color: theme.colors.textPrimary, fontSize: 22, fontWeight: '700' }}>Add Itinerary Item</Text>
      <View style={{ height: 12 }} />
      <ItineraryForm
        mode="add"
        onSubmit={(values) => {
          const item = { id: Math.random().toString(36).slice(2), label: values.label, total: values.total, category: values.category, startAt: values.startAt } as any;
          addItineraryItem(String(id), item);
          if (!isDemoMode) {
            // fire and forget
            addEvent(String(id), {
              title: values.label,
              start: values.startAt ? new Date(values.startAt) as any : new Date() as any,
              end: undefined,
              location: undefined,
              createdBy: 'unknown',
              notes: undefined,
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


