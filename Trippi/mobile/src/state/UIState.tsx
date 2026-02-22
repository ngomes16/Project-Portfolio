/**
 * File: src/state/UIState.tsx
 * Purpose: Lightweight UI state store for preserving ephemeral view state across navigations
 *          (e.g., Trips tab search query and scroll offset). This helps restore the user's
 *          context when navigating back from detail screens.
 */
import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

type TripsTabState = {
  query: string;
  scrollOffset: number;
};

type UIStateValue = {
  tripsTab: TripsTabState;
  setTripsTabQuery: (q: string) => void;
  setTripsTabScroll: (offset: number) => void;
  resetTripsTab: () => void;
};

const UIStateContext = createContext<UIStateValue | null>(null);

export function UIStateProvider({ children }: { children: React.ReactNode }) {
  const [tripsTab, setTripsTab] = useState<TripsTabState>({ query: '', scrollOffset: 0 });

  const setTripsTabQuery = useCallback((q: string) => setTripsTab(prev => ({ ...prev, query: q })), []);
  const setTripsTabScroll = useCallback((offset: number) => setTripsTab(prev => ({ ...prev, scrollOffset: Math.max(0, offset) })), []);
  const resetTripsTab = useCallback(() => setTripsTab({ query: '', scrollOffset: 0 }), []);

  const value = useMemo(() => ({ tripsTab, setTripsTabQuery, setTripsTabScroll, resetTripsTab }), [tripsTab, setTripsTabQuery, setTripsTabScroll, resetTripsTab]);

  return <UIStateContext.Provider value={value}>{children}</UIStateContext.Provider>;
}

export function useUIState() {
  const ctx = useContext(UIStateContext);
  if (!ctx) throw new Error('useUIState must be used within UIStateProvider');
  return ctx;
}


