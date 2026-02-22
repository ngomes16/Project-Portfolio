/**
 * File: src/data/sample.ts
 * Purpose: Sample mock data used to populate UI components for the MVP design.
 */
export type TripMember = { id: string; name: string; avatarColor: string };
export type BudgetCategory = 'Lodging' | 'Flights' | 'Transport' | 'Activities' | 'Food' | 'Other';
export type BudgetItem = { id: string; label: string; total: number; perPerson?: number; category: BudgetCategory; startAt?: string; endAt?: string };
export type Contribution = { id: string; memberId: string; amount: number; label: string; date?: string };
export type Expense = { id: string; itemId?: string; label: string; amount: number; paidBy: string; splitWith: string[]; createdAt: string; breakdown?: Record<string, number> };
export type Trip = {
  id: string;
  name: string;
  destination: string;
  dateRange: string;
  startDate?: string;
  endDate?: string;
  goalBudget?: number;
  members: TripMember[];
  itinerary: BudgetItem[];
  contributions?: Contribution[];
  expenses?: Expense[];
};

export const members: TripMember[] = [
  { id: '1', name: 'You', avatarColor: '#7C5CFF' },
  { id: '2', name: 'Nate', avatarColor: '#22C55E' },
  { id: '3', name: 'Ava', avatarColor: '#F59E0B' },
  { id: '4', name: 'Liam', avatarColor: '#0EA5E9' },
];

export const trips: Trip[] = [
  {
    id: 'chi',
    name: 'Chicago City Break',
    destination: 'Chicago, IL',
    dateRange: 'Sep 20 - Sep 25',
    startDate: '2025-09-20',
    endDate: '2025-09-25',
    goalBudget: 4200,
    members,
    itinerary: [
      // Day 0 travel & lodging
      { id: 'cb1', label: 'Hotel (Loop)', total: 1500, perPerson: 375, category: 'Lodging', startAt: '2025-09-20T16:00:00', endAt: '2025-09-25T11:00:00' },
      { id: 'cb2', label: 'Flights ORD Arrival', total: 1200, perPerson: 300, category: 'Flights', startAt: '2025-09-20T09:30:00', endAt: '2025-09-20T12:00:00' },
      { id: 'cb2a', label: 'CTA 3-Day Passes', total: 60, category: 'Transport', startAt: '2025-09-20T12:15:00' },
      { id: 'cb4', label: 'Welcome Dinner (Deep Dish)', total: 180, category: 'Food', startAt: '2025-09-20T18:30:00' },
      // Day 1
      { id: 'cb3', label: 'Architecture Boat Tour', total: 200, category: 'Activities', startAt: '2025-09-21T13:00:00', endAt: '2025-09-21T15:00:00' },
      { id: 'cb6', label: 'Millennium Park & The Bean', total: 0, category: 'Activities', startAt: '2025-09-21T10:00:00' },
      { id: 'cb7', label: 'Riverwalk Drinks', total: 120, category: 'Food', startAt: '2025-09-21T18:30:00' },
      // Day 2
      { id: 'cb8', label: 'Art Institute of Chicago', total: 120, category: 'Activities', startAt: '2025-09-22T11:00:00' },
      { id: 'cb9', label: 'West Loop Lunch', total: 100, category: 'Food', startAt: '2025-09-22T13:00:00' },
      { id: 'cb10', label: 'Skydeck Chicago', total: 160, category: 'Activities', startAt: '2025-09-22T17:00:00' },
      // Day 3
      { id: 'cb11', label: 'Museum of Science & Industry', total: 160, category: 'Activities', startAt: '2025-09-23T10:00:00' },
      { id: 'cb12', label: 'Coffee Crawl (West Loop)', total: 40, category: 'Food', startAt: '2025-09-23T15:00:00' },
      { id: 'cb13', label: 'Green Mill Jazz Club', total: 140, category: 'Activities', startAt: '2025-09-23T20:00:00' },
      // Day 4
      { id: 'cb14', label: 'Brunch in River North', total: 140, category: 'Food', startAt: '2025-09-24T10:00:00' },
      { id: 'cb15', label: 'Shopping on Magnificent Mile', total: 0, category: 'Activities', startAt: '2025-09-24T12:00:00' },
      { id: 'cb16', label: 'Depart ORD', total: 0, category: 'Transport', startAt: '2025-09-24T16:30:00' },
    ],
    contributions: [
      { id: 'c1', memberId: '1', amount: 400, label: 'Initial deposit', date: '2024-08-01' },
      { id: 'c2', memberId: '2', amount: 300, label: 'Flight share', date: '2024-08-05' },
    ],
    expenses: [
      { id: 'e1', itemId: 'cb4', label: 'Dinner bill', amount: 120, paidBy: '2', splitWith: ['1','2','3'], createdAt: '2025-09-20T20:00:00' },
    ],
  },
  {
    id: 't1',
    name: 'Beach Escape',
    destination: 'Cancún, MX',
    dateRange: 'Oct 02 - Oct 08',
    startDate: '2025-10-02',
    endDate: '2025-10-08',
    goalBudget: 3800,
    members,
    itinerary: [
      { id: 'b1', label: 'Airbnb', total: 1200, perPerson: 300, category: 'Lodging', startAt: '2025-10-02T16:00:00', endAt: '2025-10-08T11:00:00' },
      { id: 'b2', label: 'Flights', total: 1800, perPerson: 450, category: 'Flights', startAt: '2025-10-02T08:00:00' },
      { id: 'b3', label: 'Food & Drinks', total: 800, category: 'Food', startAt: '2025-10-03T19:30:00' },
    ],
    contributions: [ { id: 'c3', memberId: '3', amount: 250, label: 'Food kitty' } ],
    expenses: [],
  },
  {
    id: 't2',
    name: 'Ski Trip',
    destination: 'Aspen, CO',
    dateRange: 'Dec 05 - Dec 10',
    startDate: '2025-12-05',
    endDate: '2025-12-10',
    goalBudget: 5200,
    members,
    itinerary: [
      { id: 'b4', label: 'Cabin', total: 1600, perPerson: 400, category: 'Lodging', startAt: '2025-12-05T16:00:00', endAt: '2025-12-10T11:00:00' },
      { id: 'b5', label: 'Lift Passes', total: 1000, perPerson: 250, category: 'Activities', startAt: '2025-12-06T09:00:00' },
      { id: 'b6', label: 'Gear Rental', total: 600, category: 'Activities', startAt: '2025-12-06T08:00:00' },
    ],
    contributions: [],
    expenses: [],
  },
];


