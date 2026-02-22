# Development Setup

Follow these steps after cloning the repository to run the mobile app with Expo Go.

## Prerequisites
- Node.js LTS (>=18)
- npm (>=9) or yarn (>=1.22)
- Expo Go app installed on your iOS/Android device

## Initial Setup
```bash
git clone <this-repo-url>
cd Trippi/mobile
npm install
npm run start
```

When the QR code appears, open Expo Go and scan it. Ensure your device and computer are on the same network (use `npm run start:lan`) or use the default tunnel.

## Project Structure
- `mobile/` – Expo app (UI)
- `mobile/app/` – Routes powered by expo-router
- `mobile/src/components/` – Reusable UI components
- `mobile/src/theme/` – Theme provider and styling utilities
- `mobile/src/data/` – Sample data for UI stubs
- `docs/FILE_STRUCTURE.md` – Detailed file responsibilities

## Common Tasks
- Update dependencies: `npm outdated` then `npm update`
- Clear cache if needed: `expo start -c`
- iOS simulator: `npm run ios`
- Android emulator: `npm run android`


