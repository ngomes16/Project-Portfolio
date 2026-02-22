/**
 * File: app/trip/[id]/member/[memberId].tsx
 * Purpose: Basic member profile page opened from Members tab. Shows avatar and name.
 */
import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Screen } from '../../../../src/components/Screen';
import { useTheme } from '../../../../src/theme/ThemeProvider';
import { useTrips } from '../../../../src/state/TripsStore';
import { Avatar } from '../../../../src/components/Avatar';

export default function MemberProfilePage() {
  const theme = useTheme();
  const router = useRouter();
  const { id, memberId } = useLocalSearchParams<{ id: string; memberId: string }>();
  const { trips } = useTrips();
  const trip = trips.find(t => t.id === id) || trips[0];
  const m = (trip.members || []).find(mm => mm.id === memberId);

  return (
    <Screen>
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
        <Pressable onPress={() => router.replace({ pathname: '/trip/[id]', params: { id } })} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, marginRight: 12 })}>
          <Text style={{ color: theme.colors.primary }}>{'< Back'}</Text>
        </Pressable>
      </View>
      <View style={{ alignItems: 'center', marginTop: 12 }}>
        <Avatar name={m?.name || ''} color={m?.avatarColor} size={96} />
        <Text style={{ color: theme.colors.textPrimary, fontSize: 22, fontWeight: '700', marginTop: 12 }}>{m?.name}</Text>
        {m?.id === '1' ? <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>Owner</Text> : null}
      </View>
    </Screen>
  );
}


