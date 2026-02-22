/**
 * File: src/components/Segmented.tsx
 * Purpose: Simple segmented control to switch between sections within a screen.
 */
import React from 'react';
import { View, Pressable, Text, StyleProp, ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type Option = { label: string; value: string };
type Props = { options: Option[]; value: string; onChange: (val: string) => void; style?: StyleProp<ViewStyle> };

export function Segmented({ options, value, onChange, style }: Props) {
  const theme = useTheme();
  return (
    <View style={[{ flexDirection: 'row', backgroundColor: theme.colors.surface, borderRadius: 12, borderWidth: 1, borderColor: theme.colors.border, overflow: 'hidden' }, style]}>
      {options.map(opt => {
        const active = opt.value === value;
        return (
          <Pressable key={opt.value} onPress={() => onChange(opt.value)} style={({ pressed }) => ({ flex: 1, paddingVertical: 10, backgroundColor: active ? theme.colors.primary : 'transparent', opacity: pressed ? 0.9 : 1 })}>
            <Text style={{ color: active ? 'white' : theme.colors.textSecondary, textAlign: 'center', fontWeight: '600' }}>{opt.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}


