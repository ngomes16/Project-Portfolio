/**
 * File: src/components/Checkbox.tsx
 * Purpose: Minimal checkbox/toggle with label used in forms.
 */
import React from 'react';
import { Pressable, View, Text } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { Ionicons } from '@expo/vector-icons';

type Props = { label?: string; value: boolean; onChange: (v: boolean) => void };

export function Checkbox({ label, value, onChange }: Props) {
  const theme = useTheme();
  return (
    <Pressable onPress={() => onChange(!value)} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1, flexDirection: 'row', alignItems: 'center', marginVertical: 6 })}>
      <View style={{ width: 22, height: 22, borderRadius: 6, borderWidth: 1, borderColor: theme.colors.border, backgroundColor: value ? theme.colors.primary : theme.colors.surface, alignItems: 'center', justifyContent: 'center' }}>
        {value ? <Ionicons name="checkmark" size={16} color="#fff" /> : null}
      </View>
      {label ? <Text style={{ marginLeft: 8, color: theme.colors.textPrimary }}>{label}</Text> : null}
    </Pressable>
  );
}


