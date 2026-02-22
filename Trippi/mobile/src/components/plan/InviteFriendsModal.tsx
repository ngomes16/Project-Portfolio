/**
 * File: src/components/plan/InviteFriendsModal.tsx
 * Purpose: Reusable modal to invite a friend via username or email in planning flows.
 */
import React from 'react';
import { Modal, View, Text } from 'react-native';
import { SwipeableSheet } from '../SwipeableSheet';
import { useTheme } from '../../theme/ThemeProvider';
import { TextField } from '../TextField';
import { Button } from '../Button';

type Props = {
  visible: boolean;
  invitee: string;
  onInvitee: (v: string) => void;
  onSend: () => void;
  onCancel: () => void;
};

export function InviteFriendsModal({ visible, invitee, onInvitee, onSend, onCancel }: Props) {
  const theme = useTheme();
  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' }}>
        <SwipeableSheet onClose={onCancel} style={{ backgroundColor: theme.colors.surface, padding: 16, borderTopLeftRadius: 20, borderTopRightRadius: 20, borderColor: theme.colors.border, borderWidth: 1 }}>
          <Text style={{ color: theme.colors.textPrimary, fontSize: 18, fontWeight: '700' }}>Invite Friends</Text>
          <TextField label="Username or email" placeholder="friend@example.com" value={invitee} onChangeText={onInvitee} />
          <Button label="Send Invite" onPress={onSend} />
          <View style={{ height: 8 }} />
          <Button label="Cancel" variant="secondary" onPress={onCancel} />
        </SwipeableSheet>
      </View>
    </Modal>
  );
}


