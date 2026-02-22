/**
 * File: src/components/TripCard.tsx
 * Purpose: Hero-style trip card showing destination photo, dates, member avatars, and quick stats.
 * Update: Enhanced visual style with gradient overlay, info badges (members, days), and subtle CTA.
 * Update (asset path): Fix image require path to point to `mobile/assets/Trippi_logo.png` correctly.
 * Update: Use destination imagery via `getDestinationImage` with a tasteful fallback.
 */
import React from 'react';
import { View, Text, ImageBackground } from 'react-native';
import Svg, { Defs, LinearGradient, Stop, Rect } from 'react-native-svg';
import { Card } from './Card';
import { useTheme } from '../theme/ThemeProvider';
import { Avatar } from './Avatar';
import { getDestinationImage } from '../utils/images';

 type Props = { name: string; destination: string; dateRange: string; memberNames?: string[] };

 export function TripCard({ name, destination, dateRange, memberNames = [] }: Props) {
  const theme = useTheme();
  return (
    <Card style={{ marginBottom: 16, padding: 0, overflow: 'hidden' }}>
      <ImageBackground source={{ uri: getDestinationImage(destination) }} style={{ padding: 20, height: 160 }}>
        {/* Light vertical gradient to ensure readability over images */}
        <View pointerEvents="none" style={{ position: 'absolute', left: 0, right: 0, top: 0, bottom: 0 }}>
          <Svg width="100%" height="100%">
            <Defs>
              <LinearGradient id="lighten" x1="0%" y1="0%" x2="0%" y2="100%">
                <Stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.15" />
                <Stop offset="65%" stopColor="#FFFFFF" stopOpacity="0.55" />
                <Stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.85" />
              </LinearGradient>
            </Defs>
            <Rect x="0" y="0" width="100%" height="100%" fill="url(#lighten)" />
          </Svg>
        </View>
        <View style={{ position: 'relative' }}>
        <Text style={{ color: theme.colors.textPrimary, fontWeight: '800', fontSize: 20 }}>{name}</Text>
        <Text style={{ color: theme.colors.textSecondary, marginTop: 4, fontSize: 13 }}>{destination} • {dateRange}</Text>
        <View style={{ height: 10 }} />
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <View style={{ flexDirection: 'row' }}>
            {memberNames.slice(0, 4).map((n, i) => (
              <View key={n + i} style={{ marginRight: 6 }}>
                <Avatar name={n} size={26} />
              </View>
            ))}
          </View>
          <View style={{ flex: 1 }} />
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <View style={{ paddingVertical: 4, paddingHorizontal: 8, backgroundColor: theme.colors.surface, borderRadius: 999, borderWidth: 1, borderColor: theme.colors.border }}>
              <Text style={{ color: theme.colors.textSecondary, fontSize: 11 }}>{memberNames.length} members</Text>
            </View>
            <View style={{ paddingVertical: 4, paddingHorizontal: 8, backgroundColor: theme.colors.surface, borderRadius: 999, borderWidth: 1, borderColor: theme.colors.border }}>
              <Text style={{ color: theme.colors.textSecondary, fontSize: 11 }}>Tap to view</Text>
            </View>
          </View>
        </View>
        </View>
      </ImageBackground>
    </Card>
  );
 }


