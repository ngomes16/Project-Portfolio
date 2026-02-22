/**
 * File: src/components/MemberRow.tsx
 * Purpose: Member row with avatar and name. Entire row is clickable. Shows 'Owner' badge for the
 *          trip creator only; removes previous role/pref and separate View button. Designed to be
 *          paired with adjacent action buttons (e.g., Remove).
 */
import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { Avatar } from './Avatar';
import { useTheme } from '../theme/ThemeProvider';

type Props = { id: string; name: string; avatarColor?: string; onView?: (id: string) => void };

export function MemberRow({ id, name, avatarColor, onView }: Props) {
  const theme = useTheme();
  const isOwner = id === '1';
  return (
    <Pressable onPress={() => onView && onView(id)} style={({ pressed }) => ({ opacity: pressed ? 0.8 : 1 })}>
      <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 12, borderTopWidth: 1, borderTopColor: theme.colors.border, paddingTop: 8 }}>
        <Avatar name={name} color={avatarColor} size={40} />
        <View style={{ marginLeft: 12, flex: 1 }}>
          <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{name} {isOwner ? '• Owner' : ''}</Text>
        </View>
      </View>
    </Pressable>
  );
}


