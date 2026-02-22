/**
 * File: src/components/trip/SettleUpCard.tsx
 * Purpose: Compact summary card that shows the current user's balance for a trip
 *          (whether they owe or are owed) along with a high-emphasis "Settle Up"
 *          gradient button matching the new design. Used on Members and Expenses tabs.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { Trip } from '../../data/sample';
import { useTheme } from '../../theme/ThemeProvider';
import { Card } from '../Card';
import { Button } from '../Button';
import { computeBalances } from '../../utils/balances';

type Props = {
  trip: Trip;
  userId: string; // current user's uid (or '1' for demo)
  onSettleUp?: () => void;
  subtitle?: string;
};

export function SettleUpCard({ trip, userId, onSettleUp, subtitle }: Props) {
  const theme = useTheme();
  const balances = computeBalances(trip);
  const me = balances.find(b => b.memberId === userId);
  const amount = Math.abs(me?.balance || 0);
  const owes = (me?.balance ?? 0) < 0;

  return (
    <Card style={{ marginTop: 16 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ flex: 1, paddingRight: 12 }}>
          <Text style={{ color: theme.colors.textSecondary }}>{subtitle || (owes ? 'You Owe' : "You're Owed")}</Text>
          <Text style={{ color: theme.colors.textPrimary, fontWeight: '800', fontSize: 22 }}>${amount.toFixed(2)}</Text>
        </View>
        <Button label="Settle Up" variant="gradient" onPress={onSettleUp || (() => {})} style={{ minWidth: 120 }} />
      </View>
    </Card>
  );
}


