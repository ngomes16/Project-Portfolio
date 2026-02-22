/**
 * File: src/components/ListItem.tsx
 * Purpose: Reusable row item with left/right content and press handling.
 */
import React from 'react';
import { Pressable, View, Text } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type Props = { title: string; subtitle?: string; left?: React.ReactNode; right?: React.ReactNode; onPress?: () => void };

export function ListItem({ title, subtitle, left, right, onPress }: Props) {
  const theme = useTheme();
  return (
    <Pressable onPress={onPress} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}>
      <View style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 12 }}>
        {left ? <View style={{ marginRight: 12 }}>{left}</View> : null}
        <View style={{ flex: 1 }}>
          <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{title}</Text>
          {subtitle ? <Text style={{ color: theme.colors.textSecondary, marginTop: 2 }}>{subtitle}</Text> : null}
        </View>
        {right}
      </View>
    </Pressable>
  );
}


