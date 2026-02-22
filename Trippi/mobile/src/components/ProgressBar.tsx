/**
 * File: src/components/ProgressBar.tsx
 * Purpose: Simple progress bar to visualize savings progress.
 */
import React from 'react';
import { View } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type Props = { progress: number; height?: number };

export function ProgressBar({ progress, height = 10 }: Props) {
  const theme = useTheme();
  const pct = Math.max(0, Math.min(1, progress));
  return (
    <View style={{ height, backgroundColor: theme.colors.border, borderRadius: height, overflow: 'hidden' }}>
      <View style={{ width: `${pct * 100}%`, height: '100%', backgroundColor: theme.colors.primary }} />
    </View>
  );
}


