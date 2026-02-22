/**
 * File: src/components/TextField.tsx
 * Purpose: Styled text input with label and placeholder for forms.
 * Update: Supports iOS inputAccessoryViewID for keyboard navigation bar.
 */
import React from 'react';
import { View, Text, TextInput, StyleSheet, TextInputProps } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type Props = TextInputProps & { label?: string };

export const TextField = React.forwardRef<TextInput, Props>(({ label, style, ...rest }, ref) => {
  const theme = useTheme();
  return (
    <View style={{ marginBottom: 12 }}>
      {label ? <Text style={{ color: theme.colors.textSecondary, marginBottom: 6 }}>{label}</Text> : null}
      <TextInput
        ref={ref}
        placeholderTextColor={theme.colors.textSecondary}
        style={[styles.input, { color: theme.colors.textPrimary, borderColor: theme.colors.border, backgroundColor: theme.colors.surface }, style]}
        {...rest}
      />
    </View>
  );
});

const styles = StyleSheet.create({
  input: {
    height: 48,
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 12,
  },
});


