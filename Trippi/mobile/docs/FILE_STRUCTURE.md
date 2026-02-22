# Mobile App File Structure (Updated)

This document lists the key files in the `mobile/` app and their purposes. Each file includes a header comment in code describing its role.

## Routes
- `app/_layout.tsx` – root stack (login + tabs)
- `app/(tabs)/_layout.tsx` – tabs configuration (Home, Trips, Profile)
- `app/(tabs)/index.tsx` – Home (modern dashboard: Upcoming Trips tiles with progress rings, Savings Progress chart, Prioritized Savings card, Budget Summary)
- `app/(tabs)/trips.tsx` – Trips list → Trip Detail
- `app/trips/create.tsx` – Trip creation wizard
- `app/trip/[id].tsx` – Trip Detail (Overview, Itinerary with mini calendar + timeline filtering, Members, Expenses; delete via overview menu)
- `app/trip/[id]/itinerary/new.tsx` – add itinerary item page
- `app/trip/[id]/itinerary/[itemId]/edit.tsx` – edit itinerary item page
- `app/trip/[id]/itinerary/[itemId]/expense.tsx` – add expense with split editor
- `app/trip/[id]/member/[memberId].tsx` – member profile page
// Budget tab removed per product direction. Budget insights live in Trips and Home.
- `app/profile.tsx` – Redesigned profile with insights and balances. Developer seeding tools removed.
- `app/ai.tsx` – Dedicated AI Trip Planner sample conversation screen

## State & Data
- `src/state/TripsStore.tsx` – trips store (create/select/add member/item/contribution/expense; edit itinerary; deleteTrip; member persistence; supports goal budget and dates)
- `src/state/AuthContext.tsx` – auth provider; demo-aware (skips Firebase subscription when no env)
- `src/data/sample.ts` – sample trips with itinerary (category, times), contributions, expenses

## Components
- `src/components/Screen.tsx` – safe-area wrapper (supports scrolling)
- `src/components/Card.tsx` – surface card
- `src/components/Button.tsx` – buttons
- `src/components/InlineButton.tsx` – compact inline button for list actions
- `src/components/TextField.tsx` – form fields
- `src/components/KeyboardAccessory.tsx` – iOS keyboard bar with Prev/Next/Done
- `src/components/Select.tsx` – modal dropdown select
- `src/components/DateTimeField.tsx` – OS date & time picker field
- `src/components/Checkbox.tsx` – checkbox toggle
- `src/components/Segmented.tsx` – segment control
- `src/components/TripCard.tsx` – hero trip card (modern visuals, badges)
- `src/components/FAB.tsx` – floating action button
- `src/components/Avatar.tsx` – avatar
- `src/components/ListItem.tsx` – list row
- `src/components/ProgressBar.tsx` – progress
- `src/components/PieChart.tsx` – budget chart
- `src/components/PieChartWithOverlay.tsx` – interactive pie chart wrapper with tooltip overlay
- `src/components/CircularProgress.tsx` – small circular progress ring used on Upcoming Trips tiles
- `src/components/TripSwitcher.tsx` – modal trip picker
- `src/components/create-trip/StepIndicator.tsx` – progress indicator for the create trip flow
- `src/components/create-trip/WizardContainer.tsx` – animated container for step transitions
- `src/components/create-trip/steps/DetailsStep.tsx` – details form with dates and goal per person
- `src/components/create-trip/steps/MembersStep.tsx` – members selection and management
- `src/components/create-trip/steps/ReviewStep.tsx` – review summary with create action
- `src/components/MemberAvatarsRow.tsx` – avatars row
- `src/components/CategoryLegend.tsx` – budget legend
- `src/components/trip/ItineraryTimeline.tsx` – grouped timeline for itinerary (supports date filtering)
- `src/components/trip/MiniCalendar.tsx` – compact month calendar for itinerary filtering
- `src/components/trip/TripOverviewCard.tsx` – overview + budget breakdown card (menu with edit itinerary, delete trip)
- `src/components/trip/ItineraryList.tsx` – redesigned itinerary list with compact actions and projected total
- `src/components/trip/ItineraryForm.tsx` – reusable add/edit itinerary form
- `src/components/trip/ExpensesSection.tsx` – expenses summary + list
- `src/components/trip/SettleUpCard.tsx` – shows what you owe/are owed with gradient Settle Up CTA (not used on Itinerary tab)
- `src/components/trip/TripProgressRow.tsx` – per-trip goal progress row
- `src/components/chat/ChatBubble.tsx` – chat bubble for AI/User messages

## Utils
- `src/utils/format.ts` – currency/percent
- `src/utils/budget.ts` – category colors & totals
- `src/utils/balances.ts` – per-member balances from expenses & contributions

## Firebase
- `src/firebase.ts` – Firebase initialization with AsyncStorage persistence; supports demo mode when `.env` is missing. Exports `auth`, `db`, and `isDemoMode`.
 - `src/services/firestore/trips.ts` – trip CRUD and listeners (members/events/expenses); includes `listPopularTrips`, `deleteTrip`, and membership-aware listeners
 - `src/services/firestore/seeds.ts` – developer utility to seed Firestore with sample trips

