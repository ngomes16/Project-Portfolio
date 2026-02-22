/**
 * File: app/profile.tsx
 * Purpose: Modern profile screen with richer insights, quick actions, preferences, and secure account controls.
 * Update: Removed legacy developer tools (sample data seeding) to streamline the user experience.
 */
import React from 'react';
import { View, Text, StyleSheet, Switch, Modal, Pressable } from 'react-native';
import { useTheme } from '../src/theme/ThemeProvider';
import { Card } from '../src/components/Card';
import { Screen } from '../src/components/Screen';
import { Avatar } from '../src/components/Avatar';
import { ListItem } from '../src/components/ListItem';
import { ProgressBar } from '../src/components/ProgressBar';
import { useTrips } from '../src/state/TripsStore';
import { useAuth } from '../src/state/AuthContext';
import { computeBalances } from '../src/utils/balances';
import { Button } from '../src/components/Button';
import { formatCurrency } from '../src/utils/format';

export default function ProfileScreen() {
  const theme = useTheme();
  const { signOut, user } = useAuth();
  const [confirmVisible, setConfirmVisible] = React.useState(false);
  const [notifications, setNotifications] = React.useState(true);
  const { trips, selectedTripId } = useTrips();
  const current = trips.find(t => t.id === selectedTripId) || trips[0];
  const balances = current ? computeBalances(current) : [];
  return (
    <Screen scroll>
      <Text style={[styles.title, { color: theme.colors.textPrimary }]}>Profile</Text>
      <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>Manage preferences, payments, and privacy settings.</Text>

      <Card style={{ marginTop: 16 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <Avatar name={user?.displayName || 'You'} size={56} />
          <View style={{ marginLeft: 12, flex: 1 }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '700', fontSize: 16 }}>{user?.displayName || 'You'}</Text>
            <Text style={{ color: theme.colors.textSecondary }}>{user?.email || 'Guest'}</Text>
          </View>
          <Button label="Edit" variant="secondary" onPress={() => {}} />
        </View>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <Text style={{ color: theme.colors.textPrimary, fontWeight: '700' }}>Payment & Balances</Text>
        {current ? (
          <>
            <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>{current.name}</Text>
            {balances.map(b => (
              <View key={b.memberId} style={{ borderTopWidth: 1, borderTopColor: theme.colors.border, paddingTop: 8, marginTop: 8 }}>
                <Text style={{ color: theme.colors.textPrimary, fontWeight: '600' }}>{b.name}</Text>
                <Text style={{ color: b.balance >= 0 ? theme.colors.positive : '#EF4444' }}>{b.balance >= 0 ? `Should receive ${formatCurrency(b.balance)}` : `Owes ${formatCurrency(Math.abs(b.balance))}`}</Text>
              </View>
            ))}
          </>
        ) : (
          <Text style={{ color: theme.colors.textSecondary, marginTop: 4 }}>No trip selected.</Text>
        )}
      </Card>

      <Card style={{ marginTop: 16 }}>
        <ListItem title="Notifications" right={<Switch value={notifications} onValueChange={setNotifications} />} />
        <ListItem title="Payment methods" subtitle="Manage cards for contributions" onPress={() => {}} />
        <ListItem title="Default split" subtitle="Evenly" onPress={() => {}} />
        <ListItem title="Currency" subtitle="USD" onPress={() => {}} />
        <ListItem title="Security" subtitle="Password and 2FA" onPress={() => {}} />
      </Card>

      {/* Developer tools removed */}

      <View style={{ height: 24 }} />
      <Button label="Log out" variant="gradient" onPress={() => setConfirmVisible(true)} />

      <Modal transparent visible={confirmVisible} onRequestClose={() => setConfirmVisible(false)}>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', alignItems: 'center', justifyContent: 'center' }}>
          <View style={{ backgroundColor: theme.colors.surface, borderRadius: 16, borderWidth: 1, borderColor: theme.colors.border, padding: 18, width: '86%' }}>
            <Text style={{ color: theme.colors.textPrimary, fontWeight: '700', fontSize: 18 }}>Are you sure you want to log out?</Text>
            <Text style={{ color: theme.colors.textSecondary, marginTop: 8 }}>You’ll need to sign in again to access your trips.</Text>
            <View style={{ height: 14 }} />
            <Button label="Log out" onPress={() => { setConfirmVisible(false); setTimeout(signOut, 50); }} />
            <View style={{ height: 8 }} />
            <Button label="Cancel" variant="secondary" onPress={() => setConfirmVisible(false)} />
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  title: { fontSize: 22, fontWeight: '700' },
});


