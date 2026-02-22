/**
 * File: src/components/Card.tsx
 * Purpose: Surface container with rounded corners and shadow, used to group content.
 */
import React from 'react';
import { View, StyleSheet, ViewProps } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type Props = ViewProps & { children: React.ReactNode };

export function Card({ style, children, ...rest }: Props) {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.base,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
        },
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 16,
  },
});


