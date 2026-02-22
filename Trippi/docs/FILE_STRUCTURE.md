# File Structure and Responsibilities

This document outlines the modular file breakdown for the Trippi mobile app and what each file/folder does. Every file contains a brief header comment describing its purpose.

## Top-level
- `DEVELOPMENT_SETUP.md` – step-by-step project setup and common tasks
- `mobile/` – Expo app with UI
- `web/` – GitHub Pages static site (marketing + interactive demos)

## mobile/
- `package.json` – scripts and dependencies for the Expo app
- `app.config.ts` – Expo configuration (name, icons, splash, plugins)
- `babel.config.js` – Babel presets/plugins (expo, expo-router)
- `tsconfig.json` – TypeScript configuration and path aliases
- `index.js` – expo-router entrypoint
- `assets/Trippi_logo.png` – app logo asset

### Routes (expo-router)
- `app/_layout.tsx` – root layout and tab navigation
- `app/(tabs)/_layout.tsx` – tabs config (Home, Trips, Profile)
- `app/(tabs)/index.tsx` – Home dashboard (Upcoming Trips tiles w/ progress rings, Savings Progress pie, Prioritized Savings, Budget Summary). Includes an enlarged top‑right purple blur and proper safe‑area spacing so content isn’t clipped.
- `app/(tabs)/trips.tsx` – Trips list with search/filters and navigation to details + create entry
- `app/trips/create.tsx` – multi-step trip creation wizard
- `app/trip/[id].tsx` – trip detail with tabs (Overview, Itinerary, Members, Expenses) and Delete Trip action
// Budget tab removed; high-level budget summaries are shown on Home and in Trip detail.
- `app/profile.tsx` – redesigned profile/settings
- `app/ai.tsx` – dedicated AI Trip Planner sample conversation

### Source
- `src/theme/ThemeProvider.tsx` – theming, spacing, typography, safe-area
- `src/state/TripsStore.tsx` – global trips store (create/select/add member/item/contribution/expense; edit itinerary; deleteTrip; Firestore-backed members; goal budgets + dates)
- `src/state/AuthContext.tsx` – firebase-auth-backed user session; redirects unauthenticated users to login
- `src/utils/format.ts` – currency and percent formatters
- `src/utils/budget.ts` – budget helpers (category colors, totals)
- `src/components/Logo.tsx` – reusable logo component
- `src/components/Button.tsx` – primary/secondary button and gradient CTA variant
- `src/components/InlineButton.tsx` – compact inline button for list actions
- `src/components/Card.tsx` – surface container
- `src/components/Header.tsx` – simple header
- `src/components/Screen.tsx` – safe-area screen wrapper with configurable `edges`, optional `floatingBottom` overlay support, and correct bottom padding.
- `src/components/TextField.tsx` – labeled text input
- `src/components/ProgressBar.tsx` – progress indicator
- `src/components/Avatar.tsx` – avatar initial badge
- `src/components/ListItem.tsx` – row list item
- `src/components/Segmented.tsx` – segmented tabs control
- `src/components/FAB.tsx` – floating action button
- `src/components/create-trip/StepIndicator.tsx` – wizard progress indicator
- `src/components/create-trip/WizardContainer.tsx` – animated slide container for steps
- `src/components/create-trip/steps/DetailsStep.tsx` – combined first-step form
- `src/components/create-trip/steps/MembersStep.tsx` – members selection page
- `src/components/create-trip/steps/ReviewStep.tsx` – final review and create
- `src/components/TripCard.tsx` – hero trip preview card
- `src/components/TripListItem.tsx` – rich trip item row for Trips tab
- `src/components/MemberAvatarsRow.tsx` – overlapping avatars row
- `src/components/CategoryLegend.tsx` – legend for budget categories
- `src/components/TripSwitcher.tsx` – modal-based trip picker
- `src/components/PieChart.tsx` – svg-based pie chart
- `src/components/SavingsPieChart.tsx` – pie chart arcs and renderer
- `src/components/PieChartWithOverlay.tsx` – interactive pie chart overlay/tooltip wrapper
- `src/components/CircularProgress.tsx` – compact circular percent ring used on trip tiles
- `src/components/TopRightBlur.tsx` – decorative radial purple blur for page background; now originates further offscreen (top-right) and is larger to avoid clipping.
- `src/components/ExpenseForm.tsx` – keyboard-safe stepped expense form
- `src/components/chat/ChatBubble.tsx` – AI/user chat bubble
- `src/data/sample.ts` – mock trips/members/itinerary/contributions data
- `src/components/trip/ItineraryTimeline.tsx` – grouped timeline
- `src/components/trip/TripOverviewCard.tsx` – overview + budget breakdown; full‑bleed hero reaches the very top and top controls are anchored within safe‑area.
- `src/components/trip/TripSectionBar.tsx` – bottom in-screen section tabs for Trip Detail (Overview/Itinerary/Members/Expenses); label changed to “Overview” and positioning lowered.
- `src/components/trip/ItineraryList.tsx` – redesigned itinerary list
- `src/components/trip/MemberDetailsModal.tsx` – member details modal
- `src/components/trip/ExpensesSection.tsx` – expenses summary + list
- `src/components/trip/SettleUpCard.tsx` – shows what you owe/are owed with Settle Up CTA
- `src/components/trip/TripProgressRow.tsx` – per-trip goal progress

### Services
- `src/firebase.ts` – Firebase initialization; supports demo mode when env is missing (native uses memory persistence to avoid RN subpath issues)
- `src/services/firestore/seeds.ts` – developer seeding utility for sample trips
- `src/services/firestore/trips.ts` – trip CRUD (create, delete), listeners (events, expenses, membership-aware trips for owner or member), and listPopularTrips helper
- `src/services/firestore.ts` – re-exports Firestore services
- `src/services/firestore/index.ts` – barrel exports for typed Firestore helpers
- `src/services/firestore/types.ts` – Firestore document types (users, trips, members, events, expenses)
- `src/services/firestore/users.ts` – user profile CRUD and search
- `src/services/firestore/trips.ts` – trip CRUD, member add/listen, events/expenses add/listen

## Notes
- Use path aliases: `@components/*`, `@theme/*`, `@data/*`
- All UI is styled for a dark, modern look and should be easy to iterate.

## web/
- `index.html` – landing page with hero, features, toolbar, demos, stats; added Portal section (login + dashboard preview)
- `.nojekyll` – disable Jekyll processing for ES modules
- `assets/css/theme.css` – theme tokens and layout styles for the site
- `assets/css/base.css` – reset and utility styles
- `src/main.js` – entry that mounts interactive demos, page behaviors, and Portal (demo auth; optional Firebase web via window.__TRIPPI_FIREBASE__)
- `src/data/sample.js` – sample trips/members/itinerary data mirrored from mobile
- `src/utils/format.js` – currency and percentage formatters
- `src/utils/colors.js` – category color mapping
- `src/components/TripCarousel.js` – horizontally scrollable trip cards
- `src/components/BudgetDonut.js` – SVG donut chart for budget categories
- `src/components/ItineraryTimeline.js` – simple itinerary timeline list
- `src/components/AIChat.js` – local simulated AI chat UI

### CI
- `.github/workflows/pages.yml` – deploy `web/` folder to GitHub Pages on push


