/**
 * File: src/components/trip/ItineraryForm.tsx
 * Purpose: Reusable form for adding or editing itinerary items. Fields: Label (required),
 *          Budget Total ($), Category dropdown, and When (date & time). Includes keyboard
 *          accessory for prev/next/done across text inputs. Footer actions: Add/Confirm + Cancel.
 */
import React from 'react';
import { KeyboardAvoidingView, Platform, View, Text, TextInput } from 'react-native';
import { TextField } from '../TextField';
import { Select } from '../Select';
import { DateTimeField } from '../DateTimeField';
import { Button } from '../Button';
import { useTheme } from '../../theme/ThemeProvider';
import { KeyboardAccessory } from '../KeyboardAccessory';

export type Category = 'Lodging' | 'Flights' | 'Activities' | 'Food' | 'Transport' | 'Other';

type Props = {
  mode: 'add' | 'edit';
  initial?: { label?: string; total?: string; category?: Category; startAt?: string };
  onSubmit: (v: { label: string; total: number; category: Category; startAt?: string }) => void;
  onCancel: () => void;
};

export function ItineraryForm({ mode, initial, onSubmit, onCancel }: Props) {
  const theme = useTheme();
  const [label, setLabel] = React.useState(initial?.label ?? '');
  const [total, setTotal] = React.useState(initial?.total ?? '');
  const [category, setCategory] = React.useState<Category>(initial?.category ?? 'Other');
  const [startAt, setStartAt] = React.useState<string | undefined>(initial?.startAt);

  const labelRef = React.useRef<TextInput>(null);
  const totalRef = React.useRef<TextInput>(null);
  const inputs = [labelRef, totalRef];
  const accessoryId = 'itineraryFormAccessory';
  const [activeIndex, setActiveIndex] = React.useState(0);

  function focusIndex(i: number) {
    const idx = Math.max(0, Math.min(inputs.length - 1, i));
    inputs[idx].current?.focus();
    setActiveIndex(idx);
  }

  return (
    <KeyboardAvoidingView behavior={Platform.select({ ios: 'padding', android: undefined })}>
      <View style={{ maxWidth: 900, alignSelf: 'stretch' }}>
        <TextField
          ref={labelRef}
          label="Label"
          value={label}
          onChangeText={(t) => { setLabel(t); setActiveIndex(0); }}
          inputAccessoryViewID={accessoryId}
          returnKeyType="next"
          onSubmitEditing={() => focusIndex(1)}
        />
        <TextField
          ref={totalRef}
          label="Budget Total ($)"
          keyboardType="numeric"
          value={total}
          onChangeText={(t) => { setTotal(t); setActiveIndex(1); }}
          inputAccessoryViewID={accessoryId}
          returnKeyType="done"
        />
        <Select
          label="Category"
          options={[ 'Lodging','Flights','Activities','Food','Transport','Other' ]}
          value={category}
          onChange={(v) => setCategory(v as Category)}
        />
        <DateTimeField label="When" placeholder="MM-DD-YYYY HH-mm" value={startAt} onChange={setStartAt} />

        <View style={{ height: 8 }} />
        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <Button label="Cancel" variant="secondary" onPress={onCancel} style={{ flex: 1, marginRight: 8 }} />
          <Button
            label={mode === 'add' ? 'Add' : 'Confirm'}
            onPress={() => {
              if (!label.trim()) return;
              const n = Number(total || 0);
              onSubmit({ label: label.trim(), total: isNaN(n) ? 0 : n, category, startAt });
            }}
            style={{ flex: 1 }}
          />
        </View>
      </View>
      <KeyboardAccessory
        id={accessoryId}
        onPrev={() => focusIndex(activeIndex - 1)}
        onNext={() => focusIndex(activeIndex + 1)}
        onDone={() => inputs[activeIndex]?.current?.blur()}
      />
    </KeyboardAvoidingView>
  );
}


