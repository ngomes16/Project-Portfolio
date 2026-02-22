/**
 * File: src/components/trip/AddMemberModal.tsx
 * Purpose: Modal for inviting/adding a member to a trip by name or username.
 */
import React from 'react';
import { Modal, View, Text } from 'react-native';
import { SwipeableSheet } from '../SwipeableSheet';
import { useTheme } from '../../theme/ThemeProvider';
import { TextField } from '../TextField';
import { Button } from '../Button';

type Props = {
  visible: boolean;
  name: string;
  onName: (v: string) => void;
  onInvite: () => void;
  onCancel: () => void;
};

export function AddMemberModal({ visible, name, onName, onInvite, onCancel }: Props) {
  const theme = useTheme();
  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
        <SwipeableSheet onClose={onCancel} style={{ backgroundColor: theme.colors.surface, padding: 16, borderTopLeftRadius: 20, borderTopRightRadius: 20, borderColor: theme.colors.border, borderWidth: 1 }}>
          <Text style={{ color: theme.colors.textPrimary, fontSize: 18, fontWeight: '700' }}>Add Member</Text>
          <TextField label="Name or username" value={name} onChangeText={onName} />
          <Button label="Invite" onPress={onInvite} />
          <View style={{ height: 8 }} />
          <Button label="Cancel" variant="secondary" onPress={onCancel} />
        </SwipeableSheet>
      </View>
    </Modal>
  );
}


