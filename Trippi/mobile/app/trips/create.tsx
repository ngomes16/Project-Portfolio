/**
 * File: app/trips/create.tsx
 * Purpose: Modern three-step Create Trip wizard flow (Details → Members → Review) with smooth transitions.
 *          Details step combines Name, Destinations, Dates, and Goal Budget / Person. Members step mirrors
 *          current members functionality and always includes the creator. Review step summarizes and creates.
 * Update: Removed segmented tabs in favor of a flow. Goal Budget field renamed to Goal Budget / Person ($)
 *         with no placeholder value shown. Added animated transitions and subcomponents for maintainability.
 *         Creation now uses TripsStore (which persists to Firestore when configured). Member search backed by Firestore.
 */
import React from 'react';
import { View, Text, KeyboardAvoidingView, Platform, ScrollView, Pressable } from 'react-native';
import { Screen } from '../../src/components/Screen';
import { useTheme } from '../../src/theme/ThemeProvider';
import { Button } from '../../src/components/Button';
import { useRouter } from 'expo-router';
import { useTrips } from '../../src/state/TripsStore';
import { isDemoMode } from '../../src/firebase';
import { searchUsersByUsernameOrEmail } from '../../src/services/firestore';
import { Header } from '../../src/components/Header';
import { WizardContainer } from '../../src/components/create-trip/WizardContainer';
import { StepIndicator } from '../../src/components/create-trip/StepIndicator';
import { DetailsStep } from '../../src/components/create-trip/steps/DetailsStep';
import { MembersStep } from '../../src/components/create-trip/steps/MembersStep';
import { ReviewStep } from '../../src/components/create-trip/steps/ReviewStep';

export default function CreateTrip() {
  const theme = useTheme();
  const router = useRouter();
  const steps = ['Details', 'Members', 'Review'] as const;
  const [stepIndex, setStepIndex] = React.useState(0);
  const [name, setName] = React.useState('');
  const [destination, setDestination] = React.useState('');
  const [startDate, setStartDate] = React.useState('');
  const [endDate, setEndDate] = React.useState('');
  const [goalPerPerson, setGoalPerPerson] = React.useState('');
  const { createTrip } = useTrips();
  const [error, setError] = React.useState<string>('');
  const [search, setSearch] = React.useState('');
  const [searchResults, setSearchResults] = React.useState<{ id: string; username: string; name: string; avatarColor: string }[]>([]);
  const [selectedMembers, setSelectedMembers] = React.useState<{ id: string; name: string; avatarColor: string }[]>([{ id: '1', name: 'You', avatarColor: '#7C5CFF' }]);
  const [searching, setSearching] = React.useState(false);

  return (
    <Screen>
      <KeyboardAvoidingView behavior={Platform.select({ ios: 'padding', android: undefined })} style={{ flex: 1 }}>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ paddingBottom: 32 }}>
          <Header title="Create a Trip" left={<Header.Back onPress={() => router.back()} />} />
          <View style={{ height: 12 }} />
          <StepIndicator steps={[...steps]} currentIndex={stepIndex} />
          <View style={{ height: 16 }} />
          <WizardContainer index={stepIndex}>
            {/* Details */}
            <View>
              <DetailsStep
                name={name}
                onName={setName}
                destination={destination}
                onDestination={setDestination}
                startDate={startDate}
                onStartDate={setStartDate}
                endDate={endDate}
                onEndDate={setEndDate}
                goalPerPerson={goalPerPerson}
                onGoalPerPerson={setGoalPerPerson}
                error={error}
                onNext={() => { if (!name.trim()) { setError('Trip name is required'); return; } setError(''); setStepIndex(1); }}
              />
            </View>
            {/* Members */}
            <View>
              <MembersStep
                selectedMembers={selectedMembers}
                onAdd={(u) => { if (!selectedMembers.some(m => m.id === u.id)) setSelectedMembers(prev => [...prev, { id: u.id, name: u.name, avatarColor: u.avatarColor }]); }}
                onRemove={(id) => { if (id === '1') return; setSelectedMembers(prev => prev.filter(m => m.id !== id)); }}
                search={search}
                onSearch={async (v) => {
                  setSearch(v);
                  if (!v.trim()) { setSearchResults([]); return; }
                  if (isDemoMode) { setSearchResults([{ id: '1', username: 'you', name: 'You', avatarColor: '#7C5CFF' }, { id: '2', username: 'nate', name: 'Nate', avatarColor: '#22C55E' }]); return; }
                  setSearching(true);
                  try {
                    const results = await searchUsersByUsernameOrEmail(v.trim().toLowerCase());
                    const mapped = results.map(r => ({ id: r.id, username: (r as any).username || (r as any).email || 'user', name: r.displayName || r.name || r.email || 'User', avatarColor: '#7C5CFF' }));
                    setSearchResults(mapped);
                  } finally {
                    setSearching(false);
                  }
                }}
                results={searchResults}
                searching={searching}
                onPrev={() => setStepIndex(0)}
                onNext={() => setStepIndex(2)}
              />
            </View>
            {/* Review */}
            <View>
              <ReviewStep
                name={name}
                destination={destination}
                startDate={startDate}
                endDate={endDate}
                goalPerPerson={goalPerPerson}
                members={selectedMembers}
                onPrev={() => setStepIndex(1)}
                onCreate={async () => {
                  if (!name.trim()) { setStepIndex(0); setError('Trip name is required'); return; }
                  const toIso = (mmddyyyy: string) => {
                    const [mm, dd, yyyy] = mmddyyyy.split('-');
                    if (!mm || !dd || !yyyy) return undefined;
                    return new Date(Number(yyyy), Number(mm) - 1, Number(dd)).toISOString();
                  };
                  const startIso = startDate ? toIso(startDate) : undefined;
                  const endIso = endDate ? toIso(endDate) : undefined;
                  const memberList = selectedMembers.length > 0 ? selectedMembers : [ { id: '1', name: 'You', avatarColor: '#7C5CFF' } ];
                  const totalGoal = goalPerPerson && memberList.length > 0 ? Number(goalPerPerson) * memberList.length : undefined;
                  const range = startIso && endIso ? `${new Date(startIso).toLocaleDateString()} - ${new Date(endIso).toLocaleDateString()}` : 'TBD';
                  const newTrip = createTrip({ name: name.trim(), destination: destination.trim() || 'TBD', dateRange: range, startDate: startIso, endDate: endIso, goalBudget: totalGoal, members: memberList });
                  router.replace({ pathname: '/trip/[id]', params: { id: newTrip.id } });
                }}
              />
            </View>
          </WizardContainer>
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}


