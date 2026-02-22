/**
 * File: src/components/DateTimeField.tsx
 * Purpose: Combined date & time picker field with label and calendar icon. Uses OS-native picker
 *          via @react-native-community/datetimepicker. Displays placeholder MM-DD-YYYY HH-mm.
 */
import React from 'react';
import { Platform, View, Text, Pressable } from 'react-native';
import DateTimePicker, { DateTimePickerEvent } from '@react-native-community/datetimepicker';
import { useTheme } from '../theme/ThemeProvider';
import { Ionicons } from '@expo/vector-icons';

type Props = {
  label?: string;
  value?: string; // ISO string
  onChange: (iso?: string) => void;
  placeholder?: string;
};

function formatDisplay(date?: Date) {
  if (!date) return '';
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const yyyy = date.getFullYear();
  const HH = String(date.getHours()).padStart(2, '0');
  const mmn = String(date.getMinutes()).padStart(2, '0');
  return `${mm}-${dd}-${yyyy} ${HH}-${mmn}`;
}

export function DateTimeField({ label, value, onChange, placeholder }: Props) {
  const theme = useTheme();
  const [open, setOpen] = React.useState<'date' | 'time' | null>(null);
  const date = value ? new Date(value) : undefined;

  function onDateSelected(_e: DateTimePickerEvent, d?: Date) {
    if (!d) { setOpen(null); return; }
    const base = d;
    const time = date ?? new Date();
    base.setHours(time.getHours());
    base.setMinutes(time.getMinutes());
    onChange(base.toISOString());
    setOpen(Platform.OS === 'android' ? 'time' : null);
  }

  function onTimeSelected(_e: DateTimePickerEvent, d?: Date) {
    if (!d) { setOpen(null); return; }
    const base = date ?? new Date();
    base.setHours(d.getHours());
    base.setMinutes(d.getMinutes());
    onChange(base.toISOString());
    setOpen(null);
  }

  return (
    <View style={{ marginBottom: 12 }}>
      {label ? <Text style={{ color: theme.colors.textSecondary, marginBottom: 6 }}>{label}</Text> : null}
      <Pressable
        onPress={() => setOpen('date')}
        style={({ pressed }) => ({
          opacity: pressed ? 0.8 : 1,
          height: 48,
          borderRadius: 12,
          borderWidth: 1,
          borderColor: theme.colors.border,
          backgroundColor: theme.colors.surface,
          paddingHorizontal: 12,
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
        })}
      >
        <Text style={{ color: value ? theme.colors.textPrimary : theme.colors.textSecondary }}>
          {value ? formatDisplay(new Date(value)) : (placeholder || 'MM-DD-YYYY HH-mm')}
        </Text>
        <Ionicons name="calendar" size={18} color={theme.colors.textSecondary} />
      </Pressable>
      {open === 'date' && (
        <DateTimePicker value={date ?? new Date()} mode="date" display={Platform.OS === 'ios' ? 'inline' : 'calendar'} onChange={onDateSelected} />
      )}
      {open === 'time' && (
        <DateTimePicker value={date ?? new Date()} mode="time" display={Platform.OS === 'ios' ? 'spinner' : 'clock'} onChange={onTimeSelected} />
      )}
    </View>
  );
}


