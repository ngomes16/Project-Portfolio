/**
 * File: app/_layout.tsx
 * Purpose: Root stack layout for expo-router. Hosts login and the tabs group.
 * Update: Wrapped app with BudgetProvider to support Budget dashboard (flex budget and transactions).
 */
import React, { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { useFonts, Inter_400Regular, Inter_600SemiBold } from '@expo-google-fonts/inter';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import { TripsProvider } from '../src/state/TripsStore';
import { AuthProvider, useAuth } from '../src/state/AuthContext';
import { UIStateProvider } from '../src/state/UIState';
import { BudgetProvider } from '../src/state/BudgetState';

function RootLayoutNav() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    if (loading) return;

    const onLoginPage = segments[0] === 'login';

    // If the user is signed in and the current route is not in the tabs group, redirect them to the tabs group.
    if (user && onLoginPage) {
      router.replace('/(tabs)');
    } 
    // If the user is not signed in and the current route is not the login page, redirect them to the login page.
    else if (!user && !onLoginPage) {
      router.replace('/login');
    }
  }, [user, loading, segments, router]);

  // Avoid rendering any navigation until auth state has resolved
  if (loading) {
    return null;
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="login" />
      <Stack.Screen name="(tabs)" />
    </Stack>
  );
}

export default function RootLayout() {
  const [loaded] = useFonts({ Inter_400Regular, Inter_600SemiBold });
  if (!loaded) return null;

  return (
    <ThemeProvider>
      <AuthProvider>
        <TripsProvider>
          <UIStateProvider>
            <BudgetProvider>
              <RootLayoutNav />
            </BudgetProvider>
          </UIStateProvider>
        </TripsProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}


