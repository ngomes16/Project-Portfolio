/**
 * File: src/components/SavingsPieChart.tsx
 * Purpose: Interactive pie (ring) chart for savings by trip. Each trip reserves a slice sized by
 *          its goal, with the saved portion rendered in full color and the remaining portion
 *          rendered with reduced opacity. Starts at 90° (top) and proceeds clockwise.
 */
import React from 'react';
import Svg, { Circle, G } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

export type SavingsSlice = {
  id?: string;
  name?: string;
  color: string;
  saved: number; // amount saved for this trip
  goal: number;  // goal for this trip
};

type Props = {
  size?: number;
  thickness?: number;
  slices: SavingsSlice[];
  onSelect?: (index: number) => void;
};

export function SavingsPieChart({ size = 160, thickness = 22, slices, onSelect }: Props) {
  const theme = useTheme();
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  const totalGoals = Math.max(1, slices.reduce((s, x) => s + Math.max(0, x.goal), 0));

  let offset = 0;

  return (
    <Svg width={size} height={size}>
      <G rotation={-90} origin={`${size / 2}, ${size / 2}`}>
        {/* base track */}
        <Circle cx={size/2} cy={size/2} r={radius} stroke={theme.colors.border} strokeWidth={thickness} fill="none" />
        {slices.map((slice, idx) => {
          const clampedGoal = Math.max(0, slice.goal);
          const clampedSaved = Math.max(0, Math.min(slice.saved, clampedGoal));
          const segmentLen = (clampedGoal / totalGoals) * circumference; // full arc for this slice
          const savedLen = (clampedSaved / totalGoals) * circumference;  // saved portion within slice
          const remainingLen = Math.max(0, segmentLen - savedLen);

          const elements: React.ReactNode[] = [];

          if (savedLen > 0) {
            elements.push(
              <Circle
                key={`saved-${idx}`}
                cx={size/2}
                cy={size/2}
                r={radius}
                stroke={slice.color}
                strokeWidth={thickness}
                strokeDasharray={`${savedLen} ${circumference - savedLen}`}
                strokeDashoffset={-offset}
                strokeLinecap="butt"
                fill="none"
                onPress={onSelect ? () => onSelect(idx) : undefined}
              />
            );
          }

          if (remainingLen > 0) {
            elements.push(
              <Circle
                key={`remain-${idx}`}
                cx={size/2}
                cy={size/2}
                r={radius}
                stroke={slice.color}
                strokeWidth={thickness}
                strokeDasharray={`${remainingLen} ${circumference - remainingLen}`}
                strokeDashoffset={-(offset + savedLen)}
                strokeLinecap="butt"
                fill="none"
                opacity={0.35}
                onPress={onSelect ? () => onSelect(idx) : undefined}
              />
            );
          }

          offset += segmentLen;
          return elements as any;
        })}
      </G>
    </Svg>
  );
}


