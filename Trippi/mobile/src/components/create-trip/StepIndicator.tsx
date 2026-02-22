/**
 * File: src/components/create-trip/StepIndicator.tsx
 * Purpose: Visual indicator for the Create Trip wizard progress. Shows three steps (Details, Members, Review)
 *          with a modern segmented progress bar and step labels.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';

type Props = {
  steps: string[];
  currentIndex: number; // 0-based
};

export function StepIndicator({ steps, currentIndex }: Props) {
  const theme = useTheme();
  return (
    <View>
      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        {steps.map((_, i) => {
          const active = i <= currentIndex;
          return (
            <View key={i} style={{ flex: 1, height: 6, marginHorizontal: i === 0 ? 0 : 4, backgroundColor: active ? theme.colors.primary : theme.colors.border, borderRadius: 999 }} />
          );
        })}
      </View>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 }}>
        {steps.map((label, i) => (
          <Text key={label} style={{ color: i === currentIndex ? theme.colors.textPrimary : theme.colors.textSecondary, fontWeight: i === currentIndex ? '700' : '500', fontSize: 12 }}>{label}</Text>
        ))}
      </View>
    </View>
  );
}


