/**
 * File: src/components/trip/MemberDetailsModal.tsx
 * Purpose: Modal presenting richer details for a trip member with quick actions.
 */
import React from 'react';
import { Modal, View, Text } from 'react-native';
import { SwipeableSheet } from '../SwipeableSheet';
import { TripMember } from '../../data/sample';
import { useTheme } from '../../theme/ThemeProvider';
import { Avatar } from '../Avatar';
import { Button } from '../Button';

type Props = { visible: boolean; onClose: () => void; member?: TripMember };

export function MemberDetailsModal({ visible, onClose, member }: Props) {
  const theme = useTheme();
  if (!member) return null;
  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
        <SwipeableSheet onClose={onClose} style={{ backgroundColor: theme.colors.surface, padding: 16, borderTopLeftRadius: 20, borderTopRightRadius: 20, borderColor: theme.colors.border, borderWidth: 1 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Avatar name={member.name} color={member.avatarColor} size={48} />
            <View style={{ marginLeft: 12 }}>
              <Text style={{ color: theme.colors.textPrimary, fontWeight: '700', fontSize: 16 }}>{member.name}</Text>
              <Text style={{ color: theme.colors.textSecondary }}>Traveler • Prefers even split</Text>
            </View>
          </View>
          <View style={{ height: 12 }} />
          <Text style={{ color: theme.colors.textSecondary }}>Bio: Foodie, architecture lover, enjoys riverwalk sunsets.</Text>
          <View style={{ height: 12 }} />
          <Button label="Message" onPress={onClose} />
          <View style={{ height: 8 }} />
          <Button label="Close" variant="secondary" onPress={onClose} />
        </SwipeableSheet>
      </View>
    </Modal>
  );
}


