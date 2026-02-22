/**
 * File: src/components/FAB.tsx
 * Purpose: Floating action button for prominent actions like creating a trip.
 */
import React from 'react';
import { Pressable, Text } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type Props = { label?: string; onPress: () => void };

export function FAB({ label = '+', onPress }: Props) {
  const theme = useTheme();
  return (
    <Pressable onPress={onPress} style={({ pressed }) => ({ position: 'absolute', right: 20, bottom: 24, width: 56, height: 56, borderRadius: 28, backgroundColor: theme.colors.primary, alignItems: 'center', justifyContent: 'center', opacity: pressed ? 0.9 : 1 })}>
      <Text style={{ color: 'white', fontSize: 28, fontWeight: '800', marginTop: -2 }}>{label}</Text>
    </Pressable>
  );
}


