/**
 * File: env.d.ts
 * Purpose: Type declarations for Expo public runtime env used in the app (EXPO_PUBLIC_*).
 * Update: Declares 'firebase/auth/react-native' module to support React Native Auth persistence types.
 */
declare namespace NodeJS {
  interface ProcessEnv {
    EXPO_PUBLIC_API_KEY?: string;
    EXPO_PUBLIC_AUTH_DOMAIN?: string;
    EXPO_PUBLIC_PROJECT_ID?: string;
    EXPO_PUBLIC_STORAGE_BUCKET?: string;
    EXPO_PUBLIC_MESSAGING_SENDER_ID?: string;
    EXPO_PUBLIC_APP_ID?: string;
    API_KEY?: string;
    AUTH_DOMAIN?: string;
    PROJECT_ID?: string;
    STORAGE_BUCKET?: string;
    MESSAGING_SENDER_ID?: string;
    APP_ID?: string;
  }
}

declare module 'firebase/auth/react-native' {
  export function getReactNativePersistence(storage: any): any;
}
