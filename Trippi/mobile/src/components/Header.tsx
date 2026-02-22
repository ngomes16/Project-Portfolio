/**
 * File: src/components/Header.tsx
 * Purpose: Screen header with title and optional right/left actions.
 *          Provides a standard back button element via `Header.Back`.
 */
import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { Ionicons } from '@expo/vector-icons';

type Props = {
  title: string;
  left?: React.ReactNode;
  right?: React.ReactNode;
};

export function Header({ title, left, right }: Props) {
  const theme = useTheme();
  return (
    <View style={[styles.container, { borderBottomColor: theme.colors.border }]}> 
      <View style={styles.side}>{left}</View>
      <Text style={[styles.title, { color: theme.colors.textPrimary }]}>{title}</Text>
      <View style={styles.side}>{right}</View>
    </View>
  );
}

Header.Back = function Back({ onPress }: { onPress: () => void }) {
  const theme = useTheme();
  return (
    <Pressable onPress={onPress} hitSlop={10} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, flexDirection: 'row', alignItems: 'center' })}>
      <Ionicons name="chevron-back" color={theme.colors.textPrimary} size={24} />
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>Back</Text>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  container: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    paddingHorizontal: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
  },
  side: { width: 48 },
});


