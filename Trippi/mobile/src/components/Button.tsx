/**
 * File: src/components/Button.tsx
 * Purpose: Primary and secondary button with consistent styling and loading state.
 * Update: Added optional `gradient` variant for high-emphasis CTAs using a
 *         purple→blue horizontal gradient background to match the new design.
 */
import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View, ViewStyle } from 'react-native';
import Svg, { Defs, LinearGradient, Stop, Rect } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

type Props = {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'gradient';
  loading?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
};

export function Button({ label, onPress, variant = 'primary', loading = false, disabled = false, style }: Props) {
  const theme = useTheme();
  const isPrimary = variant === 'primary';

  if (variant === 'gradient') {
    return (
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [
          styles.base,
          { borderColor: 'transparent', opacity: pressed || loading || disabled ? 0.9 : 1, overflow: 'hidden' },
          style,
        ]}
        disabled={loading || disabled}
      >
        <View style={{ position: 'absolute', left: 0, right: 0, top: 0, bottom: 0 }} pointerEvents="none">
          <Svg width="100%" height="100%">
            <Defs>
              <LinearGradient id="btnGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <Stop offset="0%" stopColor="#7C5CFF" />
                <Stop offset="100%" stopColor="#5CB6FF" />
              </LinearGradient>
            </Defs>
            <Rect x="0" y="0" width="100%" height="100%" fill="url(#btnGrad)" rx={14} ry={14} />
          </Svg>
        </View>
        {loading ? (
          <ActivityIndicator color={'white'} />
        ) : (
          <Text style={[styles.label, { color: 'white', fontWeight: '800' }]}>{label}</Text>
        )}
      </Pressable>
    );
  }
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        {
          backgroundColor: isPrimary ? theme.colors.primary : theme.colors.surface,
          borderColor: theme.colors.border,
          opacity: pressed || loading || disabled ? 0.7 : 1,
        },
        style,
      ]}
      disabled={loading || disabled}
    >
      {loading ? (
        <ActivityIndicator color={isPrimary ? 'white' : theme.colors.textPrimary} />
      ) : (
        <Text style={[styles.label, { color: isPrimary ? 'white' : theme.colors.textPrimary }]}>{label}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 52,
    borderRadius: 14,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
  },
});


