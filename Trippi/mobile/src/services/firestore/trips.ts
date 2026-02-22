/**
 * File: src/services/firestore/trips.ts
 * Purpose: Firestore helpers for trips, members, events, and expenses. Encapsulates
 *          read/write logic and shapes data according to the app's model.
 * Update: Added deleteTrip (with subcollection cleanup), membership-aware listeners,
 *         and memberUids maintenance via arrayUnion on addTripMember.
 */
import { addDoc, arrayUnion, arrayRemove, collection, deleteDoc, doc, getDoc, getDocs, limit, onSnapshot, orderBy, query, serverTimestamp, setDoc, updateDoc, where } from 'firebase/firestore';
import { db, isDemoMode } from '../../firebase';
import type { TripDoc, TripMemberDoc, TripEventDoc, TripExpenseDoc } from './types';

export function tripsCollection() {
  if (!db || isDemoMode) throw new Error('Firestore not configured');
  return collection(db, 'trips');
}

function omitUndefined<T extends Record<string, any>>(obj: T): T {
  const out: any = {};
  for (const k of Object.keys(obj)) {
    const v = (obj as any)[k];
    if (v !== undefined) out[k] = v;
  }
  return out as T;
}

export async function createTrip(params: { ownerId: string; name: string; currency?: string; settings?: Partial<TripDoc['settings']>; photoURL?: string | null; destination?: string | null; startDate?: any; endDate?: any; }): Promise<string> {
  const col = tripsCollection();
  const base: Partial<TripDoc> = {
    name: params.name,
    photoURL: params.photoURL ?? null,
    currency: params.currency ?? 'USD',
    ownerId: params.ownerId,
    createdAt: serverTimestamp() as any,
    updatedAt: serverTimestamp() as any,
    destination: params.destination ?? undefined,
    startDate: params.startDate ?? undefined,
    endDate: params.endDate ?? undefined,
    settings: {
      allowAllMembersEdit: true,
      defaultSplitType: 'equal',
      timezone: 'UTC',
      budgetTarget: null,
      ...(params.settings ?? {}),
    },
    memberUids: [params.ownerId],
  };
  const docRef = await addDoc(col, omitUndefined(base) as TripDoc);
  return docRef.id;
}

export async function getTrip(tripId: string): Promise<TripDoc & { id: string } | null> {
  const col = tripsCollection();
  const snap = await getDoc(doc(col, tripId));
  if (!snap.exists()) return null;
  return { id: snap.id, ...(snap.data() as TripDoc) };
}

export function listenToTripsForUser(uid: string, cb: (trips: Array<{ id: string } & TripDoc>) => void) {
  const col = tripsCollection();
  // Listen to trips owned by user
  const ownerQ = query(col, where('ownerId', '==', uid));
  // And trips where user is a member
  const memberQ = query(col, where('memberUids', 'array-contains', uid));

  let ownerRows: Array<{ id: string } & TripDoc> = [];
  let memberRows: Array<{ id: string } & TripDoc> = [];

  function emit() {
    const map: Record<string, any> = {};
    for (const r of ownerRows) map[r.id] = r;
    for (const r of memberRows) map[r.id] = r;
    const rows = Object.values(map) as Array<{ id: string } & TripDoc>;
    rows.sort((a: any, b: any) => {
      const aTs = (a.createdAt && (a.createdAt.toMillis ? a.createdAt.toMillis() : Date.parse(a.createdAt))) || 0;
      const bTs = (b.createdAt && (b.createdAt.toMillis ? b.createdAt.toMillis() : Date.parse(b.createdAt))) || 0;
      return bTs - aTs;
    });
    cb(rows);
  }

  const handleError = (err: any) => {
    // Swallow common permission errors so they don't spam the dev console
    if (err?.code === 'permission-denied') return;
    console.error(err);
  };
  const unsubOwner = onSnapshot(ownerQ, (snap) => {
    ownerRows = snap.docs.map(d => ({ id: d.id, ...(d.data() as TripDoc) }));
    emit();
  }, handleError);
  const unsubMember = onSnapshot(memberQ, (snap) => {
    memberRows = snap.docs.map(d => ({ id: d.id, ...(d.data() as TripDoc) }));
    emit();
  }, handleError);

  return () => { unsubOwner(); unsubMember(); };
}

export async function addTripMember(tripId: string, member: TripMemberDoc) {
  const col = tripsCollection();
  const membersCol = collection(doc(col, tripId), 'members');
  await setDoc(doc(membersCol, member.uid), { ...member, joinedAt: serverTimestamp() }, { merge: true });
  // Maintain denormalized list of member UIDs on the trip for membership queries
  await updateDoc(doc(col, tripId), { memberUids: arrayUnion(member.uid), updatedAt: serverTimestamp() } as any);
}

export async function removeTripMember(tripId: string, uid: string) {
  const col = tripsCollection();
  const tripRef = doc(col, tripId);
  const membersCol = collection(tripRef, 'members');
  await deleteDoc(doc(membersCol, uid));
  await updateDoc(tripRef, { memberUids: arrayRemove(uid), updatedAt: serverTimestamp() } as any);
}

export async function listTripMembers(tripId: string): Promise<Array<{ id: string } & TripMemberDoc>> {
  const col = tripsCollection();
  const membersCol = collection(doc(col, tripId), 'members');
  const snap = await getDocs(membersCol);
  return snap.docs.map(d => ({ id: d.id, ...(d.data() as TripMemberDoc) }));
}

export async function addEvent(tripId: string, event: Omit<TripEventDoc, 'createdAt' | 'updatedAt'>): Promise<string> {
  const col = tripsCollection();
  const eventsCol = collection(doc(col, tripId), 'events');
  const payload = omitUndefined({ ...event, createdAt: serverTimestamp() as any, updatedAt: serverTimestamp() as any });
  const ref = await addDoc(eventsCol, payload);
  return ref.id;
}

export async function listEvents(tripId: string): Promise<Array<{ id: string } & TripEventDoc>> {
  const col = tripsCollection();
  const eventsCol = collection(doc(col, tripId), 'events');
  const snap = await getDocs(query(eventsCol, orderBy('start', 'asc')));
  return snap.docs.map(d => ({ id: d.id, ...(d.data() as TripEventDoc) }));
}

export function listenToEvents(tripId: string, cb: (events: Array<{ id: string } & TripEventDoc>) => void) {
  const col = tripsCollection();
  const eventsCol = collection(doc(col, tripId), 'events');
  const qy = query(eventsCol, orderBy('start', 'asc'));
  return onSnapshot(qy, (snap) => {
    cb(snap.docs.map(d => ({ id: d.id, ...(d.data() as TripEventDoc) })));
  }, (err: any) => { if (err?.code !== 'permission-denied') console.error(err); });
}

export async function updateEvent(tripId: string, eventId: string, updates: Partial<Omit<TripEventDoc, 'createdAt' | 'updatedAt'>>) {
  const col = tripsCollection();
  const ref = doc(collection(doc(col, tripId), 'events'), eventId);
  await updateDoc(ref, { ...updates, updatedAt: serverTimestamp() } as any);
}

export async function addExpense(tripId: string, expense: Omit<TripExpenseDoc, 'createdAt' | 'updatedAt'>): Promise<string> {
  const col = tripsCollection();
  const expensesCol = collection(doc(col, tripId), 'expenses');
  const payload = omitUndefined({ ...expense, createdAt: serverTimestamp() as any, updatedAt: serverTimestamp() as any });
  const ref = await addDoc(expensesCol, payload);
  return ref.id;
}

export async function listExpenses(tripId: string): Promise<Array<{ id: string } & TripExpenseDoc>> {
  const col = tripsCollection();
  const expensesCol = collection(doc(col, tripId), 'expenses');
  const snap = await getDocs(query(expensesCol, orderBy('date', 'desc'), limit(100)));
  return snap.docs.map(d => ({ id: d.id, ...(d.data() as TripExpenseDoc) }));
}

export function listenToExpenses(tripId: string, cb: (expenses: Array<{ id: string } & TripExpenseDoc>) => void) {
  const col = tripsCollection();
  const expensesCol = collection(doc(col, tripId), 'expenses');
  const qy = query(expensesCol, orderBy('date', 'desc'), limit(100));
  return onSnapshot(qy, (snap) => {
    cb(snap.docs.map(d => ({ id: d.id, ...(d.data() as TripExpenseDoc) })));
  }, (err: any) => { if (err?.code !== 'permission-denied') console.error(err); });
}

export async function listPopularTrips(): Promise<Array<{ id: string } & TripDoc>> {
  const col = tripsCollection();
  const snap = await getDocs(query(col, orderBy('createdAt', 'desc'), limit(8)));
  return snap.docs.map(d => ({ id: d.id, ...(d.data() as TripDoc) }));
}

export async function deleteTrip(tripId: string) {
  const col = tripsCollection();
  const tripRef = doc(col, tripId);
  // Delete subcollections: members, events, expenses
  const membersCol = collection(tripRef, 'members');
  const eventsCol = collection(tripRef, 'events');
  const expensesCol = collection(tripRef, 'expenses');
  const [membersSnap, eventsSnap, expensesSnap] = await Promise.all([
    getDocs(membersCol),
    getDocs(eventsCol),
    getDocs(expensesCol),
  ]);
  await Promise.all([
    ...membersSnap.docs.map(d => deleteDoc(d.ref)),
    ...eventsSnap.docs.map(d => deleteDoc(d.ref)),
    ...expensesSnap.docs.map(d => deleteDoc(d.ref)),
  ]);
  await deleteDoc(tripRef);
}


