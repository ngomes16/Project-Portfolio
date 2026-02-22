/**
 * File: src/services/firestore/users.ts
 * Purpose: Firestore user document helpers: create/update user profile, fetch by uid,
 *          and search by username or email for inviting members.
 */
import { doc, getDoc, serverTimestamp, setDoc, collection, getDocs, query, where, limit } from 'firebase/firestore';
import { db, isDemoMode } from '../../firebase';
import type { UserDoc } from './types';

export async function upsertUserProfile(params: { uid: string; displayName: string | null; email: string | null; photoURL?: string | null }) {
  if (!db || isDemoMode) return;
  const ref = doc(db, 'users', params.uid);
  const data: Partial<UserDoc> = {
    uid: params.uid,
    displayName: params.displayName ?? null,
    email: params.email ?? null,
    photoURL: params.photoURL ?? null,
    createdAt: serverTimestamp(),
    currencyPref: null,
    tripCount: 0,
  };
  await setDoc(ref, data, { merge: true });
}

export async function getUserProfile(uid: string): Promise<UserDoc | null> {
  if (!db || isDemoMode) return null;
  const snap = await getDoc(doc(db, 'users', uid));
  return snap.exists() ? (snap.data() as UserDoc) : null;
}

export async function searchUsersByUsernameOrEmail(qs: string, max: number = 8): Promise<Array<{ id: string; username?: string; name?: string; email?: string; displayName?: string }>> {
  if (!db || isDemoMode) return [];
  const usersCol = collection(db, 'users');
  const queries = [
    query(usersCol, where('username', '>=', qs), where('username', '<=', qs + '\uf8ff'), limit(max)),
    query(usersCol, where('email', '>=', qs), where('email', '<=', qs + '\uf8ff'), limit(max)),
  ];
  const results: Record<string, any> = {};
  for (const qy of queries) {
    const snap = await getDocs(qy);
    for (const d of snap.docs) results[d.id] = { id: d.id, ...(d.data() as any) };
  }
  return Object.values(results).slice(0, max);
}


