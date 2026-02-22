/**
 * File: babel.config.js
 * Purpose: Babel configuration enabling Expo. Removed react-native-dotenv to rely on Expo public env
 *          (EXPO_PUBLIC_*) for runtime configuration, which avoids manifest/env plugin conflicts.
 */
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: ['react-native-worklets/plugin'],
  };
};


