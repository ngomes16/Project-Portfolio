/**
 * File: src/components/ExpenseForm.tsx
 * Purpose: Keyboard-safe expense form with modern segmented steps and sticky footer actions.
 */
import React from 'react';
import { KeyboardAvoidingView, Platform, View, ScrollView } from 'react-native';
import { TextField } from './TextField';
import { Button } from './Button';
import { Segmented } from './Segmented';

type Props = {
  amount: string; onAmount: (v: string) => void;
  paidBy: string; onPaidBy: (v: string) => void;
  splitWith: string; onSplitWith: (v: string) => void;
  onSubmit: () => void; onCancel: () => void;
};

export function ExpenseForm({ amount, onAmount, paidBy, onPaidBy, splitWith, onSplitWith, onSubmit, onCancel }: Props) {
  const [tab, setTab] = React.useState<'Amount' | 'Payer' | 'Split'>('Amount');
  return (
    <KeyboardAvoidingView behavior={Platform.select({ ios: 'padding', android: undefined })}>
      <View style={{ maxHeight: 420 }}>
        <Segmented options={[ { label: 'Amount', value: 'Amount' }, { label: 'Payer', value: 'Payer' }, { label: 'Split', value: 'Split' } ]} value={tab} onChange={(v) => setTab(v as 'Amount' | 'Payer' | 'Split')} />
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ paddingBottom: 16 }}>
          {tab === 'Amount' && (
            <TextField label="Amount ($)" keyboardType="numeric" value={amount} onChangeText={onAmount} />
          )}
          {tab === 'Payer' && (
            <TextField label="Paid by (member id)" value={paidBy} onChangeText={onPaidBy} />
          )}
          {tab === 'Split' && (
            <TextField label="Split with (ids, comma)" value={splitWith} onChangeText={onSplitWith} />
          )}
        </ScrollView>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <Button label="Cancel" variant="secondary" onPress={onCancel} style={{ flex: 1, marginRight: 8 }} />
          <Button label="Save Expense" onPress={onSubmit} style={{ flex: 1 }} />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}


