/**
 * File: src/components/budget/DonateModal.tsx
 * Purpose: Modal for entering a donation amount to the overall trip budget.
 */
import React from 'react';
import { Modal, View, Text } from 'react-native';
import { SwipeableSheet } from '../SwipeableSheet';
import { useTheme } from '../../theme/ThemeProvider';
import { TextField } from '../TextField';
import { Button } from '../Button';

type Props = {
  visible: boolean;
  amount: string;
  onAmount: (v: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
};

export function DonateModal({ visible, amount, onAmount, onConfirm, onCancel }: Props) {
  const theme = useTheme();
  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
        <SwipeableSheet onClose={onCancel} style={{ backgroundColor: theme.colors.surface, padding: 16, borderTopLeftRadius: 20, borderTopRightRadius: 20, borderColor: theme.colors.border, borderWidth: 1 }}>
          <Text style={{ color: theme.colors.textPrimary, fontSize: 18, fontWeight: '700' }}>Donate to Overall</Text>
          <TextField label="Amount ($)" keyboardType="numeric" value={amount} onChangeText={onAmount} />
          <Button label="Confirm" onPress={onConfirm} />
          <View style={{ height: 8 }} />
          <Button label="Cancel" variant="secondary" onPress={onCancel} />
        </SwipeableSheet>
      </View>
    </Modal>
  );
}


