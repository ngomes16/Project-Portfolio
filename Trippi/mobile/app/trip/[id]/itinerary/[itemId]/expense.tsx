/**
 * File: app/trip/[id]/itinerary/[itemId]/expense.tsx
 * Purpose: Add Expense page with dynamic split editor. Supports amount input, optional
 *          group split with per-member overrides and inclusion toggles, mirroring the provided UI.
 * Update: Persists expense to Firestore when Firestore is configured.
 */
import React from 'react';
import { View, Text, Pressable, FlatList, TextInput, KeyboardAvoidingView, Platform } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Screen } from '../../../../../src/components/Screen';
import { useTheme } from '../../../../../src/theme/ThemeProvider';
import { useTrips } from '../../../../../src/state/TripsStore';
import { Avatar } from '../../../../../src/components/Avatar';
import { Button } from '../../../../../src/components/Button';
import { Checkbox } from '../../../../../src/components/Checkbox';
import { KeyboardAccessory } from '../../../../../src/components/KeyboardAccessory';
import { isDemoMode } from '../../../../../src/firebase';
import { addExpense as fsAddExpense } from '../../../../../src/services/firestore';

type MemberRowState = { id: string; name: string; avatarColor: string; included: boolean; amount: string };

export default function AddExpensePage() {
  const theme = useTheme();
  const router = useRouter();
  const { id, itemId } = useLocalSearchParams<{ id: string; itemId: string }>();
  const { trips, addExpense } = useTrips();
  const trip = trips.find(t => t.id === id) || trips[0];
  const members = trip.members;

  const [amount, setAmount] = React.useState('');
  const [group, setGroup] = React.useState(false);
  const [rows, setRows] = React.useState<MemberRowState[]>(() => members.map(m => ({ id: m.id, name: m.name, avatarColor: m.avatarColor, included: true, amount: '0' })));
  const accessoryId = 'expenseAccessory';

  React.useEffect(() => {
    if (!group) return;
    const total = Number(amount || 0);
    const included = rows.filter(r => r.included);
    const per = included.length > 0 ? Math.round((total / included.length) * 100) / 100 : 0;
    setRows(prev => prev.map(r => ({ ...r, amount: r.included ? String(per) : '0' })));
  }, [amount, group]);

  function toggleMember(idm: string) {
    setRows(prev => prev.map(r => r.id === idm ? { ...r, included: !r.included, amount: !r.included ? r.amount : '0' } : r));
  }

  function updateMemberAmount(idm: string, v: string) {
    setRows(prev => prev.map(r => r.id === idm ? { ...r, amount: v } : r));
  }

  function save() {
    const breakdown = Object.fromEntries(rows.map(r => [r.id, Number(r.amount || 0)]));
    addExpense(String(id), {
      id: Math.random().toString(36).slice(2),
      itemId: String(itemId),
      label: 'Expense',
      amount: Number(amount || 0),
      paidBy: '1',
      splitWith: rows.filter(r => r.included && Number(r.amount || 0) > 0).map(r => r.id),
      createdAt: new Date().toISOString(),
      breakdown,
    });
    if (!isDemoMode) {
      const participants = rows.filter(r => r.included && Number(r.amount || 0) > 0).map(r => r.id);
      fsAddExpense(String(id), {
        title: 'Expense',
        notes: undefined,
        amount: Number(amount || 0),
        currency: 'USD',
        date: new Date() as any,
        category: undefined,
        payers: [{ uid: '1', amount: Number(amount || 0) }],
        split: { type: 'custom', participants, shares: breakdown },
        createdBy: 'unknown',
        eventId: itemId ? String(itemId) : null,
      }).catch(() => {});
    }
    router.back();
  }

  return (
    <Screen scroll>
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
        <Pressable onPress={() => router.back()} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, marginRight: 12 })}>
          <Text style={{ color: theme.colors.primary }}>{'< Back'}</Text>
        </Pressable>
      </View>
      <Text style={{ color: theme.colors.textPrimary, fontSize: 22, fontWeight: '700' }}>Add Expense</Text>
      <View style={{ height: 12 }} />
      <KeyboardAvoidingView behavior={Platform.select({ ios: 'padding', android: undefined })}>
        <View>
          <Text style={{ color: theme.colors.textSecondary, marginBottom: 6 }}>Amount Paid</Text>
          <TextInput
            inputAccessoryViewID={accessoryId}
            keyboardType="numeric"
            placeholder="$0"
            placeholderTextColor={theme.colors.textSecondary}
            value={amount}
            onChangeText={setAmount}
            style={{ height: 48, borderRadius: 12, borderWidth: 1, borderColor: theme.colors.border, backgroundColor: theme.colors.surface, paddingHorizontal: 12, color: theme.colors.textPrimary }}
          />
          <Checkbox label="Paid for group members" value={group} onChange={setGroup} />

          {group && (
            <View style={{ marginTop: 8 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Split Amounts</Text>
                <Text style={{ color: theme.colors.textSecondary }}>${Number(amount || 0).toFixed(2)}</Text>
              </View>
              <FlatList
                data={rows}
                keyExtractor={(i) => i.id}
                renderItem={({ item }) => (
                  <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 12 }}>
                    <Pressable onPress={() => toggleMember(item.id)} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}>
                      <Avatar name={item.name} color={item.avatarColor} size={48} />
                    </Pressable>
                    <View style={{ marginLeft: 12, flex: 1 }}>
                      <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{item.name}{!item.included ? ' (excluded)' : ''}</Text>
                    </View>
                    <TextInput
                      keyboardType="numeric"
                      value={item.amount}
                      onChangeText={(v) => updateMemberAmount(item.id, v)}
                      style={{ width: 120, height: 48, borderRadius: 12, borderWidth: 1, borderColor: theme.colors.border, backgroundColor: theme.colors.surface, paddingHorizontal: 12, color: theme.colors.textPrimary }}
                    />
                  </View>
                )}
              />
            </View>
          )}

          <View style={{ height: 12 }} />
          <View style={{ flexDirection: 'row' }}>
            <Button label="Cancel" variant="secondary" onPress={() => router.back()} style={{ flex: 1, marginRight: 8 }} />
            <Button label="Add" onPress={save} style={{ flex: 1 }} />
          </View>
        </View>
        <KeyboardAccessory id={accessoryId} onDone={() => {}} />
      </KeyboardAvoidingView>
    </Screen>
  );
}


