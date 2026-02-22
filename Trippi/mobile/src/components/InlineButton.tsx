/**
 * File: src/components/InlineButton.tsx
 * Purpose: Compact button for inline actions in dense lists (e.g., itinerary rows).
 */
import React from 'react';
import { Pressable, StyleSheet, Text, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeProvider';

type Props = {
  label?: string;
  onPress: () => void;
  iconName?: React.ComponentProps<typeof Ionicons>['name'];
  variant?: 'primary' | 'secondary';
  style?: ViewStyle;
};

export function InlineButton({ label, onPress, iconName, variant = 'secondary', style }: Props) {
  const theme = useTheme();
  const isPrimary = variant === 'primary';
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        {
          backgroundColor: isPrimary ? theme.colors.primary : theme.colors.surface,
          borderColor: theme.colors.border,
          opacity: pressed ? 0.8 : 1,
        },
        style,
      ]}
    >
      {iconName ? (
        <Ionicons name={iconName} size={16} color={theme.colors.textPrimary} style={{ marginRight: label ? 6 : 0 }} />
      ) : null}
      {label ? <Text style={[styles.label, { color: theme.colors.textPrimary }]}>{label}</Text> : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 32,
    paddingHorizontal: 10,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
  },
});


