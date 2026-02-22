/**
 * File: src/components/KeyboardAccessory.tsx
 * Purpose: Reusable input accessory bar for iOS with Previous/Next/Done controls.
 *          Forms provide callbacks to move focus between fields. On Android, renders nothing.
 */
import React from 'react';
import { Platform, View, Pressable, Text } from 'react-native';
import { InputAccessoryView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeProvider';

type Props = {
  id: string;
  onPrev?: () => void;
  onNext?: () => void;
  onDone?: () => void;
};

export function KeyboardAccessory({ id, onPrev, onNext, onDone }: Props) {
  const theme = useTheme();
  if (Platform.OS !== 'ios') return null as any;
  return (
    <InputAccessoryView nativeID={id} backgroundColor={theme.colors.surface}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', borderTopWidth: 1, borderTopColor: theme.colors.border, paddingHorizontal: 8, paddingVertical: 6 }}>
        <Pressable onPress={onPrev} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1, padding: 6, marginRight: 6 })} accessibilityLabel="Previous field">
          <Ionicons name="chevron-up" size={18} color={theme.colors.textSecondary} />
        </Pressable>
        <Pressable onPress={onNext} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1, padding: 6, marginRight: 12 })} accessibilityLabel="Next field">
          <Ionicons name="chevron-down" size={18} color={theme.colors.textSecondary} />
        </Pressable>
        <Pressable onPress={onDone} style={({ pressed }) => ({ opacity: pressed ? 0.8 : 1, backgroundColor: theme.colors.primary, paddingVertical: 6, paddingHorizontal: 12, borderRadius: 8 })} accessibilityLabel="Done">
          <Text style={{ color: '#fff', fontWeight: '600' }}>Done</Text>
        </Pressable>
      </View>
    </InputAccessoryView>
  );
}


