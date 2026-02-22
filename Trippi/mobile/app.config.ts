/**
 * File: app.config.ts
 * Purpose: Expo app configuration including app metadata, icons, splash, and plugin setup (expo-router).
 *          Injects Firebase config into `extra.firebase` from .env or EXPO_PUBLIC_* so runtime code
 *          can access it via `expo-constants` without custom Babel plugins.
 */
import { ExpoConfig, ConfigContext } from 'expo/config';

export default ({ config }: ConfigContext): ExpoConfig => ({
  name: 'Trippi',
  slug: 'trippi',
  version: '1.0.0',
  orientation: 'portrait',
  scheme: 'trippi',
  userInterfaceStyle: 'automatic',
  icon: './assets/Trippi_logo.png',
  splash: {
    image: './assets/Trippi_logo.png',
    resizeMode: 'contain',
    backgroundColor: '#F5F1E9'
  },
  ios: {
    supportsTablet: true
  },
  android: {
    adaptiveIcon: {
      foregroundImage: './assets/Trippi_logo.png',
      backgroundColor: '#F5F1E9'
    }
  },
  web: {
    bundler: 'metro',
    favicon: './assets/Trippi_logo.png'
  },
  plugins: ['expo-router'],
  extra: {
    router: {},
    firebase: {
      apiKey: process.env.EXPO_PUBLIC_API_KEY || process.env.API_KEY,
      authDomain: process.env.EXPO_PUBLIC_AUTH_DOMAIN || process.env.AUTH_DOMAIN,
      projectId: process.env.EXPO_PUBLIC_PROJECT_ID || process.env.PROJECT_ID,
      storageBucket: process.env.EXPO_PUBLIC_STORAGE_BUCKET || process.env.STORAGE_BUCKET,
      messagingSenderId: process.env.EXPO_PUBLIC_MESSAGING_SENDER_ID || process.env.MESSAGING_SENDER_ID,
      appId: process.env.EXPO_PUBLIC_APP_ID || process.env.APP_ID,
    },
  },
  experiments: {
    typedRoutes: true
  },
});


