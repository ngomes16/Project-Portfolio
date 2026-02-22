/**
 * File: src/services/firestore/seeds.ts
 * Purpose: Developer utility to seed Firestore with the existing sample trips
 *          (including itinerary items as events and expenses) for the logged-in user.
 * Update: Set destination/start/end fields; guard demo mode via tripsCollection()
 */
import { trips as sampleTrips } from '../../data/sample';
import { createTrip, addEvent, addExpense, addTripMember } from './trips';
import { Timestamp } from 'firebase/firestore';

function toTimestamp(iso?: string) {
  if (!iso) return undefined as any;
  try {
    const d = new Date(iso);
    // @ts-ignore - on RN web we can pass Date directly; Firestore SDK will coerce
    return d as any;
  } catch {
    return undefined as any;
  }
}

export async function seedSampleTripsForUser(ownerId: string) {
  for (const trip of sampleTrips) {
    const tripId = await createTrip({ ownerId, name: trip.name, currency: 'USD', destination: trip.destination, startDate: toTimestamp(trip.startDate), endDate: toTimestamp(trip.endDate), settings: { budgetTarget: trip.goalBudget ?? null } });
    // members
    for (const m of trip.members) {
      await addTripMember(tripId, { uid: m.id, role: m.id === '1' ? 'owner' : 'member', displayName: m.name, joinedAt: Timestamp.now() as any });
    }
    // itinerary → events
    for (const it of trip.itinerary) {
      await addEvent(tripId, {
        title: it.label,
        notes: undefined,
        start: toTimestamp(it.startAt) ?? (new Date() as any),
        end: undefined,
        location: undefined,
        costLinkExpenseId: null,
        createdBy: ownerId,
        category: it.category,
        budgetTotal: it.total,
      });
    }
    // expenses
    for (const ex of trip.expenses || []) {
      await addExpense(tripId, {
        title: ex.label,
        notes: undefined,
        amount: ex.amount,
        currency: 'USD',
        date: toTimestamp(ex.createdAt) ?? (new Date() as any),
        category: undefined,
        payers: [{ uid: ex.paidBy, amount: ex.amount }],
        split: { type: 'custom', participants: ex.splitWith, shares: ex.breakdown ?? {} },
        createdBy: ownerId,
        eventId: ex.itemId ?? null,
      });
    }
  }
}


