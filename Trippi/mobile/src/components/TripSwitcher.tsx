/**
 * File: src/components/TripSwitcher.tsx
 * Purpose: Modal-based trip picker to switch active trip in a user-friendly way.
 */
import React from 'react';
import { Modal, View, Text, Pressable } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { useTrips } from '../state/TripsStore';

type Props = { visible: boolean; onClose: () => void };

export function TripSwitcher({ visible, onClose }: Props) {
  const theme = useTheme();
  const { trips, selectedTripId, selectTrip } = useTrips();
  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
        <View style={{ backgroundColor: theme.colors.surface, padding: 16, borderTopLeftRadius: 20, borderTopRightRadius: 20, borderColor: theme.colors.border, borderWidth: 1 }}>
          <Text style={{ color: theme.colors.textPrimary, fontSize: 18, fontWeight: '700' }}>Select Trip</Text>
          {trips.map(t => (
            <Pressable key={t.id} onPress={() => { selectTrip(t.id); onClose(); }} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1, paddingVertical: 10 })}>
              <Text style={{ color: t.id === selectedTripId ? theme.colors.primary : theme.colors.textSecondary, fontWeight: t.id === selectedTripId ? '700' as any : '600' }}>{t.name} • {t.destination}</Text>
            </Pressable>
          ))}
          <Pressable onPress={onClose} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1, marginTop: 8 })}>
            <Text style={{ color: theme.colors.textSecondary, textAlign: 'center' }}>Close</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}


