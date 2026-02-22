/**
 * File: web/src/data/sample.js
 * Purpose: Sample content for the GitHub Pages demos. Mirrors the shapes used in
 * the mobile app's sample data with a smaller dataset for the web.
 */
export const members = [
  { id: '1', name: 'You', avatarColor: '#7C5CFF' },
  { id: '2', name: 'Nate', avatarColor: '#22C55E' },
  { id: '3', name: 'Ava', avatarColor: '#F59E0B' },
  { id: '4', name: 'Liam', avatarColor: '#0EA5E9' },
];

export const trips = [
  {
    id: 'chi',
    name: 'Chicago City Break',
    destination: 'Chicago, IL',
    dateRange: 'Sep 20 - Sep 25',
    goalBudget: 4200,
    members,
    itinerary: [
      { id: 'cb1', label: 'Hotel (Loop)', total: 1500, perPerson: 375, category: 'Lodging' },
      { id: 'cb2', label: 'Flights ORD Arrival', total: 1200, perPerson: 300, category: 'Flights' },
      { id: 'cb3', label: 'Architecture Boat Tour', total: 200, category: 'Activities' },
      { id: 'cb4', label: 'Deep Dish Dinner', total: 180, category: 'Food' },
    ],
  },
  {
    id: 'beach',
    name: 'Beach Escape',
    destination: 'Cancún, MX',
    dateRange: 'Oct 02 - Oct 08',
    goalBudget: 3800,
    members,
    itinerary: [
      { id: 'b1', label: 'Airbnb', total: 1200, perPerson: 300, category: 'Lodging' },
      { id: 'b2', label: 'Flights', total: 1800, perPerson: 450, category: 'Flights' },
      { id: 'b3', label: 'Food & Drinks', total: 800, category: 'Food' },
    ],
  },
];


