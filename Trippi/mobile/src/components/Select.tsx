/**
 * File: src/components/Select.tsx
 * Purpose: Simple dropdown/select input with label. Renders a tappable field that opens
 *          a modal sheet of options. Designed to avoid external picker deps and match app style.
 */
import React from 'react';
import { Modal, Pressable, View, Text, FlatList } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { Ionicons } from '@expo/vector-icons';

export type Option = { label: string; value: string } | string;

type Props = {
  label?: string;
  placeholder?: string;
  value?: string;
  options: Option[];
  onChange: (value: string) => void;
};

function getLabel(opt: Option) { return typeof opt === 'string' ? opt : opt.label; }
function getValue(opt: Option) { return typeof opt === 'string' ? opt : opt.value; }

export function Select({ label, placeholder, value, options, onChange }: Props) {
  const theme = useTheme();
  const [open, setOpen] = React.useState(false);
  const selectedLabel = React.useMemo(() => {
    if (!value) return undefined;
    const found = options.find(o => getValue(o) === value);
    return found ? getLabel(found) : value;
  }, [value, options]);

  return (
    <>
      <View style={{ marginBottom: 12 }}>
        {label ? <Text style={{ color: theme.colors.textSecondary, marginBottom: 6 }}>{label}</Text> : null}
        <Pressable
          onPress={() => setOpen(true)}
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
          <Text style={{ color: selectedLabel ? theme.colors.textPrimary : theme.colors.textSecondary }}>
            {selectedLabel || placeholder || 'Select'}
          </Text>
          <Ionicons name="chevron-down" size={18} color={theme.colors.textSecondary} />
        </Pressable>
      </View>

      <Modal visible={open} animationType="slide" transparent onRequestClose={() => setOpen(false)}>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
          <View style={{ backgroundColor: theme.colors.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, borderWidth: 1, borderColor: theme.colors.border, maxHeight: 420 }}>
            <View style={{ alignItems: 'center', paddingVertical: 8 }}>
              <View style={{ width: 36, height: 5, borderRadius: 3, backgroundColor: theme.colors.border }} />
            </View>
            <FlatList
              contentContainerStyle={{ paddingVertical: 8 }}
              data={options}
              keyExtractor={(o) => getValue(o)}
              renderItem={({ item }) => (
                <Pressable
                  onPress={() => { onChange(getValue(item)); setOpen(false); }}
                  style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, paddingVertical: 14, paddingHorizontal: 16, borderTopWidth: 1, borderTopColor: theme.colors.border })}
                >
                  <Text style={{ color: theme.colors.textPrimary, fontWeight: getValue(item) === value ? '700' : '400' }}>{getLabel(item)}</Text>
                </Pressable>
              )}
            />
            <Pressable onPress={() => setOpen(false)} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1, padding: 14, alignItems: 'center' })}>
              <Text style={{ color: theme.colors.primary, fontWeight: '600' }}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </>
  );
}


