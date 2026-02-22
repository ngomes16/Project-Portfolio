/**
 * File: src/components/budget/GiftModal.tsx
 * Purpose: Modal for gifting a contribution amount to a friend.
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
  onSend: () => void;
  onCancel: () => void;
};

export function GiftModal({ visible, amount, onAmount, onSend, onCancel }: Props) {
  const theme = useTheme();
  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
        <SwipeableSheet onClose={onCancel} style={{ backgroundColor: theme.colors.surface, padding: 16, borderTopLeftRadius: 20, borderTopRightRadius: 20, borderColor: theme.colors.border, borderWidth: 1 }}>
          <Text style={{ color: theme.colors.textPrimary, fontSize: 18, fontWeight: '700' }}>Gift a Friend</Text>
          <TextField label="Amount ($)" keyboardType="numeric" value={amount} onChangeText={onAmount} />
          <Button label="Send Gift" onPress={onSend} />
          <View style={{ height: 8 }} />
          <Button label="Cancel" variant="secondary" onPress={onCancel} />
        </SwipeableSheet>
      </View>
    </Modal>
  );
}


