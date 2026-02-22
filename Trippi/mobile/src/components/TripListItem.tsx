/**
 * File: src/components/TripListItem.tsx
 * Purpose: Rich list item for Trips tab with destination, dates, member count, and quick actions.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { Card } from './Card';
import { useTheme } from '../theme/ThemeProvider';
import { InlineButton } from './InlineButton';

type Props = { name: string; destination: string; dateRange?: string; members: number; onOpen: () => void };

export function TripListItem({ name, destination, dateRange, members, onOpen }: Props) {
  const theme = useTheme();
  return (
    <Card style={{ marginBottom: 12 }}>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>{name}</Text>
      <Text style={{ color: theme.colors.textSecondary }}>{destination} {dateRange ? `• ${dateRange}` : ''}</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>{members} members</Text>
      <View style={{ flexDirection: 'row', marginTop: 10 }}>
        <InlineButton label="Open" iconName="open" variant="primary" onPress={onOpen} />
        <InlineButton label="Share" iconName="share-social" onPress={() => {}} style={{ marginLeft: 8 }} />
      </View>
    </Card>
  );
}


