/**
 * File: src/services/firestore/types.ts
 * Purpose: Centralized TypeScript types for Firestore documents used by the app.
 *          Mirrors the intended data model for users, trips, members, events, and expenses.
 * Update: Added optional `memberUids` on TripDoc to support membership queries and visibility
 *         for non-owners (users added as members will see trips on login).
 */

export type UserDoc = {
  uid: string;
  displayName: string | null;
  email: string | null;
  photoURL?: string | null;
  createdAt: any; // Firestore Timestamp
  currencyPref?: string | null;
  tripCount?: number;
};

export type TripSettings = {
  allowAllMembersEdit: boolean;
  defaultSplitType: 'equal' | 'weighted' | 'custom';
  timezone: string; // e.g., "America/Phoenix"
  budgetTarget: number | null;
};

export type TripDoc = {
  name: string;
  destination?: string;
  photoURL?: string | null;
  currency: string; // e.g., "USD"
  ownerId: string; // uid
  createdAt: any; // Firestore Timestamp
  updatedAt: any; // Firestore Timestamp
  settings: TripSettings;
  startDate?: any; // Firestore Timestamp
  endDate?: any; // Firestore Timestamp
  memberUids?: string[]; // uids of members (including owner) for fast membership queries
};

export type TripMemberRole = 'owner' | 'manager' | 'member' | 'viewer';
export type TripMemberDoc = {
  uid: string; // duplicate uid for querying
  role: TripMemberRole;
  displayName: string;
  joinedAt: any; // Firestore Timestamp
};

export type TripInviteStatus = 'pending' | 'accepted' | 'revoked' | 'expired';
export type TripInviteDoc = {
  email: string;
  invitedBy: string; // uid
  role: Exclude<TripMemberRole, 'owner'>;
  status: TripInviteStatus;
  tokenHash: string;
  createdAt: any; // Firestore Timestamp
  expiresAt: any; // Firestore Timestamp
};

export type GeoPointLike = { name?: string; lat: number; lng: number };

export type TripEventDoc = {
  title: string;
  notes?: string;
  start: any; // Firestore Timestamp
  end?: any; // Firestore Timestamp
  location?: GeoPointLike;
  costLinkExpenseId?: string | null;
  createdBy: string; // uid
  createdAt: any; // Firestore Timestamp
  updatedAt: any; // Firestore Timestamp
  category?: 'Lodging' | 'Flights' | 'Transport' | 'Food' | 'Activities' | 'Other' | string;
  budgetTotal?: number; // in major units for now
};

export type TripExpenseSplit = {
  type: 'equal' | 'weighted' | 'custom';
  weights?: Record<string, number>;
  shares?: Record<string, number>;
  participants: string[]; // uids
};

export type TripExpenseDoc = {
  title: string;
  notes?: string;
  amount: number; // major units for now
  currency: string; // usually trip.currency
  date: any; // Firestore Timestamp
  category?: string;
  payers: { uid: string; amount: number }[];
  split: TripExpenseSplit;
  createdBy: string; // uid
  createdAt: any; // Firestore Timestamp
  updatedAt: any; // Firestore Timestamp
  eventId?: string | null;
};

export type TripBalanceDoc = { balance: number };


