/**
 * File: src/components/DateField.tsx
 * Purpose: TextField wrapper with trailing calendar icon. Opens OS-native date picker and writes selected date
 *          as MM-DD-YYYY into the input.
 */
import React from 'react';
import { View, Pressable } from 'react-native';
import { TextField } from './TextField';
import { useTheme } from '../theme/ThemeProvider';
import { Ionicons } from '@expo/vector-icons';
import DateTimePicker from '@react-native-community/datetimepicker';

type Props = {
  label: string;
  placeholder?: string;
  value: string;
  onChangeText: (v: string) => void;
};

export function DateField({ label, placeholder = 'MM-DD-YYYY', value, onChangeText }: Props) {
  const theme = useTheme();
  const [open, setOpen] = React.useState(false);
  const [tempDate, setTempDate] = React.useState<Date>(new Date());

  const formatDate = (d: Date) => {
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const yyyy = d.getFullYear();
    return `${mm}-${dd}-${yyyy}`;
  };

  return (
    <View style={{ position: 'relative' }}>
      <TextField label={label} placeholder={placeholder} value={value} onChangeText={onChangeText} />
      <Pressable onPress={() => setOpen(true)} style={({ pressed }) => ({ position: 'absolute', right: 10, top: 32, opacity: pressed ? 0.6 : 1 })}>
        <Ionicons name="calendar" size={20} color={theme.colors.textSecondary} />
      </Pressable>
      {open && (
        <DateTimePicker
          value={tempDate}
          mode="date"
          display="default"
          onChange={(event, selectedDate) => {
            if (event.type === 'set' && selectedDate) {
              setTempDate(selectedDate);
              onChangeText(formatDate(selectedDate));
            }
            setOpen(false);
          }}
        />
      )}
    </View>
  );
}


