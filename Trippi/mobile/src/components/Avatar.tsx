/**
 * File: src/components/Avatar.tsx
 * Purpose: Circle avatar with initials and custom color.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type Props = { name: string; color?: string; size?: number };

export function Avatar({ name, color, size = 36 }: Props) {
  const theme = useTheme();
  const initials = name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
  return (
    <View style={{ width: size, height: size, borderRadius: size/2, backgroundColor: color || theme.colors.primary, alignItems: 'center', justifyContent: 'center' }}>
      <Text style={{ color: 'white', fontWeight: '700' }}>{initials}</Text>
    </View>
  );
}


