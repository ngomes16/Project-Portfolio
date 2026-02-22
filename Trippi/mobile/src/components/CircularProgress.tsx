/**
 * File: src/components/CircularProgress.tsx
 * Purpose: Small circular progress ring with a percentage label overlay.
 *          Used on the Home screen's upcoming trip tiles to show savings progress.
 */
import React from 'react';
import { View, Text } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

type Props = {
  size?: number;
  strokeWidth?: number;
  progress: number; // 0..1
};

export function CircularProgress({ size = 42, strokeWidth = 4, progress }: Props) {
  const theme = useTheme();
  const pct = Math.max(0, Math.min(1, progress || 0));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dash = pct * circumference;

  return (
    <View style={{ width: size, height: size }}>
      <Svg width={size} height={size}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={theme.colors.border}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={theme.colors.primary}
          strokeWidth={strokeWidth}
          strokeDasharray={`${dash} ${circumference - dash}`}
          strokeDashoffset={0}
          strokeLinecap="round"
          fill="none"
          rotation={-90}
          origin={`${size / 2}, ${size / 2}`}
        />
      </Svg>
      <View style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ color: theme.colors.textPrimary, fontWeight: '700', fontSize: 11 }}>{Math.round(pct * 100)}%</Text>
      </View>
    </View>
  );
}

export default CircularProgress;


