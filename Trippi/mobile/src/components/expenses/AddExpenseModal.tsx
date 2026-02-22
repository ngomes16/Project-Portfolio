/**
 * File: src/components/expenses/AddExpenseModal.tsx
 * Purpose: Container modal for the ExpenseForm, with open/close and submit handlers.
 */
import React from 'react';
import { Modal, View, Text } from 'react-native';
import { SwipeableSheet } from '../SwipeableSheet';
import { useTheme } from '../../theme/ThemeProvider';
import { ExpenseForm } from '../ExpenseForm';

type Props = {
  visible: boolean;
  amount: string;
  onAmount: (v: string) => void;
  paidBy: string;
  onPaidBy: (v: string) => void;
  splitWith: string;
  onSplitWith: (v: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
};

export function AddExpenseModal({ visible, amount, onAmount, paidBy, onPaidBy, splitWith, onSplitWith, onSubmit, onCancel }: Props) {
  const theme = useTheme();
  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
        <SwipeableSheet onClose={onCancel} style={{ backgroundColor: theme.colors.surface, padding: 16, borderTopLeftRadius: 20, borderTopRightRadius: 20, borderColor: theme.colors.border, borderWidth: 1, maxHeight: 520 }}>
          <Text style={{ color: theme.colors.textPrimary, fontSize: 18, fontWeight: '700' }}>Add Expense</Text>
          <ExpenseForm
            amount={amount}
            onAmount={onAmount}
            paidBy={paidBy}
            onPaidBy={onPaidBy}
            splitWith={splitWith}
            onSplitWith={onSplitWith}
            onSubmit={onSubmit}
            onCancel={onCancel}
          />
        </SwipeableSheet>
      </View>
    </Modal>
  );
}


