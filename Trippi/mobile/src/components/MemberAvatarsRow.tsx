/**
 * File: src/components/MemberAvatarsRow.tsx
 * Purpose: Compact overlapping avatars row for trip member previews.
 */
import React from 'react';
import { View } from 'react-native';
import { Avatar } from './Avatar';

type Member = { id: string; name: string; avatarColor?: string };
type Props = { members: Member[]; size?: number; max?: number };

export function MemberAvatarsRow({ members, size = 28, max = 4 }: Props) {
  const visible = members.slice(0, max);
  return (
    <View style={{ flexDirection: 'row' }}>
      {visible.map((m, idx) => (
        <View key={m.id || m.name + idx} style={{ marginRight: 6 }}>
          <Avatar name={m.name} color={m.avatarColor} size={size} />
        </View>
      ))}
    </View>
  );
}


