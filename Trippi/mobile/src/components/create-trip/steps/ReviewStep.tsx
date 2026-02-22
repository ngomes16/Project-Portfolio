/**
 * File: src/components/create-trip/steps/ReviewStep.tsx
 * Purpose: Final review page summarizing inputs. Shows read-only details and actions to go back or create.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { Button } from '../../../components/Button';
import { useTheme } from '../../../theme/ThemeProvider';

type Props = {
  name: string;
  destination: string;
  startDate?: string;
  endDate?: string;
  goalPerPerson?: string;
  members: { id: string; name: string }[];
  onPrev: () => void;
  onCreate: () => void;
};

export function ReviewStep({ name, destination, startDate, endDate, goalPerPerson, members, onPrev, onCreate }: Props) {
  const theme = useTheme();
  return (
    <View>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Review</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>Name: {name || '—'}</Text>
      <Text style={{ color: theme.colors.textSecondary }}>Destination: {destination || '—'}</Text>
      <Text style={{ color: theme.colors.textSecondary }}>Start: {startDate || '—'} • End: {endDate || '—'}</Text>
      <Text style={{ color: theme.colors.textSecondary }}>Goal Budget / Person: {goalPerPerson ? `$${goalPerPerson}` : '—'}</Text>
      <Text style={{ color: theme.colors.textSecondary }}>Members: {members.map(m => m.name).join(', ') || '—'}</Text>
      <View style={{ height: 12 }} />
      <View style={{ flexDirection: 'row', gap: 12 }}>
        <View style={{ flex: 1 }}><Button label="Previous" variant="secondary" onPress={onPrev} /></View>
        <View style={{ flex: 1 }}><Button label="Create" onPress={onCreate} /></View>
      </View>
    </View>
  );
}


