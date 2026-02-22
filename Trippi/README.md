# Trippi

An all-in-one trip planner and budget tracker for group travel. Plan itineraries, track expenses, split costs, and settle up — all from a mobile app backed by Firebase with real-time sync.

## Features

- **Trip Planning** — Create trips with destinations, dates, and day-by-day itineraries with a visual timeline
- **Budget Tracking** — Category-based budgets (Lodging, Flights, Transport, Activities, Food, Other) with per-person cost breakdowns and savings progress
- **Expense Splitting** — Record expenses with equal, weighted, or custom splits; track who paid and who owes
- **Balance Settlement** — Automatically calculates who owes whom with a "Settle Up" feature for easy resolution
- **Group Coordination** — Invite members, assign roles (Owner, Manager, Member, Viewer), and manage trips collaboratively
- **Real-Time Sync** — Firestore listeners keep all group members up to date instantly
- **Calendar Filtering** — Mini calendar view to filter itinerary items by day
- **AI Trip Planner** — Demo conversation UI for AI-assisted trip planning
- **Web Landing Page** — Marketing site deployed to GitHub Pages with interactive demos

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Mobile App** | React Native, Expo SDK 54, TypeScript 5.9 |
| **Routing** | expo-router (file-based) |
| **State** | React Context API (TripsStore, AuthContext, BudgetState, UIState) |
| **Backend** | Firebase (Cloud Firestore, Firebase Auth) |
| **Charts** | react-native-svg (pie charts, progress rings) |
| **Web** | Vanilla HTML/CSS/JavaScript, GitHub Pages |

## Project Structure

```
Trippi/
├── mobile/                          # Expo/React Native app
│   ├── app/                         # File-based routes
│   │   ├── (tabs)/                  # Tab navigation (Home, Trips, Profile)
│   │   ├── trips/create.tsx         # Trip creation wizard
│   │   ├── trip/[id].tsx            # Trip detail (Overview/Itinerary/Members/Expenses)
│   │   ├── trip/[id]/itinerary/     # Itinerary CRUD
│   │   └── login.tsx                # Authentication screen
│   └── src/
│       ├── components/              # Reusable UI (Button, Card, PieChart, etc.)
│       ├── state/                   # Context providers (Trips, Auth, Budget, UI)
│       ├── services/firestore/      # Firestore CRUD operations and types
│       ├── utils/                   # Currency formatting, budget helpers, balance math
│       └── theme/                   # Custom theme system
├── web/                             # GitHub Pages landing site
│   ├── index.html                   # Marketing page
│   └── src/components/              # Carousel, donut chart, timeline, AI chat demos
└── trippi-backend/                  # Firebase configuration
    ├── firebase.json
    ├── firestore.rules
    └── firestore.indexes.json
```

## Getting Started

### Prerequisites

- Node.js 18+, npm 9+
- Expo Go app on your phone (for mobile testing)
- Firebase project (or run in demo mode with sample data)

### Mobile App

```bash
cd mobile
npm install
npm start          # Starts Metro bundler — scan QR with Expo Go
```

### Web Landing Page

```bash
cd web
python3 -m http.server 5173
# Open http://localhost:5173
```

Or visit the live site: [https://arnolda2.github.io/Trippi2/](https://arnolda2.github.io/Trippi2/)

### Firebase Setup (Optional)

1. Create a Firebase project and enable Firestore + Authentication
2. Add your Firebase config to `mobile/.env`
3. Deploy Firestore rules from `trippi-backend/`

The app runs in demo mode with sample data if Firebase credentials are not configured.

## How It Works

### Firestore Data Model
Trips are top-level documents containing subcollections for members, itinerary events, and expenses. A denormalized `memberUids` array on each trip document enables efficient membership queries using Firestore's `array-contains` operator.

### Balance Calculation
For each expense, participants owe their share (based on split type) and the payer receives a credit for the full amount. Contributions further adjust balances. The algorithm aggregates all expenses, sorts members by net balance, and produces a minimal set of settlement transactions.

### Expense Splitting
Three split modes are supported: equal (divide evenly), weighted (proportional shares), and custom (manually assigned amounts). Expenses can be linked to itinerary items for budget tracking by category.

### State Management
The app uses React Context for global state across four providers: `TripsStore` (trip data and mutations), `AuthContext` (Firebase auth state), `BudgetState` (budget calculations), and `UIState` (modals and navigation). Firestore `onSnapshot` listeners provide real-time updates across all group members.
