/**
 * File: src/components/login/PasswordRequirement.tsx
 * Purpose: Display a single password requirement with a check indicator, used on the signup form.
 */
import React from 'react';
import { Text } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';

type Props = { met: boolean; label: string };

export function PasswordRequirement({ met, label }: Props) {
  const theme = useTheme();
  return (
    <Text style={{ color: met ? theme.colors.positive : theme.colors.textSecondary }}>
      {met ? '✓' : '○'} {label}
    </Text>
  );
}


