/**
 * File: src/components/plan/AddItineraryItemModal.tsx
 * Purpose: Reusable modal for creating or editing an itinerary item inside Plan/Trip screens.
 */
import React from 'react';
import { Modal, View, Text } from 'react-native';
import { SwipeableSheet } from '../SwipeableSheet';
import { useTheme } from '../../theme/ThemeProvider';
import { TextField } from '../TextField';
import { Segmented } from '../Segmented';
import { Button } from '../Button';

type Category = 'Lodging' | 'Flights' | 'Transport' | 'Activities' | 'Food' | 'Other';

type Props = {
  visible: boolean;
  title?: string;
  label: string;
  onLabel: (v: string) => void;
  total: string;
  onTotal: (v: string) => void;
  category: Category;
  onCategory: (v: Category) => void;
  startAt?: string;
  onStartAt?: (v: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
};

export function AddItineraryItemModal({ visible, title, label, onLabel, total, onTotal, category, onCategory, startAt, onStartAt, onSubmit, onCancel }: Props) {
  const theme = useTheme();
  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
        <SwipeableSheet onClose={onCancel} style={{ backgroundColor: theme.colors.surface, padding: 16, borderTopLeftRadius: 20, borderTopRightRadius: 20, borderColor: theme.colors.border, borderWidth: 1 }}>
          <Text style={{ color: theme.colors.textPrimary, fontSize: 18, fontWeight: '700' }}>{title || 'Add Itinerary Item'}</Text>
          <TextField label="Label" value={label} onChangeText={onLabel} />
          <TextField label="Budget Total ($)" keyboardType="numeric" value={total} onChangeText={onTotal} />
          <Text style={{ color: theme.colors.textSecondary, marginBottom: 6 }}>Category</Text>
          <Segmented options={[
            { label: 'Lodging', value: 'Lodging' },
            { label: 'Flights', value: 'Flights' },
            { label: 'Transport', value: 'Transport' },
            { label: 'Activities', value: 'Activities' },
            { label: 'Food', value: 'Food' },
            { label: 'Other', value: 'Other' },
          ]} value={category} onChange={(v) => onCategory(v as Category)} />
          {onStartAt && (
            <>
              <View style={{ height: 12 }} />
              <TextField label="Start (YYYY-MM-DD HH:mm)" placeholder="2025-09-21 13:00" value={startAt || ''} onChangeText={onStartAt} />
            </>
          )}
          <Button label="Save" onPress={onSubmit} />
          <View style={{ height: 8 }} />
          <Button label="Cancel" variant="secondary" onPress={onCancel} />
        </SwipeableSheet>
      </View>
    </Modal>
  );
}


