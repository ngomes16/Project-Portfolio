/**
 * File: src/firebase.ts
 * Purpose: Initialize Firebase for React Native with AsyncStorage persistence. Supports demo mode
 *          when env variables are missing so the app can run without Firebase credentials.
 *          Reads config from `app.config.ts` (Constants.expoConfig.extra.firebase) first, then
 *          falls back to EXPO_PUBLIC_* and legacy variables.
 * Update: Use platform-specific Auth initialization (web: getAuth; native: initializeAuth without
 *         react-native-specific persistence to avoid bundling issues when the RN subpath is missing).
 */
import { initializeApp, getApps, getApp, FirebaseApp } from 'firebase/app';
import { getFirestore, Firestore } from 'firebase/firestore';
import { getAuth, Auth, initializeAuth, getReactNativePersistence } from 'firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
const extra = (Constants?.expoConfig?.extra as any) || {};
const extraFirebase = extra.firebase || {};
const API_KEY = extraFirebase.apiKey || process.env.EXPO_PUBLIC_API_KEY || process.env.API_KEY;
const AUTH_DOMAIN = extraFirebase.authDomain || process.env.EXPO_PUBLIC_AUTH_DOMAIN || process.env.AUTH_DOMAIN;
const PROJECT_ID = extraFirebase.projectId || process.env.EXPO_PUBLIC_PROJECT_ID || process.env.PROJECT_ID;
const STORAGE_BUCKET = extraFirebase.storageBucket || process.env.EXPO_PUBLIC_STORAGE_BUCKET || process.env.STORAGE_BUCKET;
const MESSAGING_SENDER_ID = extraFirebase.messagingSenderId || process.env.EXPO_PUBLIC_MESSAGING_SENDER_ID || process.env.MESSAGING_SENDER_ID;
const APP_ID = extraFirebase.appId || process.env.EXPO_PUBLIC_APP_ID || process.env.APP_ID;

// In CI/dev environments without secrets, allow the app to run without Firebase
export const isDemoMode: boolean = !API_KEY || !AUTH_DOMAIN || !PROJECT_ID || !APP_ID;

let app: FirebaseApp | null = null;
let auth: Auth | null = null;
let db: Firestore | null = null;

if (!isDemoMode) {
  const firebaseConfig = {
    apiKey: API_KEY,
    authDomain: AUTH_DOMAIN,
    projectId: PROJECT_ID,
    storageBucket: STORAGE_BUCKET,
    messagingSenderId: MESSAGING_SENDER_ID,
    appId: APP_ID,
  } as const;

  app = getApps().length ? getApp() : initializeApp(firebaseConfig);
  if (Platform.OS === 'web') {
    auth = getAuth(app);
  } else {
    // Native: initialize Auth with AsyncStorage persistence for session survival
    auth = initializeAuth(app, {
      persistence: getReactNativePersistence(AsyncStorage as any),
    });
  }
  db = getFirestore(app);
}

export { auth, db };
