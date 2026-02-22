## Firebase Setup

1) Create a Firebase project and enable Firestore.
2) In Project Settings → General, add an iOS and Android app (Expo managed is fine) and obtain config values.
3) Add the config into `mobile/app.config.ts` under `extra.firebase`:

```
extra: {
  firebase: {
    apiKey: "...",
    authDomain: "...",
    projectId: "...",
    storageBucket: "...",
    messagingSenderId: "...",
    appId: "..."
  }
}
```

4) In Firestore, create security rules appropriate for your testing. For local dev you can use test mode.
5) Seed sample users (run once): open the app and call `seedSampleUsers()` from `src/services/firestore` (e.g., temporarily from a screen `useEffect`). This creates users: `you`, `nate`, `ava`, `liam`.
6) Trips created via the Create Trip wizard will be written to `trips` collection when Firebase is configured. Popular trips on Home are read ordered by `popularity`.


