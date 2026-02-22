/**
 * File: src/components/create-trip/steps/DetailsStep.tsx
 * Purpose: First page of the Create Trip wizard. Combines Trip Name, Destinations, Start/End Date,
 *          and Goal Budget / Person ($). No placeholder value inside the input. Provides Next action.
 */
import React from 'react';
import { View, Text } from 'react-native';
import { TextField } from '../../../components/TextField';
import { DateField } from '../../../components/DateField';
import { Button } from '../../../components/Button';
import { useTheme } from '../../../theme/ThemeProvider';

type Props = {
  name: string;
  onName: (v: string) => void;
  destination: string;
  onDestination: (v: string) => void;
  startDate: string;
  onStartDate: (v: string) => void;
  endDate: string;
  onEndDate: (v: string) => void;
  goalPerPerson: string;
  onGoalPerPerson: (v: string) => void;
  error?: string;
  onNext: () => void;
};

export function DetailsStep({ name, onName, destination, onDestination, startDate, onStartDate, endDate, onEndDate, goalPerPerson, onGoalPerPerson, error, onNext }: Props) {
  const theme = useTheme();
  return (
    <View>
      <TextField label="Trip Name" placeholder="Trip name" value={name} onChangeText={onName} />
      <TextField label="Destination(s)" placeholder="City, Country" value={destination} onChangeText={onDestination} />
      <DateField label="Start Date" placeholder="MM-DD-YYYY" value={startDate} onChangeText={onStartDate} />
      <DateField label="End Date" placeholder="MM-DD-YYYY" value={endDate} onChangeText={onEndDate} />
      <TextField label="Goal Budget / Person ($)" placeholder="" keyboardType="numeric" value={goalPerPerson} onChangeText={onGoalPerPerson} />
      {error ? <Text style={{ color: '#EF4444', marginBottom: 8 }}>{error}</Text> : null}
      <Button label="Next" onPress={onNext} />
    </View>
  );
}


