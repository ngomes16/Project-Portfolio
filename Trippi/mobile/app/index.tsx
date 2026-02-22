/**
 * File: app/index.tsx
 * Purpose: Index route. Immediately redirects to `/login` to ensure a consistent entry point in Expo Go.
 */
import { Redirect } from 'expo-router';

export default function RootIndex() {
  return <Redirect href="/login" />;
}


