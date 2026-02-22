/**
 * File: src/components/PieChart.tsx
 * Purpose: Minimal pie chart using react-native-svg for budget breakdowns. Supports per-segment
 *          press handling by passing an onPress handler. Each arc is rendered as a separate stroke.
 */
import React from 'react';
import Svg, { Circle } from 'react-native-svg';
import { Pressable } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type Segment = { value: number; color: string; id?: string };
type Props = { size?: number; thickness?: number; segments: Segment[]; onPressSegment?: (index: number) => void };

export function PieChart({ size = 120, thickness = 16, segments, onPressSegment }: Props) {
  const theme = useTheme();
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;

  let offset = 0;

  return (
    <Svg width={size} height={size}>
      <Circle cx={size/2} cy={size/2} r={radius} stroke={theme.colors.border} strokeWidth={thickness} fill="none" />
      {segments.map((seg, idx) => {
        const segLength = (seg.value / total) * circumference;
        const circle = (
          <Circle
            key={idx}
            cx={size/2}
            cy={size/2}
            r={radius}
            stroke={seg.color}
            strokeWidth={thickness}
            strokeDasharray={`${segLength} ${circumference - segLength}`}
            strokeDashoffset={-offset}
            strokeLinecap="butt"
            fill="none"
            onPress={onPressSegment ? () => onPressSegment(idx) : undefined}
          />
        );
        offset += segLength;
        return circle;
      })}
    </Svg>
  );
}


