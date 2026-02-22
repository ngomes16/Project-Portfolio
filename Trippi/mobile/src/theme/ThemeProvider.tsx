/**
 * File: src/theme/ThemeProvider.tsx
 * Purpose: App-wide theming (colors, spacing, typography) via React context and styled primitives.
 */
import React, { createContext, useContext } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

export type Theme = {
  colors: {
    background: string;
    surface: string;
    primary: string;
    textPrimary: string;
    textSecondary: string;
    border: string;
    positive: string;
    warning: string;
  };
  spacing: (multiplier?: number) => number;
  radius: {
    sm: number;
    md: number;
    lg: number;
    xl: number;
  };
};

const defaultTheme: Theme = {
  colors: {
    // Modern bright theme with subtle contrast between background and surfaces
    background: '#FFFFFF',   // app background
    surface: '#FAFAFA',      // slightly off-white so cards stand out on white
    primary: '#7C5CFF',      // light purple accent
    textPrimary: '#0F172A',  // slate-900
    textSecondary: '#475569',// slate-600
    border: '#EAEAEA',       // very light neutral border
    positive: '#10B981',     // emerald-500
    warning: '#F59E0B',      // amber-500
  },
  spacing: (m: number = 1) => 8 * m,
  radius: { sm: 8, md: 12, lg: 16, xl: 24 },
};

const ThemeContext = createContext<Theme>(defaultTheme);

export function useTheme() {
  return useContext(ThemeContext);
}

type Props = { children: React.ReactNode };

export function ThemeProvider({ children }: Props) {
  return (
    <ThemeContext.Provider value={defaultTheme}>
      <SafeAreaProvider>
        <StatusBar style="dark" />
        {children}
      </SafeAreaProvider>
    </ThemeContext.Provider>
  );
}


