/**
 * File: src/components/create-trip/steps/MembersStep.tsx
 * Purpose: Members selection page for the Create Trip wizard. Mirrors members tab functionality:
 *          search users (Firestore) and add/remove; ensures creator is always selected.
 */
import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { TextField } from '../../../components/TextField';
import { Button } from '../../../components/Button';
import { useTheme } from '../../../theme/ThemeProvider';

export type Member = { id: string; name: string; avatarColor: string; username?: string };

type Props = {
  selectedMembers: Member[];
  onAdd: (m: Member) => void;
  onRemove: (id: string) => void;
  search: string;
  onSearch: (v: string) => void;
  results: Member[];
  searching?: boolean;
  onPrev: () => void;
  onNext: () => void;
};

export function MembersStep({ selectedMembers, onAdd, onRemove, search, onSearch, results, searching, onPrev, onNext }: Props) {
  const theme = useTheme();
  return (
    <View>
      <Text style={{ color: theme.colors.textPrimary, fontWeight: '700', marginBottom: 8 }}>Add members by username</Text>
      <TextField label="Search username" placeholder="Start typing..." value={search} onChangeText={onSearch} />
      {searching ? <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>Searching...</Text> : null}
      {results.map(u => (
        <Pressable key={u.id} onPress={() => onAdd(u)} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, borderTopColor: theme.colors.border, borderTopWidth: 1, paddingTop: 8, marginTop: 8 })}>
          <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{u.name}</Text>
          {u.username ? <Text style={{ color: theme.colors.textSecondary }}>@{u.username}</Text> : null}
        </Pressable>
      ))}
      <View style={{ marginTop: 12 }} />
      <Text style={{ color: theme.colors.textSecondary, fontWeight: '600' }}>Selected</Text>
      {selectedMembers.length === 0 ? <Text style={{ color: theme.colors.textSecondary, marginTop: 6 }}>No members yet.</Text> : null}
      {selectedMembers.map(m => (
        <View key={m.id} style={{ borderTopColor: theme.colors.border, borderTopWidth: 1, paddingTop: 8, marginTop: 8, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text style={{ color: theme.colors.textPrimary }}>{m.name}</Text>
          <Pressable onPress={() => onRemove(m.id)}><Text style={{ color: '#EF4444' }}>Remove</Text></Pressable>
        </View>
      ))}
      <View style={{ height: 12 }} />
      <View style={{ flexDirection: 'row', gap: 12 }}>
        <View style={{ flex: 1 }}><Button label="Previous" variant="secondary" onPress={onPrev} /></View>
        <View style={{ flex: 1 }}><Button label="Next" onPress={onNext} /></View>
      </View>
    </View>
  );
}


