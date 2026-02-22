/**
 * File: src/state/TripsStore.tsx
 * Purpose: Centralized state for trips, selection, and mutations (create trip, select, add member/item, add contribution, add expense, edit itinerary item).
 * Update: If Firestore is configured, loads trips for current user (owner or member) and persists create/mutations to subcollections.
 *         Added deleteTrip action; added persistence for addMember; createTrip now persists members and owner membership.
 */
import React, { createContext, useContext, useMemo, useState, useCallback } from 'react';
import { trips as initialTrips, Trip, TripMember, BudgetItem, Contribution, Expense } from '../data/sample';
import { isDemoMode } from '../firebase';
import { createTrip as fsCreateTrip, listenToTripsForUser, listenToEvents as fsListenEvents, listenToExpenses as fsListenExpenses, addTripMember as fsAddTripMember, deleteTrip as fsDeleteTrip, listTripMembers as fsListTripMembers, removeTripMember as fsRemoveTripMember } from '../services/firestore';
import { useAuth } from './AuthContext';

export type TripsState = {
  trips: Trip[];
  selectedTripId?: string;
  selectTrip: (tripId: string) => void;
  createTrip: (trip: Pick<Trip, 'name' | 'destination' | 'dateRange'> & { goalBudget?: number; startDate?: string; endDate?: string; members?: TripMember[]; itinerary?: BudgetItem[] }) => Trip;
  addMember: (tripId: string, member: TripMember) => void;
  removeMember: (tripId: string, uid: string) => void;
  addItineraryItem: (tripId: string, item: BudgetItem) => void;
  addContribution: (tripId: string, contribution: Contribution) => void;
  addExpense: (tripId: string, expense: Expense) => void;
  editItineraryItem: (tripId: string, item: Partial<BudgetItem> & { id: string }) => void;
  deleteTrip: (tripId: string) => void;
};

const TripsContext = createContext<TripsState | null>(null);

export function useTrips() {
  const ctx = useContext(TripsContext);
  if (!ctx) throw new Error('useTrips must be used within TripsProvider');
  return ctx;
}

export function TripsProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [trips, setTrips] = useState<Trip[]>(initialTrips);
  const [selectedTripId, setSelectedTripId] = useState<string | undefined>(trips[0]?.id);

  // Load trips from Firestore for the logged-in user
  React.useEffect(() => {
    if (isDemoMode || !user) return;
    const unsub = listenToTripsForUser(user.uid, (fsTrips) => {
      // Map Firestore trips to local Trip model minimally for now
      const mapped: Trip[] = fsTrips.map(t => ({
        id: t.id,
        name: t.name,
        destination: (t as any).destination || 'TBD',
        dateRange: '',
        startDate: (t as any).startDate ? ((t as any).startDate.toDate ? (t as any).startDate.toDate().toISOString().slice(0,10) : (t as any).startDate) : undefined,
        endDate: (t as any).endDate ? ((t as any).endDate.toDate ? (t as any).endDate.toDate().toISOString().slice(0,10) : (t as any).endDate) : undefined,
        goalBudget: (t.settings?.budgetTarget ?? undefined) as any,
        members: [],
        itinerary: [],
        contributions: [],
        expenses: [],
      }));
      setTrips(mapped);
      setSelectedTripId(mapped[0]?.id);
    });
    return () => unsub();
  }, [user]);

  // When a trip is selected, subscribe to its events and expenses to hydrate the UI
  React.useEffect(() => {
    if (isDemoMode || !user || !selectedTripId) return;
    const unsubEvents = fsListenEvents(selectedTripId, (events) => {
      setTrips(prev => prev.map(t => t.id !== selectedTripId ? t : ({
        ...t,
        itinerary: events.map(ev => ({
          id: ev.id,
          label: ev.title,
          total: ev.budgetTotal ?? 0,
          category: (ev.category as any) ?? 'Other',
          startAt: ev.start ? new Date((ev.start as any).toDate ? (ev.start as any).toDate() : ev.start).toISOString() : undefined,
        }))
      })));
    });
    const unsubExpenses = fsListenExpenses(selectedTripId, (expenses) => {
      setTrips(prev => prev.map(t => t.id !== selectedTripId ? t : ({
        ...t,
        expenses: expenses.map(ex => ({
          id: ex.id,
          itemId: ex.eventId ?? undefined,
          label: ex.title,
          amount: ex.amount,
          paidBy: ex.payers?.[0]?.uid ?? '1',
          splitWith: ex.split?.participants ?? [],
          createdAt: ex.date ? new Date((ex.date as any).toDate ? (ex.date as any).toDate() : ex.date).toISOString() : new Date().toISOString(),
          breakdown: (ex.split?.shares as any) ?? undefined,
        }))
      })));
    });
    // Fetch members once for display
    fsListTripMembers(selectedTripId).then((members) => {
      setTrips(prev => prev.map(t => t.id !== selectedTripId ? t : ({
        ...t,
        members: members.map(m => ({ id: m.uid, name: m.displayName, avatarColor: '#7C5CFF' })),
      })));
    }).catch(() => {});
    return () => { unsubEvents(); unsubExpenses(); };
  }, [user, selectedTripId]);

  const selectTrip = useCallback((tripId: string) => setSelectedTripId(tripId), []);

  const createTrip: TripsState['createTrip'] = useCallback((input) => {
    const localId = Math.random().toString(36).slice(2);
    const newTrip: Trip = {
      id: localId,
      name: input.name,
      destination: input.destination,
      dateRange: input.dateRange,
      goalBudget: input.goalBudget,
      startDate: input.startDate,
      endDate: input.endDate,
      members: input.members ?? [],
      itinerary: input.itinerary ?? [],
    };
    setTrips(prev => [newTrip, ...prev]);
    setSelectedTripId(newTrip.id);
    if (!isDemoMode && user) {
      // Persist to Firestore and replace local provisional id with Firestore id when available
      fsCreateTrip({ ownerId: user.uid, name: input.name, currency: 'USD', settings: { budgetTarget: input.goalBudget ?? null }, destination: input.destination, startDate: input.startDate, endDate: input.endDate })
        .then(async (fsId) => {
          // Swap local id with Firestore id
          setTrips(prev => prev.map(t => t.id === localId ? { ...t, id: fsId, members: (t.members || []).map(m => m.id === '1' && user ? { ...m, id: user.uid, name: user.displayName || m.name } : m) } : t));
          setSelectedTripId(fsId);
          // Persist owner membership and selected members
          try {
            await fsAddTripMember(fsId, { uid: user.uid, role: 'owner', displayName: user.displayName || 'You', joinedAt: undefined as any });
          } catch {}
          const fsMembers = (input.members || []).filter(m => m.id !== '1');
          for (const m of fsMembers) {
            try {
              await fsAddTripMember(fsId, { uid: m.id, role: 'member', displayName: m.name, joinedAt: undefined as any });
            } catch {}
          }
        })
        .catch(() => {});
    }
    return newTrip;
  }, []);

  const addMember: TripsState['addMember'] = useCallback((tripId, member) => {
    setTrips(prev => prev.map(t => t.id === tripId ? { ...t, members: [ ...t.members, member ] } : t));
    if (!isDemoMode && user) {
      fsAddTripMember(tripId, { uid: member.id, role: 'member', displayName: member.name, joinedAt: undefined as any }).catch(() => {});
    }
  }, [user]);

  const removeMember: TripsState['removeMember'] = useCallback((tripId, uid) => {
    setTrips(prev => prev.map(t => t.id === tripId ? { ...t, members: t.members.filter(m => m.id !== uid) } : t));
    if (!isDemoMode && user) {
      fsRemoveTripMember(tripId, uid).catch(() => {});
    }
  }, [user]);

  const addItineraryItem: TripsState['addItineraryItem'] = useCallback((tripId, item) => {
    setTrips(prev => prev.map(t => t.id === tripId ? { ...t, itinerary: [ ...t.itinerary, item ] } : t));
  }, []);

  const addContribution: TripsState['addContribution'] = useCallback((tripId, contribution) => {
    setTrips(prev => prev.map(t => t.id === tripId ? { ...t, contributions: [ ...(t.contributions ?? []), contribution ] } : t));
  }, []);

  const addExpense: TripsState['addExpense'] = useCallback((tripId, expense) => {
    setTrips(prev => prev.map(t => t.id === tripId ? { ...t, expenses: [ ...(t.expenses ?? []), expense ] } : t));
  }, []);

  const editItineraryItem: TripsState['editItineraryItem'] = useCallback((tripId, item) => {
    setTrips(prev => prev.map(t => {
      if (t.id !== tripId) return t;
      return { ...t, itinerary: t.itinerary.map(it => it.id === item.id ? { ...it, ...item } as BudgetItem : it) };
    }));
  }, []);

  const deleteTrip: TripsState['deleteTrip'] = useCallback((tripId) => {
    setTrips(prev => prev.filter(t => t.id !== tripId));
    setSelectedTripId(prev => (prev === tripId ? undefined : prev));
    if (!isDemoMode && user) {
      fsDeleteTrip(tripId).catch(() => {});
    }
  }, [user]);

  const value = useMemo(() => ({ trips, selectedTripId, selectTrip, createTrip, addMember, removeMember, addItineraryItem, addContribution, addExpense, editItineraryItem, deleteTrip }), [trips, selectedTripId, selectTrip, createTrip, addMember, removeMember, addItineraryItem, addContribution, addExpense, editItineraryItem, deleteTrip]);

  return <TripsContext.Provider value={value}>{children}</TripsContext.Provider>;
}


